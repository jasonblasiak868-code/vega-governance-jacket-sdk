========================================
VEGA — EXECUTION SENTINEL
EXEC_SENTINEL_V1
========================================

STATUS
------
Active Doctrine • Non-executing • Sentinel Rules

PURPOSE
-------
Prevent “execution drift”:
- bypassing the governed chain,
- patching runtime without manifest discipline,
- running modules directly,
- silent scope expansion,
- repeated unstable edits that create duplicate systems.

This sentinel protects runtime stability and user time.

----------------------------------------
I. DEFINITIONS
----------------------------------------

A) GOVERNED CHAIN (CANON)
launcher -> vega_run -> access_gate_enforcer -> gate -> runner -> module

B) EXECUTION DRIFT
Any attempt to:
- run a module directly (without chain marker),
- change runtime files without:
  - backup
  - manifest rebuild
  - manifest verify pass
  - audit log entry

C) STABILITY WINDOW
After a manifest PASS:
- avoid edits unless necessary
- prefer testing over rewriting

----------------------------------------
II. SCORING (0–5)
----------------------------------------
EXEC_RISK_SCORE:
+1 direct module run attempt
+1 manifest verify FAIL
+1 registry mismatch detected
+1 path-root inconsistency detected
+1 repeated edits within short window (>=3 changes)

----------------------------------------
III. ACTION LADDER
----------------------------------------

A) Allow
If score <=1: proceed

B) Stabilize
If score 2–3:
- stop new edits
- force:
  1) backup
  2) manifest rebuild
  3) manifest verify PASS

C) Protection / Freeze (Tier-5 posture concept)
If score >=4 OR integrity mismatch on spine files:
- deny execution changes
- require incident triad
- require “single smallest fix”
- rebuild + verify + system_check

----------------------------------------
IV. AUDIT EVENTS (LOG NAMES ONLY)
----------------------------------------
EXEC_DIRECT_RUN_DENIED
EXEC_MANIFEST_FAIL
EXEC_REGISTRY_MISMATCH
EXEC_PATH_DRIFT
EXEC_SHADOW_SUCCESS_DETECTED
EXEC_TIER5_POSTURE

END OF FILE
========================================
