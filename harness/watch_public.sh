#!/usr/bin/env bash
# watch_public.sh — poll public kernels/datasets of the competition for NEW releases.
# Appends only newly-seen refs to /tmp/opencode/watch/new_releases.log (state kept in state.tsv).
set -u
KG=kaggle
COMP=google-verifiable-quantum-circuit-compilation
DIR=/tmp/opencode/watch
mkdir -p "$DIR"
STATE="$DIR/state.tsv"
NEW="$DIR/new_releases.log"
[ -f "$STATE" ] || : > "$STATE"

poll() {
  local kind="$1"; shift
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    ref=$(echo "$line" | awk '{print $1}')
    case "$ref" in ref|-) continue;; esac
    key="$kind|$ref"
    if ! grep -qF "$key" "$STATE"; then
      echo "$key|$line" >> "$STATE"
      echo "=== $(date -u) NEW $kind: $line" >> "$NEW"
    fi
  done < <("$@" 2>/dev/null | grep -v '^ref ' | grep -v '^---' | grep -v '^ *$')
}

for i in $(seq 1 100000); do
  poll kernel "$KG" kernels list --competition "$COMP" --sort-by dateRun --page-size 40
  # NOTE: `kaggle datasets list` has no --competition filter in this CLI version,
  # so we poll the global newest-created datasets (competition ones dominate the head).
  poll dataset "$KG" datasets list --sort-by dateCreated --page-size 40
  # also the known portfolio publishers (they publish outside the competition filter)
  for u in ozertuu boristown jeffemerson leotang09 hayatohikawa marculera syed3000 manwithacat atakanaldemir asteriospanoras; do
    poll "kernel-$u" "$KG" kernels list --user "$u" --sort-by dateRun --page-size 10
    poll "dataset-$u" "$KG" datasets list --user "$u" --sort-by dateUpdated --page-size 10
  done
  sleep 600
done
