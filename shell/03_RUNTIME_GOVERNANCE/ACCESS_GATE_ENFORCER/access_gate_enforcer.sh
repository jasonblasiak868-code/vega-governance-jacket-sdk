#!/usr/bin/env bash
VEGA_ROOT="${VEGA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export VEGA_ROOT
set -euo pipefail

VEGA_ROOT="${VEGA_ROOT}"
RG="$VEGA_ROOT/03_RUNTIME_GOVERNANCE"

# Hard Stop (canonical)
CONF="$RG/EXECUTION_GATE/hard_stop_path.conf"
if [ -f "$CONF" ]; then source "$CONF"; fi
HARD_STOP_FLAG="${HARD_STOP_FLAG:-${VEGA_ROOT}/03_RUNTIME_GOVERNANCE/EXECUTION_GATE/HARD_STOP.flag}"

# Optional manifest verifier (single canonical)
MANIFEST_VERIFY="${VEGA_ROOT}/03_RUNTIME_GOVERNANCE/GOV_MANIFEST/TOOLS/manifest_verify_v1.sh"

# Inputs (we keep signature compatible with gate calls)
MODULE="${1:-}"
ACTION="${2:-}"
EXTRA="${3:-}"

fail(){ echo "DENY: $*"; exit 1; }

# 1) Hard Stop first
if [ -f "$HARD_STOP_FLAG" ]; then
  TS="$(date +%Y%m%d_%H%M%S)"
  OUT="$RG/AUDIT_LOG/INCIDENTS/$TS"
  bash "$RG/ACCESS_GATE_ENFORCER/TOOLS/triad_generate.sh" "$OUT" >/dev/null 2>&1 || true
  fail "Hard Stop active ($HARD_STOP_FLAG)"
fi

# 2) Manifest verify (if present)
if [ -n "$MANIFEST_VERIFY" ] && [ -f "$MANIFEST_VERIFY" ]; then
  if [ -x "$MANIFEST_VERIFY" ]; then
    "$MANIFEST_VERIFY" || fail "Manifest verification failed"
  else
    bash "$MANIFEST_VERIFY" || fail "Manifest verification failed"
  fi
fi

# 3) Minimal sanity (deny empty)
[ -z "$MODULE" ] && fail "Missing MODULE"
[ -z "$ACTION" ] && fail "Missing ACTION"

echo "OK: ACCESS_GATE_ENFORCER passed"
