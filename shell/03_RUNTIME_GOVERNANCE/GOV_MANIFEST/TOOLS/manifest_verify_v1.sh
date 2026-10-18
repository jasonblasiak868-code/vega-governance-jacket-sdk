#!/usr/bin/env bash
VEGA_ROOT="${VEGA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
export VEGA_ROOT
set -euo pipefail

VEGA_ROOT="${VEGA_ROOT}"
RG="$VEGA_ROOT/03_RUNTIME_GOVERNANCE"

MAN_CUR="$RG/GOV_MANIFEST/GOV_MANIFEST_CURRENT.txt"
VERIFY_DIR="$RG/GOV_MANIFEST/VERIFY"
mkdir -p "$VERIFY_DIR"

[ -f "$MAN_CUR" ] || { echo "DENY: No GOV_MANIFEST_CURRENT.txt (build first)"; exit 1; }
SNAP="$(cat "$MAN_CUR")"
[ -f "$SNAP" ] || { echo "DENY: Manifest snapshot missing: $SNAP"; exit 1; }

TS="$(date +%Y%m%d_%H%M%S)"
RECOMP="$VERIFY_DIR/recomputed_${TS}.sha256"
SNAPSORT="$VERIFY_DIR/snapshot_${TS}.sha256"

# Normalize: extract path column robustly and strip leading "VEGA_ROOT/"
# Snapshot format: "<sha>  VEGA_ROOT/<relpath>"
awk '{print $2}' "$SNAP" | sed 's|^VEGA_ROOT/||' | while read -r rel; do
  f="$VEGA_ROOT/$rel"
  if [ ! -f "$f" ]; then
    echo "MISSING  VEGA_ROOT/$rel" >> "$RECOMP"
  else
    sha256sum "$f" | sed "s| $VEGA_ROOT/| VEGA_ROOT/|" >> "$RECOMP"
  fi
done

sort "$RECOMP" > "$RECOMP.sorted"
sort "$SNAP"   > "$SNAPSORT.sorted"

if diff -q "$RECOMP.sorted" "$SNAPSORT.sorted" >/dev/null; then
  echo "OK: manifest verify PASS"
  echo "Recompute: $RECOMP.sorted"
  exit 0
else
  echo "DENY: manifest verify FAIL"
  echo "Snapshot : $SNAP"
  echo "Recompute: $RECOMP.sorted"
  echo "Diff (first 120):"
  diff -u "$SNAPSORT.sorted" "$RECOMP.sorted" | sed -n '1,120p' || true
  exit 1
fi
