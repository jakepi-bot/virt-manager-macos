#!/usr/bin/env bash
# GUI launch smoke test for virt-manager on macOS.
#
# Usage: smoke-test-macos.sh "<command to launch>" [alive_seconds]
# Env:   SMOKE_LOG=<path>   (default /tmp/vm-smoke.log)
#
# Pass criteria:
#   1. the process is still running after alive_seconds (GTK main loop reached), AND
#   2. the captured log contains no Python traceback / abort / macOS fork-safety trip.
set -u

CMD="$1"
ALIVE="${2:-20}"
LOG="${SMOKE_LOG:-/tmp/vm-smoke.log}"

echo "== launch: $CMD"
echo "== log:    $LOG"
: > "$LOG"

eval "$CMD" >"$LOG" 2>&1 &
PID=$!

rc=0
sleep "$ALIVE"
if kill -0 "$PID" 2>/dev/null; then
  echo "OK: alive after ${ALIVE}s (GUI main loop running)"
  kill "$PID" 2>/dev/null || true
  sleep 2
  kill -9 "$PID" 2>/dev/null || true
else
  echo "FAIL: process exited before ${ALIVE}s"
  rc=1
fi
wait "$PID" 2>/dev/null || true

# best-effort cleanup of any surviving children (CI boxes are ephemeral)
pkill -f "virt-manager" >/dev/null 2>&1 || true

echo "----- log (tail 120) -----"
tail -n 120 "$LOG"
echo "--------------------------"

if grep -Eq "Traceback \(most recent call last\)|Abort trap|may have been in progress in another thread when fork|exited with code" "$LOG"; then
  echo "FAIL: crash signature found in log"
  rc=1
fi

if ! grep -q "virt-manager version" "$LOG"; then
  echo "WARN: expected 'virt-manager version' debug line not found in log"
fi

exit "$rc"
