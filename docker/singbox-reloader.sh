#!/usr/bin/env bash
set -euo pipefail

CFG="${CFG:-/vpn/server.json}"
BIN="${BIN:-/vpn/sing-box}"
INTERVAL="${INTERVAL:-2}"
DEBOUNCE="${DEBOUNCE:-2}"

log(){ echo "[singbox-reloader] $*"; }

hash_cfg() {
  sha256sum "$CFG" 2>/dev/null | awk '{print $1}'
}

last="$(hash_cfg || echo "INIT")"
log "watching $CFG, interval=${INTERVAL}s"

while sleep "$INTERVAL"; do
  cur="$(hash_cfg || echo "ERR")"
  [[ "$cur" == "$last" ]] && continue

  sleep "$DEBOUNCE"
  cur2="$(hash_cfg || echo "ERR")"
  [[ "$cur2" != "$cur" ]] && { log "changes still flowing, waiting…"; last="$cur2"; continue; }

  log "detected change, validating…"
  if "$BIN" check -c "$CFG" >/dev/null 2>&1; then
    log "config valid, restarting via supervisor"
    supervisorctl restart singbox || log "supervisorctl restart failed"
    last="$cur2"
  else
    log "config INVALID, not restarting. Run: $BIN check -c $CFG"
    last="$cur2"
  fi
done
