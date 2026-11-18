#!/usr/bin/env bash
# campaign_wake.sh — inject the continuation prompt into the campaign session,
# FOREVER (until a stop file appears or the user stops the unit).
#
# The loop is perpetual by design (user directive): when the agent's turn
# returns, the prompt is re-injected immediately so the campaign never idles.
#
# Model chain:
#   Primary: opencode/glm-5.3-flash-free — used NORMALLY, every wake.
#   Fallback: nvidia/minimaxai/minimax-m3.1-flash#thinking — ONLY when the
#   free route is actually exhausted (quota/limit), i.e. the run failed
#   (rc != 0, or output starts with an error JSON) AND a limit signature is
#   present. A successful run never triggers the fallback (the 02:43 bug).
set -u
SESSION=ses_e40ca51eeffeZH1jOA0zacun2v
PROJ=/home/bandoc/Downloads/opencode
PROMPT_FILE=$PROJ/harness/CONTINUE_PROMPT.md
LOG=$PROJ/harness/campaign_wake.log
LOCK=/tmp/opencode/harness/campaign_wake.lock
STOPFILE=$PROJ/harness/STOP_WAKE
OC=/home/bandoc/.opencode/bin/opencode

FREE_MODEL='opencode/glm-5.3-flash-free'
FALLBACK_MODEL='nvidia/minimaxai/minimax-m3.1-flash#thinking'
LIMIT_RE='Free usage limit reached|usage limit|rate limit|quota|429|limit reached|exceeded your|daily limit'
SLEEP_BETWEEN=45          # seconds between re-injections (agent turn boundary)

mkdir -p /tmp/opencode/harness
exec 9>"$LOCK"
flock -n 9 || { echo "$(date -u '+%F %T') skip: previous wake still running" >>"$LOG"; exit 0; }

TMP=""
cleanup() { [ -n "$TMP" ] && rm -f "$TMP"; }
trap cleanup EXIT INT TERM

cd "$PROJ"
if ! "$OC" session list 2>/dev/null | grep -q "$SESSION"; then
  echo "$(date -u '+%F %T') ABORT: session $SESSION not found" >>"$LOG"
  exit 1
fi

echo "$(date -u '+%F %T') campaign loop START (model $FREE_MODEL, fallback $FALLBACK_MODEL)" >>"$LOG"

ITER=0
while true; do
  [ -f "$STOPFILE" ] && { echo "$(date -u '+%F %T') stop file present — campaign loop exiting" >>"$LOG"; break; }
  ITER=$((ITER + 1))
  TMP=$(mktemp /tmp/opencode/harness/wake_out.XXXXXX)
  "$OC" run --auto -m "$FREE_MODEL" -s "$SESSION" "$(cat "$PROMPT_FILE")" >"$TMP" 2>&1
  rc=$?
  cat "$TMP" >>"$LOG"

  free_failed=0
  firstline=$(head -c 2000 "$TMP" | head -1)
  case "$firstline" in *'"error"'*) free_failed=1 ;; esac
  [ "$rc" -ne 0 ] && free_failed=1
  limit_hit=0
  grep -qiE "$LIMIT_RE" "$TMP" && limit_hit=1

  if [ "$free_failed" = 1 ] && [ "$limit_hit" = 1 ]; then
    echo "$(date -u '+%F %T') iter $ITER: free route exhausted (rc=$rc) — switching to $FALLBACK_MODEL" >>"$LOG"
    rm -f "$TMP"; TMP=""
    "$OC" run --auto -m "$FALLBACK_MODEL" -s "$SESSION" "$(cat "$PROMPT_FILE")" >>"$LOG" 2>&1
    rc=$?
  elif [ "$free_failed" = 1 ]; then
    echo "$(date -u '+%F %T') iter $ITER: free route failed without limit signature (rc=$rc) — no fallback" >>"$LOG"
  else
    echo "$(date -u '+%F %T') iter $ITER: free route served (rc=$rc, $(wc -c <"$TMP") B) — no fallback" >>"$LOG"
  fi
  rm -f "$TMP"; TMP=""
  echo "$(date -u '+%F %T') iter $ITER done rc=$rc; re-injecting in ${SLEEP_BETWEEN}s" >>"$LOG"
  sleep "$SLEEP_BETWEEN"
done

echo "$(date -u '+%F %T') campaign loop END after $ITER iterations" >>"$LOG"
exit 0
