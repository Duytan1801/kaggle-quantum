#!/usr/bin/env bash
# poll_submission.sh — background poller for one Kaggle submission ref.
# Usage: poll_submission.sh <ref> <max_minutes> [logfile]
set -u
REF=${1:?ref}
MAX=${2:-90}
LOG=${3:-/tmp/opencode/sub_poll_${REF}.log}
KG=/home/bandoc/Downloads/opencode/qaenv/bin/kaggle
for i in $(seq 1 $((MAX*2))); do
  line=$("$KG" competitions submissions -c google-verifiable-quantum-circuit-compilation 2>/dev/null | grep "$REF" || true)
  echo "$(date -u) ${line:-<no line>}" >> "$LOG"
  case "$line" in
    *COMPLETE*) echo "$(date -u) DONE ${line}" >> "$LOG"; exit 0;;
    *ERROR*|*FAIL*) echo "$(date -u) FAILED ${line}" >> "$LOG"; exit 1;;
  esac
  sleep 30
done
echo "$(date -u) TIMEOUT" >> "$LOG"
exit 2
