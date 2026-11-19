#!/usr/bin/env bash
# harvest_kernels.sh — SUPERSEDED by harness/watch_public.py (2026-11-19).
#
# This script was never running as a service and duplicated part of the radar's
# job (and only the KERNEL channel — the channel where competitors are LEAST
# likely to release, since they publish their trees as DATASETS).  It also kept
# its state in /tmp, which a reboot wipes.
#
# The radar now lives in harness/watch_public.py:
#   * valid Kaggle sort keys only, every poll VALIDATED (never a silent no-op)
#   * kernels AND datasets AND a self-growing publisher list
#   * durable state in work/harvest/ (survives reboot)
#   * output = work/harvest/PENDING.tsv, which every wake reads
#
# Do NOT start this script.  It is kept only as a record of the old mechanism.
set -u
ROOT=/home/bandoc/Downloads/opencode
KG=kaggle
PY=$ROOT/work/toolchain/venv/bin/python
KICK=$ROOT/work/toolchain/kickmix
VER=$ROOT/work/toolchain/verifiers/invsqrt/verify_submission_invsqrt.py
COMP=google-verifiable-quantum-circuit-compilation
DIR=/tmp/opencode/harvest
KDIR=$DIR/kernels
ART=$DIR/artifacts
LOG=$DIR/harvest_kernels.log
SEEN=$DIR/kernels_seen.txt
FOUND=$DIR/found_artifacts.tsv
mkdir -p "$KDIR" "$ART"
[ -f "$SEEN" ] || : > "$SEEN"
[ -f "$FOUND" ] || printf 'when\tkind\tsha\tbytes\tinfo\n' > "$FOUND"
BEST_COST=${BEST_COST:-75006.3658334007}

log() { echo "$(date -u '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

echo "harvest_kernels.sh is SUPERSEDED by harness/watch_public.py — run that instead." >&2
exit 2

while :; do
  "$KG" kernels list --competition "$COMP" --sort-by dateRun --page-size 40 2>/dev/null \
    | awk 'NR>2 && $1 ~ /^[a-zA-Z0-9_]+\// {print $1}' > "$DIR/.refs"
  while read -r ref; do
    [ -n "$ref" ] || continue
    grep -qxF "$ref" "$SEEN" && continue
    echo "$ref" >> "$SEEN"
    slug=$(echo "$ref" | tr '/' '_')
    mkdir -p "$KDIR/$slug"
    if ! "$KG" kernels pull "$ref" -p "$KDIR/$slug" >/dev/null 2>&1; then
      log "pull failed $ref"; continue
    fi
    log "pulled $ref"
    python3 "$ROOT/work/tools/extract_artifacts.py" "$KDIR/$slug" --out "$ART" >> "$LOG" 2>&1
  done < "$DIR/.refs"

  # score any new invsqrt-sized artifacts with the official verifier
  for f in "$ART"/*.kmb; do
    [ -e "$f" ] || continue
    sha=$(basename "$f" .kmb)
    grep -qF "$sha" "$FOUND" && continue
    q=$($PY - "$f" <<'EOF'
import struct, sys
# the kickmix header is 16 magic bytes + struct '<4I9Q' = 52 bytes -> read 128 to be safe
raw = open(sys.argv[1], 'rb').read(128)
h = struct.unpack_from('<4I9Q', raw, 16)
print(h[1])
EOF
)
    if [ "$q" -ge 20 ] 2>/dev/null && [ "$q" -le 80 ] 2>/dev/null; then
      out=$(PYTHONPATH="$KICK" timeout 900 "$PY" "$VER" "$f" --shots-per-x 1 --batch-size 32 --max-workers 4 2>/dev/null)
      score=$(echo "$out" | python3 -c "
import sys, json
t = sys.stdin.read()
i, j = t.find('{'), t.rfind('}')
try:
    d = json.loads(t[i:j+1]); print(d.get('score', ''), d.get('status', ''), d.get('num_qubits',''), d.get('toffoli_count',''), d.get('rotation_count',''))
except Exception: print('')
")
      echo "$(date -u '+%Y-%m-%d %H:%M:%S')\tinvsqrt\t$sha\t$(stat -c%s "$f")\t$score" >> "$FOUND"
      log "scored invsqrt artifact $sha -> $score"
    else
      echo "$(date -u '+%Y-%m-%d %H:%M:%S')\tother\t$sha\t$(stat -c%s "$f")\tqubits=$q" >> "$FOUND"
      log "artifact $sha (qubits=$q) logged"
    fi
  done
  sleep 300
done
