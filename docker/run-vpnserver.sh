#!/usr/bin/env bash
set -euo pipefail

BIN="${BIN:-/opt/vpnserver}"
DB="${DB_PATH:-/var/lib/bd/bd.db}"
ADDR="${ADDR:-0.0.0.0:8080}"   # внешний адрес/порт, куда слушать

log(){ echo "[run-vpnserver] $*"; }

if [ ! -x "$BIN" ]; then
  log "FATAL: $BIN not found or not executable"
  exit 1
fi

# Если базы нет — создаём пустую SQLite
if [ ! -f "$DB" ]; then
  log "WARN: DB not found at $DB — creating empty SQLite DB"
  mkdir -p "$(dirname "$DB")"
  sqlite3 "$DB" "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);" || true
fi

ARGS=()

# Безопасно проверяем поддержку флагов, не зависаем
HELP="$(timeout 2 "$BIN" --help 2>&1 || true)"

if echo "$HELP" | grep -qiE '\-\-db(=|\s)'; then
  ARGS+=(--db "$DB")
else
  export DB_PATH="$DB"
fi

if echo "$HELP" | grep -qiE '\-\-addr(=|\s)'; then
  ARGS+=(--addr "$ADDR")
fi

log "Starting: $BIN ${ARGS[*]:-} (DB=$DB, ADDR=$ADDR)"
exec "$BIN" "${ARGS[@]}"
