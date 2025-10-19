#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------- настройки путей ----------
VPN_DIR = Path(os.getenv("VPN_DIR", "/vpn"))
DB_PATH = Path(os.getenv("DB_PATH", "/var/lib/bd/bd.db"))
HAPROXY_CFG = Path(os.getenv("HAPROXY_CFG", "/etc/haproxy/haproxy.cfg"))
CHANGES_JSON = VPN_DIR / "changes_dict.json"

# теги -> имена бекендов, которые матчим по path_beg
TAG_TO_BACKENDS: Dict[str, List[str]] = {
    "v10-vless-ws": ["v10-vless-ws"],
    "v10-vless-grpc": ["v10-vless-grpc"],
    "v10-vless-httpupgrade": ["v10-vless-httpupgrade"],
    "v10-vless-tcp": ["v10-vless-tcp", "v10-vless-tcp-http"],
    "v10-vmess-ws": ["v10-vmess-ws"],
    "v10-vmess-grpc": ["v10-vmess-grpc"],
    "v10-vmess-httpupgrade": ["v10-vmess-httpupgrade"],
    "v10-vmess-tcp": ["v10-vmess-tcp", "v10-vmess-tcp-http"],
    "v10-trojan-ws": ["v10-trojan-ws"],
    "v10-trojan-grpc": ["v10-trojan-grpc"],
    "v10-trojan-httpupgrade": ["v10-trojan-httpupgrade"],
    "v10-trojan-tcp": ["v10-trojan-tcp", "v10-trojan-tcp-http"],
}

def _ensure_leading_slash(p: str) -> str:
    p = (p or "").strip()
    return p if (not p or p.startswith("/")) else f"/{p}"

def _backend_line_regex(backend_name: str) -> re.Pattern:
    # Ищем строки вида: use_backend <be> if { path_beg /OLD }
    return re.compile(rf'(use_backend\s+{re.escape(backend_name)}\s+if\s+\{{\s*path_beg\s+)(/[^ \}}\n]+)')

def _replace_paths(text: str, paths: Dict[str, str], notes: List[str]) -> str:
    for tag, new_val in (paths or {}).items():
        bes = TAG_TO_BACKENDS.get(tag)
        if not bes:
            notes.append(f"[WARN] Неизвестный тег '{tag}' — пропускаю.")
            continue
        new_path = _ensure_leading_slash(str(new_val))
        for be in bes:
            rx = _backend_line_regex(be)
            def _sub(m: re.Match) -> str:
                old = m.group(2)
                if old == new_path:
                    return m.group(1) + old
                notes.append(f"[PATH] {be}: {old} -> {new_path}")
                return m.group(1) + new_path
            text, n = rx.subn(_sub, text)
            if n == 0:
                notes.append(f"[MISS] use_backend {be} с path_beg не найден.")
    return text

def _replace_domains(text: str,
                     reality_server_name: Optional[str],
                     shadowtls_server_name: Optional[str],
                     notes: List[str]) -> str:
    """Заменяем 'www.habbo.com' -> reality, 'www.shamela.ws' -> shadowtls во всех местах (включая ':80')."""

    def _sub_all(all_text: str, old: str, new: str, label: str) -> str:
        rx_port = re.compile(rf'\b{re.escape(old)}:80\b')
        rx_plain = re.compile(rf'\b{re.escape(old)}\b')
        def _sub_port(m: re.Match) -> str:
            oldv, newv = m.group(0), f"{new}:80"
            if oldv != newv: notes.append(f"[HOST] {label}: {oldv} -> {newv}")
            return newv
        def _sub_plain(m: re.Match) -> str:
            oldv, newv = m.group(0), new
            if oldv != newv: notes.append(f"[HOST] {label}: {oldv} -> {newv}")
            return newv
        all_text, _ = rx_port.subn(_sub_port, all_text)
        all_text, _ = rx_plain.subn(_sub_plain, all_text)
        return all_text

    if reality_server_name:
        text = _sub_all(text, "www.habbo.com", reality_server_name, "Reality")
    if shadowtls_server_name:
        text = _sub_all(text, "www.shamela.ws", shadowtls_server_name, "ShadowTLS")
    return text

def read_changes() -> Dict[str, str]:
    if not CHANGES_JSON.exists():
        raise FileNotFoundError(f"Нет {CHANGES_JSON} — сперва должен отработать скрипт 10.")
    with open(CHANGES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def read_domains_from_db() -> Tuple[Optional[str], Optional[str]]:
    """Берём reality/shadowtls из таблицы fakedomain (создана 10-м скриптом)."""
    if not DB_PATH.exists():
        return None, None
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT reality, shadowtls FROM fakedomain ORDER BY ROWID DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return None, None
    return row[0], row[1]

def apply_haproxy_changes(
    haproxy_path: str,
    path_changes: Optional[Dict[str, str]] = None,
    reality_server_name: Optional[str] = None,
    shadowtls_server_name: Optional[str] = None,
    out_path: Optional[str] = None,
) -> Tuple[str, List[str]]:
    with open(haproxy_path, "r", encoding="utf-8") as f:
        text = f.read()

    notes: List[str] = []

    if path_changes:
        text = _replace_paths(text, path_changes, notes)

    if reality_server_name or shadowtls_server_name:
        text = _replace_domains(text, reality_server_name, shadowtls_server_name, notes)

    # Бэкап и запись
    write_path = out_path or haproxy_path
    if os.path.abspath(write_path) == os.path.abspath(haproxy_path):
        shutil.copy2(haproxy_path, haproxy_path + ".bak")
        notes.append(f"[BACKUP] {haproxy_path}.bak создан")

    with open(write_path, "w", encoding="utf-8") as f:
        f.write(text)
    notes.append(f"[WRITE] {write_path} обновлён")

    return text, notes

def main():
    paths = read_changes()  # dict {tag: new_path}
    reality, shadow = read_domains_from_db()
    if not reality or not shadow:
        print("[WARN] Домены для Reality/ShadowTLS не найдены в БД — доменные замены пропущены.")
    _, log = apply_haproxy_changes(
        haproxy_path=str(HAPROXY_CFG),
        path_changes=paths,
        reality_server_name=reality,
        shadowtls_server_name=shadow,
        out_path=str(HAPROXY_CFG),
    )
    print("\n".join(log))

if __name__ == "__main__":
    main()
