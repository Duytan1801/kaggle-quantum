#!/usr/bin/env bash
# harvest_dqi_pool.sh — download public QCC portfolios that may carry 890q-lineage DQI candidates.
# Each dataset is small-ish (<=60 MB) except black-cat; we fetch the cheap ones first.
set -u
KG=/home/bandoc/Downloads/opencode/qaenv/bin/kaggle
DST=/tmp/opencode/pool
mkdir -p "$DST"
DSETS=(
  balramsrinivasan/vqcc-28-10-norm-preserving-dqi-closings
  maoxin123/qcc-frontier-dqi-chem-mirror
  ratnachand/vqcc-verified-public-floor
  ghazarosbarseghyan91/vqcc-combo-candidates
  jezzlin/vqcc-bori-hybrid-20261117
  jezzlin/vqcc-ozertuu-invchem-hayato-hybrid-20261117
  jezzlin/vqcc-verified-base-portfolio-20261116
  jezzlin/vqcc-task1-maoxin-v27-audit-20261116
  hayatohikawa/qcc-c8-milestone-portfolio
  sheroleg/qcc-dqi-cutoff17-decoder-c60beda8
  igorholt/vqcc-28cluster-field-circuits
  syed3000/vqcc-own-circuit-portfolio
  varianceofx/vqcc-28075-verified-bundle
  neoluxlee/vqcc-verified-portfolio-20261116-v2
  ahoirg/qcc-portfolio-gm-27-28999
  lucifer19/black-cat-v11-credited-portfolio
  kirderf/vqcc-portfolio-27-11
  busyaprime/33-qcc-v8-members
)
one() {
  ref="$1"; slug="${ref//\//__}"
  mkdir -p "$DST/$slug"
  "$KG" datasets download "$ref" -p "$DST/$slug" --force >"$DST/$slug/dl.log" 2>&1 \
    && echo "OK   $ref" || echo "FAIL $ref"
}
export -f one
export KG DST
printf '%s\n' "${DSETS[@]}" | xargs -P 5 -I{} bash -c 'one "$@"' _ {}
echo "=== done"
du -sh "$DST" 2>/dev/null
