#!/usr/bin/env bash
set -euo pipefail


# Проверим, что бинарник есть и исполняемый
if [ ! -x /vpn/sing-box ]; then
  echo "[ERR] /vpn/sing-box not found or not executable" >&2
  exit 1
fi

# Проверим, что конфиг существует
if [ ! -f /vpn/server.json ]; then
  echo "[ERR] /vpn/server.json not found" >&2
  exit 1
fi

# Запускаем supervisor (поднимет sing-box и вотчер)
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf

python /app/scripts/04_setconfiguration.py