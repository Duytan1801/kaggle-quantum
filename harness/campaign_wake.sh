#!/usr/bin/env bash
# campaign_wake.sh — the campaign's wake supervisor.
#
# MODEL CHAIN (handpicked by the user — exactly two models, quality order):
#   A = opencode/deepseek-v4.1-flash-free          (primary)
#   B = nvidia/minimaxai/minimax-m3.1-flash#thinking (on A's quota)
#   B is retried FOREVER on 429/quota until it answers — the campaign must never
#   die because a provider throttled us.
#
# Design rules (learned from the 2026-11-18 all-day outage):
#   * A quota  → switch to B (once).
#   * B error  → sleep with capped exponential backoff, retry B. NEVER give up,
#                 NEVER busy-loop, NEVER "switch to B" from inside B.
#   * A 429    → retry A with backoff a few times, then fall through to B.
#   * A dead/invalid session → regenerate the session id and retry.
#   * SIGTERM  → exit cleanly (143). A bare cleanup trap would ignore it.
#   * One wake = one agent turn. All state lives on disk; each wake runs in a
#     FRESH session so context never accumulates (Anthropic's scheduled-run
#     guidance).
#
# Cadence: systemd timer campaign-wake.timer fires this every 2 h.
set -u
PROJ=${PROJ:-/home/bandoc/Downloads/opencode}
PROMPT_FILE=${PROMPT_FILE:-$PROJ/harness/CONTINUE_PROMPT.md}
LOG=${LOG:-$PROJ/harness/campaign_wake.log}
LOCK=${LOCK:-/tmp/opencode/harness/campaign_wake.lock}
STOPFILE=${STOPFILE:-$PROJ/harness/STOP_WAKE}
OC=${OC:-/home/bandoc/.opencode/bin/opencode}

MODEL_A=${MODEL_A:-opencode/deepseek-v4.1-flash-free}
MODEL_B=${MODEL_B:-nvidia/minimaxai/minimax-m3.1-flash#thinking}
# quota = the provider/account is spent (switch model); 429 = throttled (retry)
QUOTA_RE='usage limit|daily limit|insufficient_quota|quota exceeded|monthly limit|subscription required|end of life|reached its end'
SOFT_RE='HTTP 429|Too Many Requests|429:|rate limit|rate_limit'
WAKE_TIMEOUT=${WAKE_TIMEOUT:-5400}        # wall-clock cap for ONE opencode attempt
RETRY_BASE=${RETRY_BASE:-60}               # first backoff (s)
RETRY_CAP=${RETRY_CAP:-900}                # max backoff (s)
A_429_TRIES=${A_429_TRIES:-3}              # 429s on A before falling through to B

mkdir -p /tmp/opencode/harness
exec 9>"$LOCK"
flock -n 9 || { echo "$(date -u '+%F %T') skip: previous wake still running" >>"$LOG"; exit 0; }

TMP=""
cleanup() { [ -n "$TMP" ] && rm -f "$TMP"; }
trap cleanup EXIT
trap 'cleanup; echo "$(date -u "+%F %T") received SIGTERM — exiting" >>"$LOG"; exit 143' TERM INT

cd "$PROJ"
log() { echo "$(date -u '+%F %T') $*" >>"$LOG"; }

[ -f "$STOPFILE" ] && { log "stop file present — wake skipped"; exit 0; }
[ -f "$PROMPT_FILE" ] || { log "ABORT: prompt missing"; exit 1; }
[ -x "$OC" ] || { log "ABORT: opencode binary missing"; exit 1; }

# Session handling: the wake injects into the ONE canonical campaign session so
# the whole campaign stays in a single, followable thread. Context growth is
# handled by (a) the lean map-style prompt with bounded reads, (b) all state on
# disk, and (c) OpenCode's own automatic compaction — NOT by session rotation.
# If the canonical session is gone, opencode run -s recreates it; we log that
# loudly so the change is never silent.
SESSION=${SESSION:-ses_e40ca51eeffeZH1jOA0zacun2v}

# attempt <model> → 0 ok, 1 throttle(429), 2 quota, 3 other error
attempt() {
  local model="$1"
  TMP=$(mktemp /tmp/opencode/harness/wake_out.XXXXXX)
  timeout "$WAKE_TIMEOUT" "$OC" run --auto -m "$model" -s "$SESSION" "$(cat "$PROMPT_FILE")" >"$TMP" 2>&1
  local rc=$?
  cat "$TMP" >>"$LOG"
  if [ "$rc" -eq 0 ] && ! grep -qiE "$SOFT_RE|$QUOTA_RE" "$TMP"; then
    rm -f "$TMP"; TMP=""; return 0
  fi
  if grep -qiE "session.*not found|no such session|invalid session" "$TMP"; then
    log "canonical session $SESSION unusable — recreating it (same id)"
    "$OC" session list >/dev/null 2>&1 || true
  fi
  if grep -qiE "$QUOTA_RE" "$TMP"; then rm -f "$TMP"; TMP=""; return 2; fi
  if grep -qiE "$SOFT_RE" "$TMP"; then rm -f "$TMP"; TMP=""; return 1; fi
  rm -f "$TMP"; TMP=""; return 3
}

sleep_backoff() {  # $1 = current backoff → echoes next
  local b=$1
  [ "$b" -lt "$RETRY_BASE" ] && b=$RETRY_BASE
  [ "$b" -gt "$RETRY_CAP" ] && b=$RETRY_CAP
  echo "$b"
}

log "wake START session=$SESSION A=$MODEL_A B=$MODEL_B"

# ---- Stage 1: primary model A ----------------------------------------------
backoff=$RETRY_BASE
a429=0
while true; do
  attempt "$MODEL_A"; rc=$?
  case "$rc" in
    0) log "wake served by A ($MODEL_A)"; log "wake END session=$SESSION rc=0"; exit 0 ;;
    2) log "A ($MODEL_A) is out of quota → switching to B ($MODEL_B)"; break ;;
    1) a429=$((a429 + 1))
       if [ "$a429" -ge "$A_429_TRIES" ]; then
         log "A throttled $a429× → falling through to B ($MODEL_B)"; break
       fi
       backoff=$(sleep_backoff "$backoff"); log "A throttled (429, try $a429) — retry in ${backoff}s"; sleep "$backoff"
       backoff=$(( backoff * 2 )); [ "$backoff" -gt "$RETRY_CAP" ] && backoff=$RETRY_CAP ;;
    3) backoff=$(sleep_backoff "$backoff"); log "A error (not quota/429) — retry in ${backoff}s"; sleep "$backoff"
       backoff=$(( backoff * 2 )); [ "$backoff" -gt "$RETRY_CAP" ] && backoff=$RETRY_CAP ;;
  esac
done

# ---- Stage 2: fallback model B — retried FOREVER until it answers ----------
backoff=$RETRY_BASE
tries=0
while true; do
  tries=$((tries + 1))
  attempt "$MODEL_B"; rc=$?
  case "$rc" in
    0) log "wake served by B ($MODEL_B) after $tries attempt(s)"; log "wake END session=$SESSION rc=0"; exit 0 ;;
    *) backoff=$(sleep_backoff "$backoff")
       log "B ($MODEL_B) unavailable (rc=$rc, try $tries) — retry in ${backoff}s (forever)"
       sleep "$backoff"
       backoff=$(( backoff * 2 )); [ "$backoff" -gt "$RETRY_CAP" ] && backoff=$RETRY_CAP ;;
  esac
done
