VEGA_ROOT="${VEGA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export VEGA_ROOT
# ---- VEGA PATCH: canonical root ----
CONF="${VEGA_ROOT}/10_VEGA_CORE/ORCHESTRATOR_CORE/config/vega_root.conf"
if [ -f "$CONF" ]; then source "$CONF"; fi
# ------------------------------------
#!/usr/bin/env bash
set -euo pipefail

# --- Canonical roots (Passport) ---
VEGA_ROOT="${VEGA_ROOT}"
RG="$VEGA_ROOT/03_RUNTIME_GOVERNANCE"
CORE="$VEGA_ROOT/VEGA_RUNNER_CORE"
GOV="$RG"   # compat: legacy scripts may reference GOV
# ----------------------------------

VEGA_ROOT="${VEGA_ROOT}"
RG="$VEGA_ROOT/03_RUNTIME_GOVERNANCE"
CORE="$VEGA_ROOT/VEGA_RUNNER_CORE"

ROUTES="$GOV/GOV_MANIFEST/ROUTING_TABLE_V1.json"
LOG="$RG/AUDIT_LOG/orchestrator.log"

GATE="$RG/EXECUTION_GATE/gate.sh"
RUNNER="$CORE/runner.sh"
MODULES_DIR="$RG/MODULES"

# Usage:
#   orchestrator.sh "TASK_TEXT" [MODULE_OVERRIDE] [ACTION_OVERRIDE]
TASK="${1:-}"
MODULE_OVERRIDE="${2:-}"
ACTION_OVERRIDE="${3:-}"

if [ -z "$TASK" ]; then
  echo "Usage: orchestrator.sh \"TASK_TEXT\" [MODULE_OVERRIDE] [ACTION_OVERRIDE]"
  exit 1
fi

ts() { date +"%Y-%m-%d %H:%M:%S %Z"; }
log() { echo "$(ts) $*" >> "$LOG"; }

# ---- helper: pick module/action/lane from routing table (if present) ----
pick_from_routes() {
  local task_lc="$1"
  local module="" action="" lane=""

  if [ -f "$ROUTES" ]; then
    # minimal JSON parsing by grep/sed (kept simple on purpose)
    # Finds first route whose "match" appears in task.
    while read -r line; do
      # pull match/module/action/lane from single-line object
      local match=$(echo "$line" | sed -n 's/.*"match"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      [ -z "$match" ] && continue
      if echo "$task_lc" | grep -qi "$match"; then
        module=$(echo "$line" | sed -n 's/.*"module"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
        action=$(echo "$line" | sed -n 's/.*"action"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
        lane=$(echo "$line"   | sed -n 's/.*"lane"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
        break
      fi
    done < <(grep -o '{[^}]*"match"[^}]*}' "$ROUTES" 2>/dev/null || true)

    if [ -z "$module" ]; then
      module=$(grep -o '"default"[[:space:]]*:[[:space:]]*{[^}]*}' "$ROUTES" 2>/dev/null | sed -n 's/.*"module"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      action=$(grep -o '"default"[[:space:]]*:[[:space:]]*{[^}]*}' "$ROUTES" 2>/dev/null | sed -n 's/.*"action"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      lane=$(grep -o '"default"[[:space:]]*:[[:space:]]*{[^}]*}' "$ROUTES" 2>/dev/null | sed -n 's/.*"lane"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    fi
  fi

  echo "${module}|${action}|${lane}"
}

# ---- helper: heuristic fallback if no routing table ----
pick_heuristic() {
  local task_lc="$1"
  if echo "$task_lc" | grep -qi "patent\|provisional\|claims"; then
    echo "PATENT_OFFICE|run|BUILDERS"; return
  fi
  if echo "$task_lc" | grep -qi "swarm\|agents\|orchestrate"; then
    echo "SWARM_AGENTS|run|BUILDERS"; return
  fi
  if echo "$task_lc" | grep -qi "finance\|trade\|broker\|bankroll"; then
    echo "FINANCE|run|FINANCE"; return
  fi
  echo "BUILDERS|run|BUILDERS"
}

TASK_LC="$(echo "$TASK" | tr '[:upper:]' '[:lower:]')"

picked="$(pick_from_routes "$TASK_LC")"
MODULE="$(echo "$picked" | cut -d'|' -f1)"
ACTION="$(echo "$picked" | cut -d'|' -f2)"
LANE="$(echo "$picked" | cut -d'|' -f3)"

if [ -z "$MODULE" ] || [ -z "$ACTION" ]; then
  picked="$(pick_heuristic "$TASK_LC")"
  MODULE="$(echo "$picked" | cut -d'|' -f1)"
  ACTION="$(echo "$picked" | cut -d'|' -f2)"
  LANE="$(echo "$picked" | cut -d'|' -f3)"
fi

# Apply explicit overrides (hybrid rule)
[ -n "$MODULE_OVERRIDE" ] && MODULE="$MODULE_OVERRIDE"
[ -n "$ACTION_OVERRIDE" ] && ACTION="$ACTION_OVERRIDE"

# ---- lane validation (presence check only; lane enforcement is via gate/runner/modules) ----
LANE_DOC="$GOV/EXECUTION_STATES/${LANE}_EXECUTION_LANE_V1.md"
if [ ! -f "$LANE_DOC" ]; then
  # if lane doc missing, we still proceed but log it (no hard fail)
  log "WARN lane_doc_missing lane=$LANE expected=$LANE_DOC"
fi

# ---- preflight: gate (if present) ----
# ---- preflight: ACCESS_GATE_ENFORCER (must run before gate) ----
if [ -f "${VEGA_ROOT}/03_RUNTIME_GOVERNANCE/ACCESS_GATE_ENFORCER/access_gate_enforcer.sh" ]; then
  bash "${VEGA_ROOT}/03_RUNTIME_GOVERNANCE/ACCESS_GATE_ENFORCER/access_gate_enforcer.sh" "$MODULE" "$ACTION" "$TASK" >/dev/null || exit 1
fi

if [ -f "$GATE" ]; then
  bash "$GATE" "$MODULE" "$ACTION" || { log "DENY gate module=$MODULE action=$ACTION task=$TASK"; exit 1; }
else
  log "WARN gate_missing expected=$GATE"
fi

# ---- preflight: runner permission check (registry) ----
if [ -f "$RUNNER" ]; then
  bash "$RUNNER" "$MODULE" "$ACTION" >/dev/null || { log "DENY runner module=$MODULE action=$ACTION task=$TASK"; exit 1; }
else
  echo "FATAL: runner.sh missing at $RUNNER"
  log "FATAL runner_missing expected=$RUNNER"
  exit 1
fi

# ---- dispatch into module ----
MODULE_DIR="$MODULES_DIR/$MODULE"
MODULE_RUN="$MODULE_DIR/run.sh"

if [ ! -d "$MODULE_DIR" ]; then
  echo "DENY: Module folder missing: $MODULE_DIR"
  log "DENY module_dir_missing module=$MODULE action=$ACTION task=$TASK"
  exit 1
fi

if [ ! -f "$MODULE_RUN" ]; then
  echo "DENY: Module run.sh missing: $MODULE_RUN"
  log "DENY module_run_missing module=$MODULE action=$ACTION task=$TASK"
  exit 1
fi

log "ROUTE module=$MODULE action=$ACTION lane=$LANE task=$TASK"
# Pass: TASK as $1, ACTION as $2 (module can ignore/extend)
VIA_ORCHESTRATOR=1 bash "$MODULE_RUN" "$TASK" "$ACTION"
log "DONE module=$MODULE action=$ACTION"
echo "OK: routed -> $MODULE ($ACTION)"
