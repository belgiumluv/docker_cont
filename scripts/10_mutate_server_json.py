#!/usr/bin/env python3
import os, json, sqlite3, shutil, base64, secrets, string
from pathlib import Path
from random import sample
from nacl.public import PrivateKey  # требуется python3-nacl

CONFIGS_DIR = Path(os.getenv("CONFIGS_DIR", "/app/configs"))
VPN_DIR     = Path(os.getenv("VPN_DIR", "/vpn"))
DB_PATH     = Path(os.getenv("DB_PATH", "/var/lib/bd/bd.db"))

MASQ_SRC    = CONFIGS_DIR / "masq_domain_list.json"
MASQ_DST    = VPN_DIR     / "masq_domain_list.json"
SERVER_JSON = VPN_DIR     / "server.json"
DOMAIN_TXT  = VPN_DIR     / "domain.txt"
CHANGES_OUT = VPN_DIR     / "changes_dict.json"

def log(m): print(f"[mutate] {m}", flush=True)

def b64url_nopad(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def generate_reality_keypair():
    sk = PrivateKey.generate()
    pk = sk.public_key
    return b64url_nopad(bytes(sk)), b64url_nopad(bytes(pk))

def gen_ss2022_password() -> str:
    return base64.b64encode(os.urandom(32)).decode("utf-8")

def gen_str(n=22) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(n))

def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fakedomain (
            reality   TEXT,
            shadowtls TEXT,
            hysteria  TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS realitykey (
            key TEXT
        )
    """)
    conn.commit()
    conn.close()

def main():
    # 1) Копируем маскарад-лист в /vpn
    if not MASQ_SRC.exists():
        raise FileNotFoundError(f"Нет {MASQ_SRC}. Положи masq_domain_list.json в {CONFIGS_DIR}")
    VPN_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MASQ_SRC, MASQ_DST)
    log(f"скопирован {MASQ_SRC} -> {MASQ_DST}")

    # 2) Загружаем список доменов и выбираем 3 уникальных
    with open(MASQ_DST, "r", encoding="utf-8") as f:
        domains = json.load(f)
    if not isinstance(domains, list) or len(domains) < 3:
        raise ValueError("masq_domain_list.json должен быть списком длиной >= 3")
    reality_dom, shadowtls_dom, hysteria_dom = sample(domains, 3)

    # 3) Обеспечиваем БД и сохраняем выбранные домены
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH), timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("DELETE FROM fakedomain")
    cur.execute("INSERT INTO fakedomain (reality, shadowtls, hysteria) VALUES (?, ?, ?)",
            (reality_dom, shadowtls_dom, hysteria_dom))
    conn.commit()

    # 4) Читаем наш домен с диска
    if not DOMAIN_TXT.exists():
        raise FileNotFoundError(f"Нет {DOMAIN_TXT}; сначала должен отработать setconfiguration")
    with open(DOMAIN_TXT, "r", encoding="utf-8") as f:
        my_domain = f.read().strip()

    # 5) Мутируем /vpn/server.json
    if not SERVER_JSON.exists():
        raise FileNotFoundError(f"Нет {SERVER_JSON}")
    with open(SERVER_JSON, "r+", encoding="utf-8") as f:
        data = json.load(f)

        changes = {}
        for proto in data.get("inbounds", []):
            tag = proto.get("tag", "")
            if tag in ("v10-trojan-grpc", "v10-vless-grpc", "v10-vmess-grpc"):
                t = proto.get("transport", {})
                t["service_name"] = f"api{gen_str()}"
                changes[tag] = t["service_name"]
            elif tag in ("v10-vless-httpupgrade", "v10-vmess-httpupgrade"):
                t = proto.get("transport", {})
                t["path"] = f"/files{gen_str()}"
                changes[tag] = t["path"]
            elif tag in ("v10-vless-tcp", "v10-vmess-tcp", "v10-trojan-tcp"):
                t = proto.get("transport", {})
                t["path"] = f"/user{gen_str()}"
                changes[tag] = t["path"]
            elif tag in ("v10-vmess-ws", "v10-trojan-ws", "v10-vless-ws"):
                t = proto.get("transport", {})
                t["path"] = f"/assets{gen_str()}"
                changes[tag] = t["path"]
            elif tag == "hysteria_in_50062":
                proto["masquerade"] = f"https://{hysteria_dom}:80/"
                obfs = proto.get("obfs", {})
                obfs["password"] = gen_str()
                changes[tag] = obfs["password"]
                tls = proto.get("tls", {})
                tls["server_name"] = my_domain
            elif tag == "realityin_43124":
                priv, pub = generate_reality_keypair()
                tls = proto.get("tls", {})
                tls["server_name"] = reality_dom
                reality = tls.get("reality", {})
                reality["private_key"] = priv
                handshake = reality.get("handshake", {})
                handshake["server"] = reality_dom
                # сохранить обратно вложенные dict (на случай отсутствия)
                reality["handshake"] = handshake
                tls["reality"] = reality
                proto["tls"] = tls
                changes[tag] = priv
                # Запоминаем публичный ключ
                cur.execute("DELETE FROM realitykey")
                cur.execute("INSERT INTO realitykey (key) VALUES (?)", (pub,))
            elif tag == "ss-new":
                proto["password"] = gen_ss2022_password()
                changes[tag] = proto["password"]
            elif tag == "shadowtls":
                hs = proto.get("handshake", {})
                hs["server"] = shadowtls_dom
                proto["handshake"] = hs
            elif tag == "tuic_in_55851":
                tls = proto.get("tls", {})
                tls["server_name"] = my_domain
                proto["tls"] = tls

        f.seek(0)
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.truncate()

    conn.commit()
    conn.close()

    with open(CHANGES_OUT, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=4)

    log("done")

if __name__ == "__main__":
    main()
