#!/usr/bin/env bash
VEGA_ROOT="${VEGA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export VEGA_ROOT
set -euo pipefail

VEGA_ROOT="${VEGA_ROOT}"
RG="$VEGA_ROOT/03_RUNTIME_GOVERNANCE"

REGISTRY="$RG/MODULE_REGISTRY/modules.jsonl"
LOG="$RG/AUDIT_LOG/runner.log"
mkdir -p "$(dirname "$LOG")"

MODULE="${1:-}"
ACTION="${2:-}"

if [ -z "$MODULE" ] || [ -z "$ACTION" ]; then
  echo "Usage: runner.sh MODULE ACTION"
  exit 1
fi

if [ ! -f "$REGISTRY" ]; then
  echo "DENY: Registry missing at $REGISTRY"
  echo "$(date) | $MODULE | $ACTION | DENY | Registry missing" >> "$LOG"
  exit 1
fi

# Find JSONL entry by "name"
ENTRY="$(grep -E "\"name\"[[:space:]]*:[[:space:]]*\"$MODULE\"" "$REGISTRY" 2>/dev/null || true)"

if [ -z "$ENTRY" ]; then
  echo "DENY: Module not registered"
  echo "$(date) | $MODULE | $ACTION | DENY | Not registered" >> "$LOG"
  exit 1
fi

ALLOWED="$(echo "$ENTRY" | grep -o "\"allowed\"[[:space:]]*:[[:space:]]*\[[^]]*\]" | sed 's/.*\[\(.*\)\]/\1/' | tr -d '"' | tr -d ' ')"

if ! echo "$ALLOWED" | tr ',' '\n' | grep -qx "$ACTION"; then
  echo "DENY: Action not allowed"
  echo "$(date) | $MODULE | $ACTION | DENY | Action not allowed" >> "$LOG"
  exit 1
fi

# Require gate=required unless explicitly gate=none
GATE_REQ="$(echo "$ENTRY" | sed -n 's/.*"gate"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
if [ "${GATE_REQ:-required}" != "required" ]; then
  echo "DENY: Gate requirement missing"
  echo "$(date) | $MODULE | $ACTION | DENY | Gate requirement missing" >> "$LOG"
  exit 1
fi

echo "ALLOW: $MODULE may perform $ACTION"
echo "$(date) | $MODULE | $ACTION | ALLOW | runner ok" >> "$LOG"
exit 0
