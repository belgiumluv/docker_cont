#!/usr/bin/env bash
set -euo pipefail

BIN="/opt/vpnserver"
DB="${DB_PATH:-/var/lib/bd/bd.db}"

log(){ echo "[run-vpnserver] $*"; }

# Проверки наличия
if [ ! -x "$BIN" ]; then
  log "FATAL: $BIN not found or not executable"
  exit 1
fi
if [ ! -f "$DB" ]; then
  log "WARN: DB not found at $DB — creating empty SQLite DB"
  mkdir -p "$(dirname "$DB")"
  sqlite3 "$DB" "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);" || true
fi

# Попытка понять, поддерживает ли бинарник флаг --db
if "$BIN" --help 2>&1 | grep -qiE '\-\-db(=|\s)'; then
  log "Starting with argument --db=$DB"
  exec "$BIN" --db "$DB"
else
  log "Starting with env DB_PATH=$DB"
  export DB_PATH="$DB"
  exec "$BIN"
fi
