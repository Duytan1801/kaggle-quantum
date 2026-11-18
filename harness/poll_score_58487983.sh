#!/usr/bin/env bash
# poll_score_58487983.sh — poll until the v131 submission scores.
set -u
export PATH=$HOME/.local/bin:$PATH
for i in $(seq 1 240); do
  sleep 60
  ROW=$(kaggle competitions submissions -c google-verifiable-quantum-circuit-compilation 2>/dev/null | sed -n '3p')
  if echo "$ROW" | grep -q COMPLETE; then
    SC=$(echo "$ROW" | grep -oE "[0-9]+\.[0-9]+ *$" | tail -1)
    echo "[$(date -u)] v131 (58487983) SCORED: $SC" >> /tmp/opencode/score_v131.log
    echo "$ROW" | grep -oE "[0-9]{8} .*" | head -c 400 >> /tmp/opencode/score_v131.log
    exit 0
  fi
done
echo "[$(date -u)] v131 score poll TIMEOUT" >> /tmp/opencode/score_v131.log
