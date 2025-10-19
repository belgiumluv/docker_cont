#!/usr/bin/env bash
set -euo pipefail

CFG="/haproxy/haproxy.cfg"
BIN="/haproxy/haproxy"

echo "[watch-haproxy] watching ${CFG} for changes..."

# Проверяем конфиг и запускаем в цикл
while inotifywait -e close_write,move,create,delete "${CFG%/*}"; do
  if [ -f "$CFG" ]; then
    if "$BIN" -c -f "$CFG" >/dev/null 2>&1; then
      echo "[watch-haproxy] config valid, restarting haproxy"
      supervisorctl restart haproxy || true
    else
      echo "[watch-haproxy] config invalid — not restarting"
    fi
  fi
done
