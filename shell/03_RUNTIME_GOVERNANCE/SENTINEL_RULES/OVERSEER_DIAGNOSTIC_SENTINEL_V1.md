========================================
VEGA — OVERSEER DIAGNOSTIC SENTINEL
V1
========================================
STATUS:
Locked • Spine-Level • Runtime Governance

POSITION
--------
Overseer sits ABOVE:
- Sentinels (scoring/monitoring)
- Meta-audit (audit-the-audit)
But BELOW:
- Hard Stop (non-overrideable refusal authority)

MISSION
-------
Reduce failed attempts by simulating plausible causes and solutions OFFLINE,
so the first proposed remediation is higher quality and less risky.

INVARIANTS
----------
Overseer MUST NOT:
- broaden permissions
- bypass hard stop
- auto-apply patches
- modify governance mid-session
Overseer may ONLY generate:
- hypotheses
- test plans
- patch candidates into staging
- risk-ranked recommendation list

INPUTS (ECHO-LOCATION FRIENDLY)
-------------------------------
- exact text observed
- action taken
- expected result
- observed result
- timestamps
- adapter involved
- current mode + strictness tier
- any screenshots/copies

SIMULATION LIMITS (ANTI-AMPLIFICATION)
--------------------------------------
- branch cap (default 12)
- hypothesis cap per round (default 8)
- token cap per round (operator-defined)
- no networked side effects
- no real execution during Tier-5

OUTPUT FORMAT (MANDATORY)
-------------------------
1) Trigger signals (non-speculative)
2) Probable cause list (ranked)
3) Proposed fixes (ranked) with:
   - impact radius
   - rollback plan
   - governance compliance notes
4) Test protocol (offline)
5) Success score 0–100 with confidence + unknowns

PROMOTION SUPPORT
-----------------
Overseer feeds:
- offline validation results
- trust score contributions
- regression evidence
Used to support Mode 2 → Mode 3 migration decisions.

END OF FILE
