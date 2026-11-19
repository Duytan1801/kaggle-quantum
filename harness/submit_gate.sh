#!/usr/bin/env bash
# submit_gate.sh — MECHANICAL two-receipt submission gate (invariant, not prose).
#
# Usage:
#   submit_gate.sh <tree_dir> <sha_table.json> <receipt.json> <label> [message]
#
# Checks (all must pass, else exit 1 with GATE-FAIL + reason):
#   1. tree_dir contains EXACTLY the files named in the sha table
#   2. every file's sha256 + size matches the table
#   3. receipt verdict contains "-RECEIPT-PASS" and shas_ok is true
#   4. a fresh zip is rebuilt from the tree and its sha256 is printed
# If all pass: prints "GATE-OK <zipsha> <zippath>".
# With --submit as the last arg: submits to Kaggle AFTER the gate, with message.
set -eu

PROJ=${PROJ:-/home/bandoc/Downloads/opencode}
MODE="gate"
if [ "${1:-}" = "--submit" ]; then MODE="submit"; shift; fi
TREE="$1"; TABLE="$2"; RECEIPT="$3"; LABEL="$4"; MSG="${5:-$LABEL}"

fail() { echo "GATE-FAIL: $*" >&2; exit 1; }

[ -d "$TREE" ] || fail "tree dir missing: $TREE"
[ -f "$TABLE" ] || fail "sha table missing: $TABLE"
[ -f "$RECEIPT" ] || fail "receipt missing: $RECEIPT"

# 3. receipt verdict
python3 - "$RECEIPT" <<'EOF' || fail "receipt verdict not PASS"
import json, sys
r = json.load(open(sys.argv[1]))
ok = (r.get("shas_ok") is True) and ("RECEIPT-PASS" in str(r.get("verdict", "")))
sys.exit(0 if ok else 1)
EOF

# 1+2. tree contents vs table
python3 - "$TREE" "$TABLE" <<'EOF' || fail "tree/table mismatch (see above)"
import json, hashlib, os, sys
tree, tab = sys.argv[1], json.load(open(sys.argv[2]))["files"]
actual = {}
for root, _, names in os.walk(tree):
    for n in names:
        p = os.path.join(root, n)
        actual[os.path.relpath(p, tree).replace(os.sep, "/")] = p
bad = 0
for name in sorted(set(actual) | set(tab)):
    if name not in tab: print("EXTRA in tree:", name); bad += 1; continue
    if name not in actual: print("MISSING from tree:", name); bad += 1; continue
    h = hashlib.sha256(open(actual[name], "rb").read()).hexdigest()
    sz = os.path.getsize(actual[name])
    want_sha, want_sz = (tab[name] if isinstance(tab[name], (list, tuple)) else (tab[name], None))[0:2]
    if h != want_sha or (want_sz is not None and sz != want_sz):
        print("MISMATCH:", name, want_sha[:12], "->", h[:12]); bad += 1
sys.exit(1 if bad else 0)
EOF

# 4. rebuild zip fresh from the gated tree
STAGE=$(mktemp -d /tmp/opencode/gate_zip.XXXXXX)
ZIP="$STAGE/submission.zip"
python3 - "$TREE" "$ZIP" <<'EOF'
import hashlib, os, sys, zipfile
tree, zipp = sys.argv[1], sys.argv[2]
files = sorted(
    os.path.relpath(os.path.join(r, n), tree).replace(os.sep, "/")
    for r, _, ns in os.walk(tree) for n in ns)
with zipfile.ZipFile(zipp, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in files:
        z.write(os.path.join(tree, rel), rel)
with zipfile.ZipFile(zipp) as z:
    for rel in files:
        assert hashlib.sha256(z.read(rel)).hexdigest() == hashlib.sha256(open(os.path.join(tree, rel), "rb").read()).hexdigest()
EOF
ZIPSHA=$(python3 -c "import hashlib;print(hashlib.sha256(open('$ZIP','rb').read()).hexdigest()[:16])")
echo "GATE-OK $ZIPSHA $ZIP  (label: $LABEL)"

# Persist the gated zip durably.  /tmp/opencode is volatile and the GitHub
# mirror must hold the EXACT submitted bytes; without this, the mirror's
# "latest tree" was whichever stale gate_zip.* directory happened to sort
# first.  The path is derived from the sha-table name (sha_table_v132.txt ->
# work/trees/v132/submission.zip).
TSLOT=$(basename "$TABLE" .txt | sed 's/^sha_table_//')
if [ -n "$TSLOT" ]; then
  KEEP="$PROJ/work/trees/$TSLOT"
  mkdir -p "$KEEP"
  cp -f "$ZIP" "$KEEP/submission.zip"
  cp -f "$TABLE" "$KEEP/SHA_TABLE.json"
  cp -f "$RECEIPT" "$KEEP/RECEIPT.json"
  echo "GATE-KEEP $KEEP/submission.zip  zipsha=$ZIPSHA"
fi

if [ "$MODE" = "submit" ]; then
  export PATH="$HOME/.local/bin:$PATH"
  kaggle competitions submit -c google-verifiable-quantum-circuit-compilation -f "$ZIP" -m "$MSG"
  echo "SUBMITTED (gated) label=$LABEL zipsha=$ZIPSHA"
fi
