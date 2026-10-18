========================================
VEGA — FINANCE ADAPTER CONTRACT ADDENDUM
V1
========================================
STATUS:
Locked • Spine-Level • Adapter Governance

SCOPE
-----
Applies to any adapter that can:
- place trades,
- move funds,
- interact with exchanges/brokerages,
- or trigger financial commitments.

NON-NEGOTIABLE INVARIANTS
-------------------------
Finance adapters MUST NOT:
1) Execute without Orchestrator-controlled routing
2) Chain into other adapters to bypass gates
3) Expand permissions silently
4) Modify bankroll constraints
5) Override stop-loss/drawdown policies if required by band
6) Trade outside allowed instruments
7) Exceed declared leverage or exposure caps
8) Persist secrets outside approved secure storage policy

REQUIRED DECLARATIONS
---------------------
Finance adapter must declare:
- target environment (broker/exchange/API)
- allowed actions (Read / Simulate / Execute)
- instruments allowed
- rate limits + failure modes
- audit event hooks
- revocation behavior (immediate disable)

BOUNDARY ENFORCEMENT
--------------------
If adapter detects:
- mismatch between requested action and declared constraints
- missing confirmation
- Tier-5 active
It MUST:
- refuse execution
- return reason code
- request checkpoint escalation

END OF FILE
