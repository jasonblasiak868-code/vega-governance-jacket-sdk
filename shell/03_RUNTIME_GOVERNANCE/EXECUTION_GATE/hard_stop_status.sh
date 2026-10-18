#!/usr/bin/env bash
VEGA_ROOT="${VEGA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export VEGA_ROOT
set -euo pipefail
CONF="${VEGA_ROOT}/03_RUNTIME_GOVERNANCE/EXECUTION_GATE/hard_stop_path.conf"
source "$CONF"
if [ -f "$HARD_STOP_FLAG" ]; then
  echo "Hard Stop: ON  ($HARD_STOP_FLAG)"
else
  echo "Hard Stop: OFF ($HARD_STOP_FLAG)"
fi
