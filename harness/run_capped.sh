#!/usr/bin/env bash
# run_capped.sh — run any command inside a user-owned cgroup memory cage.
#
# NO ROOT REQUIRED: systemd --user manages your own delegated cgroup subtree,
# and the kernel kills offending processes INSIDE the cage only — so a runaway
# script can never take the desktop down with it (the 2026-11-09 OOM freeze).
#
# Usage:
#   run_capped.sh [CAP] cmd args...        # CAP as systemd size (default 4G)
# examples:
#   run_capped.sh python3 script.py        # 4G cage   (default)
#   run_capped.sh 512M python3 train.py    # 512M cage
#
# Behaviour:
#   * MemoryMax   = CAP (hard kill wall, kernel OOM-kills the cage's members)
#   * MemoryHigh  = 85% of CAP (soft wall: reclaim+throttle before hard kill)
#   * MemorySwapMax = 1G (can never eat the whole 2G swapfile)
#   * OOMScoreAdjust = 500 (if the SYSTEM-wide OOM ever fires, this process
#     is chosen as victim ahead of gnome/chrome)
#   * fallback (no user systemd reachable): ulimit -v cap instead
# Exit code = the child's exit code (137 = cage OOM-kill).
set -u
CAP_IN=${1:-}; shift 2>/dev/null || true
if [ -z "${CAP_IN:-}" ]; then CAP_IN=4G; else :; fi
case "$CAP_IN" in
  *[!0-9GMTgmbKk]*) echo "run_capped: bad cap '$CAP_IN'" >&2; exit 64;;
esac
CAP_BYTES=$(numfmt --from=iec "$CAP_IN" 2>/dev/null || echo "")
if [ -n "$CAP_BYTES" ] && [ "$CAP_BYTES" -ge 33554432 ]; then          # ≥ 32 MiB
  HIGH_BYTES=$(( CAP_BYTES * 85 / 100 ))
else
  CAP_BYTES=4294967296; HIGH_BYTES=3650722201; CAP_IN=4G
fi
SWAP_BYTES=$(numfmt --from=iec "${CAP_SWAP:-1G}" 2>/dev/null || echo 1073741824)

if command -v systemd-run >/dev/null 2>&1 && [ -n "${XDG_RUNTIME_DIR:-}" ] \
   && [ -S "${XDG_RUNTIME_DIR}/systemd/private" ] 2>/dev/null; then
  # limits passed as RAW BYTES (locale-proof, e.g. "1,7G" is rejected by systemd)
  exec systemd-run --user --scope --quiet \
    -p "MemoryMax=$CAP_BYTES" \
    -p "MemoryHigh=$HIGH_BYTES" \
    -p "MemorySwapMax=$SWAP_BYTES" \
    -- bash -c 'echo 500 > /proc/$$/oom_score_adj 2>/dev/null; exec "$@"' _ "$@"
else
  echo "run_capped: user systemd unreachable → ulimit -v fallback ($CAP_IN VA)" >&2
  ulimit -v $(( CAP_BYTES / 1024 )) 2>/dev/null || true
  exec "$@"
fi
