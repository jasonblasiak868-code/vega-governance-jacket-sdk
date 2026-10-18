========================================
VEGA — BUILDERS ADAPTER CONTRACT ADDENDUM
V1
========================================
STATUS:
Locked • Spine-Level • Adapter Governance

SCOPE
-----
Any adapter used by Builders (codegen, build tools, repo tools, CI tools).

INVARIANTS
----------
Builders adapters MUST:
1) Declare write roots (allowed directories)
2) Refuse any write outside allowed roots
3) Provide dry-run previews for destructive operations
4) Emit audit events for:
   - destructive changes
   - bulk changes
   - export packets
   - any gated side-effect attempt
5) Never chain adapters to bypass gates

DECLARATIONS REQUIRED
---------------------
Adapter manifest must declare:
- tool name/version
- action list (generate/build/organize/export)
- prohibited actions
- write boundaries
- rollback behavior (where possible)

DENY RULE
---------
If requested action implies publish/deploy/pay/post:
- DENY by default
- return "GATE_REQUIRED"

END OF FILE
