#!/usr/bin/env bash
set -euo pipefail

CFG="/vpn/server.json"
BIN="/vpn/sing-box"

echo "[watch] watching ${CFG} for changes..."
# Первичная проверка конфига при старте
if ! "${BIN}" check -c "${CFG}" >/dev/null 2>&1; then
  echo "[watch] initial config is INVALID, fix /vpn/server.json"
fi

# Непрерывно ждём изменений файла и перезапускаем sing-box через supervisor,
# только если конфиг валиден
while inotifywait -e close_write,move,create,delete "${CFG%/*}"; do
  if [ -f "${CFG}" ] && "${BIN}" check -c "${CFG}" >/dev/null 2>&1; then
    echo "[watch] config changed & valid -> restarting singbox"
    supervisorctl restart singbox || true
  else
    echo "[watch] config changed but INVALID -> not restarting"
  fi
done
