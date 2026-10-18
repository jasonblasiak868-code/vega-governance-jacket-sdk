========================================
VEGA — BUILDERS GOVERNANCE DOCTRINE
V1
========================================
STATUS:
Locked • Spine-Level • Runtime Governance

PURPOSE
-------
Define what "Builders" are allowed to do, how they are bounded, and
how they integrate with adapters and execution gates.

DEFINITION
----------
Builders are non-human worker processes that transform artifacts:
- generate code, docs, configs
- create folder structures
- move/rename/merge files
- compile/build packages locally
- produce drafts/exports for user review

Builders are NOT autonomous executors of external side effects.

SAFE CORE PRINCIPLE
-------------------
Builders may create and organize artifacts.
Builders may NOT publish, spend, or execute irreversible actions
without explicit gate approval.

ALLOWED ACTIONS (GREEN-A)
-------------------------
1) Generate:
- code stubs
- project scaffolds
- documentation
- configuration files

2) Transform:
- format, lint, refactor (non-destructive)
- convert file types (md/pdf/json) when permitted

3) Organize:
- create folders
- move/copy files within VEGA_AUTHORITATIVE
- produce export packets to designated export folders

4) Build (local only):
- run local compilation/build steps that do NOT publish or deploy

PROHIBITED ACTIONS (RED BY DEFAULT)
-----------------------------------
Builders may not:
1) Publish content (social posts, app store submission, pushing repos)
2) Spend money or trigger paid actions
3) Execute remote commands or act on external services without a gate
4) Access secrets outside approved vault policy
5) Modify governance canon or constitutional floors
6) Alter audit logs or suppression of alerts
7) Self-extend permissions or add new adapters silently

YELLOW (REQUIRES USER CONFIRMATION)
-----------------------------------
1) Any action that changes more than N files (bulk refactor)
2) Any destructive change (delete/overwrite) outside a sandbox
3) Any build that produces an installable artifact (APK/IPA/EXE)
4) Any export packet that leaves VEGA_AUTHORITATIVE boundary

RED (SYSTEM VIOLATIONS)
-----------------------
1) Any prohibited action executed
2) Any boundary escape (writing outside allowed roots)
3) Any silent permission expansion
4) Missing audit events for gated actions
5) Adapter chaining to bypass Orchestrator

OPERATING MODES
---------------
GREEN-A: Draft + Build Local + Organize
GREEN-B: Declared Risk Build (large refactors) with explicit consent
YELLOW: Confirmation needed
RED: Deny + escalate Tier-5 if integrity threatened

END OF FILE
