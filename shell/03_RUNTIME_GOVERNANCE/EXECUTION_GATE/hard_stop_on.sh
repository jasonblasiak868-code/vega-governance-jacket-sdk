#!/usr/bin/env bash
VEGA_ROOT="${VEGA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export VEGA_ROOT
set -euo pipefail
CONF="${VEGA_ROOT}/03_RUNTIME_GOVERNANCE/EXECUTION_GATE/hard_stop_path.conf"
source "$CONF"
mkdir -p "$(dirname "$HARD_STOP_FLAG")"
date "+%F %T" > "$HARD_STOP_FLAG"
echo "HARD STOP ON -> $HARD_STOP_FLAG"
