# Changelog

## 2026-10-20: fixes found by a source read

These were found by reading the source against its own documentation after release, not by the earlier test and review passes. Each fix has a regression test in
`tests/test_findings_20261020.py` that failed before the fix, and each fix was checked by undoing it and confirming a test fails. Behaviour that changed is listed under "Changed".

### Fixed
- **One human approval could be accepted twice across two gate objects.** A `Commit` read its set of used approvals once, when it was built. Two `Commit` objects sharing one DAG could both accept an approval whenever no ledger mint was there to catch the duplicate (`boundary_crossing=False`). The set is now re-read from the DAG on every check, and the check and the burn run under one lock shared by every gate on that DAG.
- **`human_cli sign`** reported a refused action, device, surface or lease as "wrong passphrase"; a lease of zero or less was not refused up front. Both are fixed.
- **Legacy shell layer.** `shell/.../hard_stop_off.sh` deleted the hard-stop flag with no authority check. It now refuses and points to the signed restore (`HardStop.restore` in `vega-two-gate-sdk`). `gate.sh` used the module name as a regular expression, so `gate.sh '.*' run` was allowed for a module that does not exist, and a newline in a name could forge an audit line. Names and actions must now be plain words. The shell scripts remain a legacy, weaker path; the Python gates are the strong one.

### Changed (read before upgrading)
- `hard_stop_off.sh` no longer lifts the stop.
