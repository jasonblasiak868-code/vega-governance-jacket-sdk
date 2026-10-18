========================================
VEGA — SHADOW META-AUDIT SELF-VALIDATION
V1
========================================
STATUS:
Locked • Spine-Level • Runtime Governance

ROLE
----
Meta-audit verifies that shadow audit is functioning correctly
and not producing unsafe drift, false confidence, or blind spots.

CORE CHECKS (CHECKPOINT-ONLY)
-----------------------------
1) COVERAGE CHECK
   - Shadow audit must observe all high-risk adapter actions
   - Any missing observation => YELLOW (or RED if high-impact)

2) CONSISTENCY CHECK
   - Similar inputs must not produce wildly different severity without cause
   - Large variance => YELLOW + requires explanation artifact

3) REGRESSION CHECK
   - Known past incidents are replayed as test vectors (non-sensitive)
   - If shadow audit misses them => RED

4) SNR / FALSE POSITIVE CHECK
   - If YELLOW rate too high with no harm:
     reduce notification verbosity, NOT tier floors
   - If RED rate too low and incidents occur:
     raise rule floors and require offline validation

5) DRIFT DETECTION
   - governance version mismatch
   - sentinel threshold drift
   - adapter contract changes without revalidation
   Any drift => Tier-5 protection

OUTPUTS
-------
Meta-audit outputs only:
- pass/fail
- confidence band
- unknowns
- required inputs
It does not execute fixes.

END OF FILE
