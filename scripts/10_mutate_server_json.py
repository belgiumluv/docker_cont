import json
import secrets
import string
import os
import sqlite3
#base64 -- ss-new password
#path начинается с /
# "server_name": "www.habbo.com" -- > google.com
# masquerade, server_name --> заменить в hysteria
#shadowtls --> shamela
from nacl.public import PrivateKey
import base64
from random import randint
db_path = "/var/lib/bd/bd.db"
os.makedirs(os.path.dirname(db_path), exist_ok=True)



conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
cur = conn.cursor()

def generate_ss2022_password() -> str:

    key = os.urandom(32)  # 32 байта = 256 бит
    return base64.b64encode(key).decode("utf-8")


def generateString():
    length = 22
    chars = string.ascii_letters + string.digits
    result = ''.join(secrets.choice(chars) for _ in range(length))
    return result

def b64url_nopad(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def generate_reality_keypair():
    sk = PrivateKey.generate()       
    pk = sk.public_key               
    priv = b64url_nopad(bytes(sk))
    pub  = b64url_nopad(bytes(pk))
    return priv, pub

with open("/vpn/masq_domain_list.json", 'r', encoding='utf-8') as file:
    data = json.load(file)
    list_selected = []
    num = randint(0, len(data))
    list_selected.append(data[num-1])
    num = randint(0, len(data))
    while True:
        if data[num-1] not in list_selected:
            list_selected.append(data[num-1])
            break
        else:
            num = randint(0, len(data))
    num = randint(0, len(data))
    while True:
        if data[num-1] not in list_selected:
            list_selected.append(data[num-1])
            break
        else:
            num = randint(0, len(data))
    file.close()

with open("/vpn/msq_domain_list_vibork.json", 'w', encoding='utf-8') as file:
    json.dump(list_selected, file, ensure_ascii=False, indent=4)
    file.close()

cur.execute("""
CREATE TABLE IF NOT EXISTS fakedomain (
    reality   TEXT,
    shadowtls TEXT,
    hysteria  TEXT
)
""")

cur.execute(
    "INSERT INTO fakedomain (reality, shadowtls, hysteria) VALUES (?, ?, ?)", (list_selected[0], list_selected[1], list_selected[2])
)


with open("/vpn/domain.txt", 'r', encoding='utf-8') as file:
    domain = file.read()
    file.close()
#настроить пути, path --> правдоподобная генерация

with open("/vpn/server.json", mode="r+", encoding="utf-8") as file:
    data = json.load(file)
    mainBlock = data["inbounds"]
    changes_list = {}
    changes_listwith = {}
    for protocol in mainBlock:
        if protocol["tag"] == "v10-trojan-grpc":
            transport = protocol["transport"]
            transport["service_name"] = f'api{generateString()}'
            changes_list["v10-trojan-grpc"] = transport["service_name"]
            changes_listwith["v10_trojan_grpc"] = transport["service_name"]
        elif protocol["tag"] == "v10-vless-grpc":
            transport = protocol["transport"]
            transport["service_name"] = f'api{generateString()}'
            changes_list["v10-vless-grpc"] = transport["service_name"]
            changes_listwith["v10_vless_grpc"] = transport["service_name"]
        elif protocol["tag"] == "v10-vmess-grpc":
            transport = protocol["transport"]
            transport["service_name"] = f'api{generateString()}'
            changes_list["v10-vmess-grpc"] = transport["service_name"]
            changes_listwith["v10_vmess_grpc"] = transport["service_name"]
        elif protocol["tag"] == "v10-vless-httpupgrade":
            transport = protocol["transport"]
            transport["path"] = f"/files{generateString()}"
            changes_list["v10-vless-httpupgrade"] = transport["path"]
            changes_listwith["v10_vless_httpupgrade"] = transport["path"]
        elif protocol["tag"] == "v10-vless-tcp":
            transport = protocol["transport"]
            transport["path"] = f"/user{generateString()}"
            changes_list["v10-vless-tcp"] = transport["path"]
            changes_listwith["v10_vless_tcp"] = transport["path"]
        elif protocol["tag"] == "v10-vmess-ws":
            transport = protocol["transport"]
            transport["path"] = f"/assets{generateString()}"
            changes_list["v10-vmess-ws"] = transport["path"]
            changes_listwith["v10_vmess_ws"] = transport["path"]
        elif protocol["tag"] == "v10-vmess-tcp":
            transport = protocol["transport"]
            transport["path"] = f"/user{generateString()}"
            changes_list["v10-vmess-tcp"] = transport["path"]
            changes_listwith["v10_vmess_tcp"] = transport["path"]
        elif protocol["tag"] == "v10-vmess-httpupgrade":
            transport = protocol["transport"]
            transport["path"] = f"/files{generateString()}"
            changes_list["v10-vmess-httpupgrade"] = transport["path"]
            changes_listwith["v10_vmess_httpupgrade"] = transport["path"]
        elif protocol["tag"] == "hysteria_in_50062":
            protocol["masquerade"] = f'https://{list_selected[2]}:80/'
            obfs = protocol["obfs"]
            obfs["password"] = generateString()
            changes_list["hysteria_in_50062"] = obfs["password"]
            changes_listwith["hysteria_in_50062"] = obfs["password"]
            tls = protocol["tls"]
            tls["server_name"] = domain
        elif protocol["tag"] == "realityin_43124":
            private, publick = generate_reality_keypair()
            print(publick)#dump sql
            tls = protocol["tls"]
            reality = tls["reality"]
            reality["private_key"] = private
            changes_list["realityin_43124"] = private
            changes_listwith["realityin_43124"] = private
            tls = protocol["tls"]
            tls["server_name"] = list_selected[0]
            reality = tls["reality"]
            handshake = reality["handshake"]
            handshake["server"] = list_selected[0]

        elif protocol["tag"] == "ss-new":
            protocol["password"] = generate_ss2022_password()
            changes_list["ss-new"] = protocol["password"]
            changes_listwith["ss_new"] = protocol["password"]
        elif protocol["tag"] == "shadowtls":
            handshake = protocol["handshake"]
            handshake["server"] = list_selected[1]
        elif protocol["tag"] == "v10-trojan-tcp":
            transport = protocol["transport"]
            transport["path"] = f"/user{generateString()}"
            changes_list["v10-trojan-tcp"] = transport["path"]
            changes_listwith["v10_trojan_tcp"] = transport["path"]
        elif protocol["tag"] == "v10-trojan-ws":
            transport = protocol["transport"] 
            transport["path"] = f"/assets{generateString()}"
            changes_list["v10-trojan-ws"] = transport["path"]
            changes_listwith["v10_trojan_ws"] = transport["path"]
        elif protocol["tag"] == "v10-vless-ws":
            transport = protocol["transport"] 
            transport["path"] = f"/assets{generateString()}"
            changes_list["v10-vless-ws"] = transport["path"]
            changes_listwith["v10_vless_ws"] = transport["path"]
        elif protocol["tag"] == "tuic_in_55851":
            tls = protocol["tls"]
            tls["server_name"] = domain

    file.seek(0)
    json.dump(data, file, ensure_ascii=False, indent=4)
    file.truncate()
    file.close()
publick = str(publick)

cur.execute("""
CREATE TABLE IF NOT EXISTS protocol_path (
    v10_trojan_grpc TEXT NOT NULL,
    v10_vless_grpc TEXT NOT NULL,
    v10_vmess_grpc TEXT NOT NULL,
    v10_vless_httpupgrade TEXT NOT NULL,
    v10_vless_tcp TEXT NOT NULL,
    v10_vmess_ws TEXT NOT NULL,
    v10_vmess_tcp TEXT NOT NULL,
    v10_vmess_httpupgrade TEXT NOT NULL,
    hysteria_in_50062 TEXT NOT NULL,
    realityin_43124 TEXT NOT NULL,
    ss_new TEXT NOT NULL,
    v10_trojan_tcp TEXT NOT NULL,
    v10_trojan_ws TEXT NOT NULL,
    v10_vless_ws TEXT NOT NULL
)
""")


cols = ", ".join(changes_listwith.keys())
placeholders = ", ".join("?" for _ in changes_listwith)
values = tuple(changes_listwith.values())

cur.execute(f"INSERT INTO protocol_path ({cols}) VALUES ({placeholders})", values)



cur.execute("""
CREATE TABLE IF NOT EXISTS realitykey (
    key TEXT
)
""")

# вставка
cur.execute("INSERT INTO realitykey (key) VALUES (?)", (publick,))

conn.commit()
conn.close()
with open("/vpn/changes_dict.json", 'w', encoding="utf-8") as file:
    json.dump(changes_list, file, ensure_ascii=False, indent=4)
    print("done")