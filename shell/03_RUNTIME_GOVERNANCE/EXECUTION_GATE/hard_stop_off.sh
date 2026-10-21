#!/usr/bin/env bash
# DEPRECATED AND DISABLED. This script used to delete the hard-stop flag with no authority check, so anyone who could run it lifted a stop that was meant to need the
# human key. Lifting the hard stop is a human-signed action: use HardStop.restore() in vega_twogate (Python), which checks a human commitment for exactly
# restore_after_hard_stop, burns it, and records the restore. The shell layer is the legacy Termux-era path and is not the strong path.
echo "REFUSED: the shell cannot lift the hard stop. A human-signed restore (HardStop.restore) is required; see SECURITY.md." >&2
exit 1
