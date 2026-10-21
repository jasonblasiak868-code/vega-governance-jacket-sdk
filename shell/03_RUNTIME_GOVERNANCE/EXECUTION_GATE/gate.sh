VEGA_ROOT="${VEGA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export VEGA_ROOT
# ---- VEGA PATCH: canonical root ----


# --- Hard Stop (canonical) ---
CONF="${VEGA_ROOT}/03_RUNTIME_GOVERNANCE/EXECUTION_GATE/hard_stop_path.conf"
if [ -f "$CONF" ]; then source "$CONF"; fi
HARD_STOP_FLAG="${HARD_STOP_FLAG:-${VEGA_ROOT}/03_RUNTIME_GOVERNANCE/EXECUTION_GATE/HARD_STOP.flag}"
if [ -f "$HARD_STOP_FLAG" ]; then
  echo "DENY: Hard Stop active ($HARD_STOP_FLAG)"
  exit 1
fi
# -----------------------------
# --- Tier ranking (hardened) ---
rank_tier(){
  case "${1:-none}" in
    none) echo 0;;
    read) echo 1;;
    write) echo 2;;
    core) echo 3;;
    *) echo 0;;
  esac
}
# --------------------------------

CONF="${VEGA_ROOT}/10_VEGA_CORE/ORCHESTRATOR_CORE/config/vega_root.conf"
if [ -f "$CONF" ]; then source "$CONF"; fi
# ------------------------------------
#!/usr/bin/env bash
set -euo pipefail

# ---- dynamic path resolution (no hardcoded /storage paths) ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RG_DEFAULT="$(cd "$SCRIPT_DIR/.." && pwd)"          # .../03_RUNTIME_GOVERNANCE
RG="${RG:-$RG_DEFAULT}"

VEGA_ROOT_DEFAULT="$(cd "$RG/.." && pwd)"          # .../vega_runtime (or VEGA_AUTHORITATIVE if run there)
VEGA_ROOT="${VEGA_ROOT:-$VEGA_ROOT_DEFAULT}"

REGISTRY="${REGISTRY:-$RG/MODULE_REGISTRY/modules.jsonl}"
AUDIT="${AUDIT:-$RG/AUDIT_LOG/audit.log}"
AUDIT_ROOT="${AUDIT_ROOT:-$(dirname "$AUDIT")}"
AUDIT="$AUDIT_ROOT/audit.log"

SECURE_ROOT="${SECURE_ROOT:-$VEGA_ROOT/00_SECURE_FOLDER}"
SECURE_UNLOCK="${SECURE_ROOT}/.unlocked"

mkdir -p "$(dirname "$AUDIT")"

MODULE="${1:-}"
ACTION="${2:-}"

if [ -z "$MODULE" ] || [ -z "$ACTION" ]; then
  echo "DENY: Missing MODULE/ACTION."
  echo "$(date) | $MODULE | $ACTION | DENY | Missing args" >> "$AUDIT"
  exit 1
fi

# A module or action is a plain word: letters, digits, underscore, hyphen. Anything else (a regular expression, a newline, a separator) is refused BEFORE it is used to
# search the registry or written to the audit log (a name like '.*' used to match any entry, and a newline could forge an audit line).
case "$MODULE$ACTION" in
  *[!A-Za-z0-9_-]*)
    echo "DENY: module and action must be plain words (letters, digits, _ and -)."
    echo "$(date) | (invalid name) | (invalid action) | DENY | Invalid characters" >> "$AUDIT"
    exit 1
  ;;
esac

# tolerate spacing in JSON (jsonl)
ENTRY="$(grep -E "\"name\"[[:space:]]*:[[:space:]]*\"$MODULE\"" "$REGISTRY" 2>/dev/null || true)"

if [ "$(printf '%s
' "$ENTRY" | grep -c .)" -gt 1 ]; then
  echo "DENY: Registry has more than one entry for this module."
  echo "$(date) | $MODULE | $ACTION | DENY | Ambiguous registry entry" >> "$AUDIT"
  exit 1
fi

if [ -z "$ENTRY" ]; then
  echo "DENY: Module not registered."
  echo "$(date) | $MODULE | $ACTION | DENY | Not registered" >> "$AUDIT"
  exit 1
fi

TIER="$(echo "$ENTRY" | sed -n 's/.*"tier"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
ALLOWED="$(echo "$ENTRY" | grep -o "\"allowed\"[[:space:]]*:[[:space:]]*\[[^]]*\]" | sed 's/.*\[\(.*\)\]/\1/' | tr -d '"' | tr -d ' ')"

tier_val() {
  case "$1" in
    none)  echo 0 ;;
    read)  echo 1 ;;
    write) echo 2 ;;
    admin) echo 3 ;;
    core)  echo 4 ;;
    *)     echo 0 ;;
  esac
}


required_tier_for_action() {
  case "$1" in
    run|view|echo|cat) echo read ;;
    write|export|create|update) echo write ;;
    admin|register|grant|revoke) echo admin ;;
    *) echo read ;;
  esac
}

REQ_TIER="$(required_tier_for_action "$ACTION")"

if ! echo "$ALLOWED" | tr ',' '\n' | grep -qx "$ACTION"; then
  echo "DENY: Action not permitted."
  echo "$(date) | $MODULE | $ACTION | DENY | Action not allowed" >> "$AUDIT"
  exit 1
fi

if [ "$(tier_val "$TIER")" -lt "$(tier_val "$REQ_TIER")" ]; then
  echo "DENY: Tier insufficient. Need=$REQ_TIER Have=$TIER"
  echo "$(date) | $MODULE | $ACTION | DENY | Tier insufficient (need=$REQ_TIER have=$TIER)" >> "$AUDIT"
  exit 1
fi

case "$ACTION" in
  write|export|create|update)
    if [ ! -f "$SECURE_UNLOCK" ]; then
      echo "DENY: Secure folder not unlocked ($SECURE_UNLOCK missing)."
      echo "$(date) | $MODULE | $ACTION | DENY | Secure locked" >> "$AUDIT"
      exit 1
    fi
  ;;
esac

echo "ALLOW: $MODULE may perform $ACTION"
echo "$(date) | $MODULE | $ACTION | ALLOW | Passed gate" >> "$AUDIT"
exit 0
