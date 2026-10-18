#!/usr/bin/env bash
VEGA_ROOT="${VEGA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export VEGA_ROOT
set -euo pipefail

CONF="${VEGA_ROOT}/10_VEGA_CORE/ORCHESTRATOR_CORE/config/vega_root.conf"; if [ -f "$CONF" ]; then source "$CONF"; else VEGA_ROOT="${VEGA_ROOT}"; fi
RG="$VEGA_ROOT/03_RUNTIME_GOVERNANCE"
AUDIT_ROOT="$RG/AUDIT_LOG"
export AUDIT_ROOT
export VEGA_CHAIN_OK=1


CORE="$VEGA_ROOT/VEGA_RUNNER_CORE"
GATE="$VEGA_ROOT/03_RUNTIME_GOVERNANCE/EXECUTION_GATE/gate.sh"
RUNNER_LOG="$VEGA_ROOT/03_RUNTIME_GOVERNANCE/AUDIT_LOG/runner.log"

mkdir -p "$RG/AUDIT_LOG"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$RUNNER_LOG" >/dev/null
}

TASK="${1:-}"
ACTION="${2:-run}"

if [ -z "$TASK" ]; then
  echo "Usage: vega_run.sh \"task\" [action]"
  exit 1
fi

log "=== VEGA_RUN START ==="
log "TASK=$TASK"
log "ACTION=$ACTION"

  # --- ACCESS_GATE_ENFORCER (preflight choke point) ---
  if [ -f "${VEGA_ROOT}/03_RUNTIME_GOVERNANCE/ACCESS_GATE_ENFORCER/access_gate_enforcer.sh" ]; then
    bash "${VEGA_ROOT}/03_RUNTIME_GOVERNANCE/ACCESS_GATE_ENFORCER/access_gate_enforcer.sh" "VEGA" "$TASK" "$ACTION" >/dev/null
  fi
  # ----------------------------------------------------


if [ ! -f "$GATE" ]; then
  echo "ERROR: gate.sh missing at $GATE"
  exit 1
fi

bash "$GATE" "VEGA" "$TASK" "$ACTION" >> "$RUNNER_LOG" 2>&1

log "=== VEGA_RUN DONE ==="
echo "OK: Vega run complete"
