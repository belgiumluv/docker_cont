#!/usr/bin/env bash
set -euo pipefail

DB_PATH="/var/lib/bd/bd.db"
DB_DIR="$(dirname "$DB_PATH")"

mkdir -p "$DB_DIR"

# Если базы нет — создаём и добавляем тестовую таблицу
if [ ! -f "$DB_PATH" ]; then
  echo "[sqlite-init] creating database at $DB_PATH"
  sqlite3 "$DB_PATH" "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);"
  echo "[sqlite-init] database created."
else
  echo "[sqlite-init] database already exists."
fi

# держим процесс живым, чтобы supervisor не перезапускал постоянно
tail -f /dev/null
