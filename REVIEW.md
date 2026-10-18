# REVIEW (automated), 2026-10-17T09:28:33

Repo: vega-governance-jacket-sdk | python files 18 | seconds 16.7
Findings: high 0, medium 0, low 0, info 1
Tests: {"ran": true, "tests": 58, "ok": true, "redteam_files": {"1": 1, "2": 1}, "test_files": 5}
Network-capable modules imported: none

Limits: a clean scan is not proof of safety. Static rules are shallow; the copy check finds verbatim and light-edit copying against the 251-repo library only.

## info (1)
- `PY-SWALLOW-REVIEWED` src\vega_jacket\gate\exit_gate.py:28 the action is denied below whether or not the denial could be recorded (fail closed)             pass

