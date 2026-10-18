#!/usr/bin/env bash
VEGA_ROOT="${VEGA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
export VEGA_ROOT
set -euo pipefail

VEGA_ROOT="${VEGA_ROOT}"
RG="$VEGA_ROOT/03_RUNTIME_GOVERNANCE"

MAN_SNAPS="$RG/GOV_MANIFEST/MANIFEST_SNAPSHOTS"
MAN_CUR="$RG/GOV_MANIFEST/GOV_MANIFEST_CURRENT.txt"
mkdir -p "$MAN_SNAPS"

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$MAN_SNAPS/MANIFEST_V1_${TS}.sha256"

# IMPORTANT: set CURRENT pointer BEFORE hashing so it doesn’t drift
echo "$OUT" > "$MAN_CUR"

# Stable integrity scope (EXCLUDES logs, backups, and snapshots themselves)
collect() {
  find "$VEGA_ROOT" -type f \( \
    -path "$RG/EXECUTION_GATE/*" -o \
    -path "$RG/MODULE_REGISTRY/*" -o \
    -path "$RG/ACCESS_GATE_ENFORCER/*" -o \
    -path "$RG/SENTINEL_RULES/*" -o \
    -path "$RG/META_AUDIT/*" -o \
    -path "$RG/GOV_MANIFEST/TOOLS/*" -o \
    -path "$RG/GOV_MANIFEST/GOV_MANIFEST_CURRENT.txt" -o \
    -path "$VEGA_ROOT/VEGA_RUNNER_CORE/*" \
  \) \
  ! -path "$RG/AUDIT_LOG/*" \
  ! -path "$VEGA_ROOT/08_BACKUPS/*" \
  ! -path "$RG/GOV_MANIFEST/MANIFEST_SNAPSHOTS/*" \
  -print0
}

collect \
| xargs -0 sha256sum \
| sed "s| $VEGA_ROOT/| VEGA_ROOT/|" \
| sort > "$OUT"

echo "OK: built manifest snapshot:"
echo "  $OUT"
echo "OK: current pointer:"
echo "  $MAN_CUR -> $(cat "$MAN_CUR")"
