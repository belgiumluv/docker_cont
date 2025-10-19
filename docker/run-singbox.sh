#!/usr/bin/env bash
set -euo pipefail
BIN="/vpn/sing-box"
CFG="/vpn/server.json"

# На всякий случай — права на бинарник
chmod +x "$BIN" || true
if ! [ -x "$BIN" ]; then
  echo "[FATAL] $BIN not executable"
  exit 1
fi

# Проверяем конфиг перед запуском
if ! "$BIN" check -c "$CFG"; then
  echo "[FATAL] invalid config: $CFG"
  exit 1
fi

# Запускаем
exec "$BIN" run -c "$CFG"
