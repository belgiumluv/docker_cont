#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import os
import shutil
from typing import Dict, List, Tuple, Optional

# Теги, для которых действительно есть path_beg в haproxy.cfg
TAG_TO_BACKENDS: Dict[str, List[str]] = {
    "v10-vless-ws": ["v10-vless-ws"],
    "v10-vless-grpc": ["v10-vless-grpc", "v10-vless-grpc-http"],
    "v10-vless-httpupgrade": ["v10-vless-httpupgrade"],
    "v10-vless-tcp": ["v10-vless-tcp", "v10-vless-tcp-http"],


    "v10-vmess-ws": ["v10-vmess-ws"],
    "v10-vmess-grpc": ["v10-vmess-grpc", "v10-vmess-grpc-http"],
    "v10-vmess-httpupgrade": ["v10-vmess-httpupgrade"],
    "v10-vmess-tcp": ["v10-vmess-tcp", "v10-vmess-tcp-http"],

    "v10-trojan-ws": ["v10-trojan-ws"],
    "v10-trojan-grpc": ["v10-trojan-grpc", "v10-trojan-grpc-http"],
    "v10-trojan-httpupgrade": ["v10-trojan-httpupgrade"],
    "v10-trojan-tcp": ["v10-trojan-tcp", "v10-trojan-tcp-http"],
}

def _ensure_leading_slash(p: str) -> str:
    p = (p or "").strip()
    return p if (not p or p.startswith("/")) else f"/{p}"

def _backend_line_regex(backend_name: str) -> re.Pattern:
    # Ищем: use_backend <backend_name> if { path_beg /OLD }
    return re.compile(rf'(use_backend\s+{re.escape(backend_name)}\s+if\s+\{{\s*path_beg\s+)(/[^ \}}\n]+)')

def _replace_paths(text: str, paths: Dict[str, str], notes: List[str]) -> str:
    for tag, new_val in (paths or {}).items():
        backends = TAG_TO_BACKENDS.get(tag)
        if not backends:
            notes.append(f"[WARN] Неизвестный тег '{tag}' — пропускаю.")
            continue

        new_path = _ensure_leading_slash(str(new_val))
        for be in backends:
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
    """
    Меняем домены только если они переданы.
    Реальность в конфиге встречается как:
      - req.ssl_sni -i www.habbo.com
      - hdr(host) -i www.habbo.com
      - www.habbo.com:80 (для http-бэкенда-демаскировки)
      - просто www.habbo.com
    ShadowTLS встречается как:
      - hdr(host) -i www.shamela.ws
      - www.shamela.ws:80
      - просто www.shamela.ws
    """

    def sub_domain(all_text: str, old: str, new: str, label: str) -> str:
        # Сначала ":" с портом, потом голый домен
        rx_port = re.compile(rf'\b{re.escape(old)}:80\b')
        rx_plain = re.compile(rf'\b{re.escape(old)}\b')

        def _sub_port(m: re.Match) -> str:
            oldv = m.group(0)
            newv = f"{new}:80"
            if oldv != newv:
                notes.append(f"[HOST] {label}: {oldv} -> {newv}")
            return newv

        def _sub_plain(m: re.Match) -> str:
            oldv = m.group(0)
            newv = new
            if oldv != newv:
                notes.append(f"[HOST] {label}: {oldv} -> {newv}")
            return newv

        all_text, _ = rx_port.subn(_sub_port, all_text)
        all_text, _ = rx_plain.subn(_sub_plain, all_text)
        return all_text

    if reality_server_name:
        # заменяем все вхождения habbo
        text = sub_domain(text, "www.habbo.com", reality_server_name, "Reality")

    if shadowtls_server_name:
        # заменяем все вхождения shamela
        text = sub_domain(text, "www.shamela.ws", shadowtls_server_name, "ShadowTLS")

    return text

def apply_haproxy_changes(
    haproxy_path: str,
    path_changes: Optional[Dict[str, str]] = None,
    reality_server_name: Optional[str] = None,
    shadowtls_server_name: Optional[str] = None,
    out_path: Optional[str] = None,
    dry_run: bool = False,
) -> Tuple[str, List[str]]:
    """
    Меняет конфиг haproxy:
      - paths: словарь {tag: "/new_path"} — меняем только указанные теги.
      - reality_server_name: опционально заменить домен для Reality.
      - shadowtls_server_name: опционально заменить домен для ShadowTLS.
    Ничего не указали — ничего не меняем.

    Возвращает (новый_текст, лог_изменений).
    """
    with open(haproxy_path, "r", encoding="utf-8") as f:
        text = f.read()

    notes: List[str] = []

    # 1) пути по тегам
    if path_changes:
        text = _replace_paths(text, path_changes, notes)

    # 2) домены (только если заданы)
    if reality_server_name or shadowtls_server_name:
        text = _replace_domains(text, reality_server_name, shadowtls_server_name, notes)

    if dry_run:
        return text, notes

    # Запись с бэкапом
    write_path = out_path or haproxy_path
    if os.path.abspath(write_path) == os.path.abspath(haproxy_path):
        shutil.copy2(haproxy_path, haproxy_path + ".bak")
        notes.append(f"[BACKUP] Создан бэкап: {haproxy_path}.bak")

    with open(write_path, "w", encoding="utf-8") as f:
        f.write(text)
    notes.append(f"[WRITE] Записано: {write_path}")

    return text, notes


# --- Пример запуска как скрипта ---
ROOT_PREFIX = os.getenv("ROOT_PREFIX", "")
HAP_PATH = os.path.join(ROOT_PREFIX, "etc/haproxy/haproxy.cfg")   # будет /host/etc/haproxy/haproxy.cfg
CHANGES_PATH = os.path.join(ROOT_PREFIX, "vpn/changes_dict.json") # будет /host/opt/changes_dict.json

DOMAIN_PATH = os.path.join(ROOT_PREFIX, "vpn/masq_domain_list.json") # будет /host/opt/changes_dict.json

if __name__ == "__main__":
    with open(DOMAIN_PATH, 'r', encoding='utf-8') as file_1:
        domain = json.load(file_1)
    hap_path = HAP_PATH
    with open(CHANGES_PATH, 'r', encoding='utf-8') as file:
        path_changes = json.load(file)

    reality = None
    shadowtls = None

    _, log = apply_haproxy_changes(
        haproxy_path=hap_path,
        path_changes=path_changes,
        reality_server_name=domain[0],
        shadowtls_server_name=domain[1],
        out_path=hap_path,
        dry_run=False
    )
    print("\n".join(log))