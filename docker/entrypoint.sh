#!/usr/bin/env bash
set -euo pipefail

log(){ echo "[entrypoint] $*"; }

# Проверки на наличие бинарей/конфигов, которые нужны рантайм-сервисам
if [ ! -x /vpn/sing-box ]; then
  echo "[ERR] /vpn/sing-box not found or not executable" >&2
  exit 1
fi

# === ONE-SHOT СТАДИЯ ===
# 1) setconfiguration: кладет serverlist.json в /vpn, читает публичный IP, пишет /vpn/server_configuration.json и /vpn/domain.txt и обновляет SQLite.
if ! /usr/bin/python3 /app/scripts/04_setconfiguration.py; then
  echo "[ERR] setconfiguration failed. Проверь /app/configs/serverlist.json и доступ к интернету для api.ipify.org" >&2
  exit 1
fi

# 2) mutate_server_json: генерирует ключи/пароли, правит /vpn/server.json, записывает chosen fake domains в БД и формирует /vpn/changes_dict.json
if ! /usr/bin/python3 /app/scripts/10_mutate_server_json.py; then
  echo "[ERR] mutate_server_json failed" >&2
  exit 1
fi

# 3) apply_haproxy_changes: применяет изменения путей и доменов в /etc/haproxy/haproxy.cfg
if ! /usr/bin/python3 /app/scripts/11_apply_haproxy_changes.py; then
  echo "[ERR] apply_haproxy_changes failed" >&2
  exit 1
fi

# Можно добавить быструю валидацию конфигов (не обязательно)
if ! /usr/sbin/haproxy -c -f /etc/haproxy/haproxy.cfg; then
  echo "[ERR] haproxy.cfg invalid after apply" >&2
  exit 1
fi
if ! /vpn/sing-box check -c /vpn/server.json; then
  echo "[ERR] sing-box server.json invalid after mutate" >&2
  exit 1
fi

log "one-shot stage complete; starting supervisor..."

# === РАНТАЙМ СТАДИЯ ===
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
