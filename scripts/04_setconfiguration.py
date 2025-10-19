#!/usr/bin/env python3
import os
import json
import shutil
import sqlite3
from pathlib import Path

import requests

# ---------- пути (можно переопределить через ENV) ----------
CONFIGS_DIR = Path(os.getenv("CONFIGS_DIR", "/app/configs"))
VPN_DIR     = Path(os.getenv("VPN_DIR", "/vpn"))
DB_PATH     = Path(os.getenv("DB_PATH", "/var/lib/bd/bd.db"))
SERVERLIST  = CONFIGS_DIR / "serverlist.json"         # источник
VPN_SERVERLIST = VPN_DIR / "serverlist.json"          # целевой

VPN_SERVERCONF = VPN_DIR / "server_configuration.json"
VPN_DOMAIN_TXT = VPN_DIR / "domain.txt"

def log(msg: str):
    print(f"[setconfiguration] {msg}", flush=True)

def get_public_ip(timeout=5) -> str:
    # можно подключить резервные источники при желании
    url = "https://api.ipify.org?format=text"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text.strip()

def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    # таблица + уникальность ip
    cur.execute("""
    CREATE TABLE IF NOT EXISTS server_conf (
        ip TEXT PRIMARY KEY,
        domain TEXT
    )
    """)
    conn.commit()
    conn.close()

def upsert_server_conf(ip: str, domain: str):
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    # UPSERT по ключу ip
    cur.execute("""
        INSERT INTO server_conf (ip, domain) VALUES (?, ?)
        ON CONFLICT(ip) DO UPDATE SET domain=excluded.domain
    """, (ip, domain))
    conn.commit()
    conn.close()

def main():
    # 1) Перенос serverlist.json из configs -> /vpn
    if not SERVERLIST.exists():
        raise FileNotFoundError(f"Не найден {SERVERLIST}. Положи serverlist.json в {CONFIGS_DIR}")
    VPN_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SERVERLIST, VPN_SERVERLIST)
    log(f"скопирован {SERVERLIST} -> {VPN_SERVERLIST}")

    # 2) Публичный IP
    ip = get_public_ip()
    log(f"публичный IP: {ip}")

    # 3) Читаем карту ip->domain
    with open(VPN_SERVERLIST, "r", encoding="utf-8") as f:
        data = json.load(f)
    if ip not in data:
        # можно вместо raise просто записать пустой домен
        log(f"Внимание: IP {ip} не найден в serverlist.json; запишу domain=''")
        domain = ""
    else:
        domain = str(data[ip])

    # 4) Пишем артефакты в /vpn
    with open(VPN_SERVERCONF, "w", encoding="utf-8") as f:
        json.dump([ip, domain], f, ensure_ascii=False, indent=2)
    with open(VPN_DOMAIN_TXT, "w", encoding="utf-8") as f:
        f.write(domain)
    log(f"записано: {VPN_SERVERCONF} и {VPN_DOMAIN_TXT}")

    # 5) DB: ensure + upsert
    ensure_db()
    upsert_server_conf(ip, domain)
    log(f"SQLite обновлена: {DB_PATH} (ip={ip}, domain='{domain}')")

if __name__ == "__main__":
    main()
