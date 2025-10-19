#!/usr/bin/env bash
set -euo pipefail

CFG_DIR="${CFG_DIR:-/etc/haproxy}"      # куда распаковываешь haproxy-etc.tar.gz
CFG_MAIN="${CFG_MAIN:-${CFG_DIR}/haproxy.cfg}"
BIN="${BIN:-/usr/sbin/haproxy}"
INTERVAL="${INTERVAL:-2}"               # период опроса (сек)
DEBOUNCE="${DEBOUNCE:-2}"               # «устаканить» изменения (сек)

hash_cfg() {
  # хешируем все .cfg в каталоге (порядок фиксируем sort'ом)
  find "$CFG_DIR" -type f -name '*.cfg' -print0 \
    | sort -z \
    | xargs -0 sha256sum | sha256sum | awk '{print $1}'
}

log(){ echo "[haproxy-reloader] $*"; }

# начальное состояние
last="$(hash_cfg || echo "INIT")"
log "watching $CFG_DIR (main: $CFG_MAIN), interval=${INTERVAL}s"

while sleep "$INTERVAL"; do
  cur="$(hash_cfg || echo "ERR")"
  [[ "$cur" == "$last" ]] && continue

  # дебаунс: ждём DEBOUNCE и проверяем, что хеш тот же
  sleep "$DEBOUNCE"
  cur2="$(hash_cfg || echo "ERR")"
  [[ "$cur2" != "$cur" ]] && { log "changes still flowing, waiting…"; last="$cur2"; continue; }

  log "detected change, validating ${CFG_MAIN}…"
  if "$BIN" -c -f "$CFG_MAIN" >/dev/null 2>&1; then
    log "config valid, restarting via supervisor"
    supervisorctl restart haproxy || log "supervisorctl restart failed"
    last="$cur2"
  else
    log "config INVALID, not restarting. Run: $BIN -c -f $CFG_MAIN"
    last="$cur2"
  fi
done
