#!/usr/bin/env bash
set -euo pipefail
OUTDIR="${1:-}"
[ -z "$OUTDIR" ] && { echo "FAIL: usage triad_generate.sh <outdir>"; exit 1; }
mkdir -p "$OUTDIR"
BASE="$(cd "$(dirname "$0")/.." && pwd)/INCIDENT_TRIAD_TEMPLATES"
cp -f "$BASE/INCIDENT_LOG.template.md"  "$OUTDIR/INCIDENT_LOG.md"
cp -f "$BASE/PATCH_PLAN.template.md"    "$OUTDIR/PATCH_PLAN.md"
cp -f "$BASE/TEST_PROTOCOL.template.md" "$OUTDIR/TEST_PROTOCOL.md"
echo "OK: triad created in: $OUTDIR"
