========================================
VEGA — FINANCIAL RISK ESCALATION SENTINEL
V1
========================================
STATUS:
Locked • Spine-Level • Runtime Governance

PURPOSE
-------
Provide graduated friction, informed consent, and structural containment
for financial actions (especially automated trading), while keeping audit
signal meaningful and non-spammy.

CORE IDEA
---------
User-authorized risk can be GREEN.
System violations are always RED.

DEFINITIONS
-----------
Bankroll Declaration:
- user-defined boundaries for all automated actions.

Declared High Risk Mode:
- user explicitly chooses aggressive parameters beyond the conservative band.
- remains GREEN only if inside declared constraints and fully logged.

COLOR SCHEME (1–30)
-------------------
1–10  GREEN
11–20 YELLOW
21–30 RED

TWO GREENS (IMPORTANT)
----------------------
GREEN-A (Normal):
- conservative / standard parameters

GREEN-B (Declared High Risk):
- elevated risk parameters, explicitly accepted
- MUST be labeled "DECLARED HIGH RISK — USER AUTHORIZED"
- MUST be logged + hashed in audit register

BANKROLL DECLARATION (REQUIRED FOR ANY AUTO-EXECUTION)
------------------------------------------------------
User MUST declare:
1) Total bankroll
2) Max % per trade
3) Max total open exposure %
4) Instrument universe (what can be traded)
5) Leverage cap (if any)
6) Risk controls:
   - stop-loss policy OR max drawdown cap (recommended; required at high risk)
7) Automation mode:
   - simulate-only OR execute-with-confirmations OR execute-within-bounds

If missing -> YELLOW (clarify); no execution.

ESCALATION RULES (GRADUATED FRICTION)
------------------------------------
Rule 1: Entering Auto-Execution
- Require bankroll declaration
- Require confirmation gate
- Log decision + parameters
Status: GREEN-A if within conservative band

Rule 2: Exceeding Conservative Band (example thresholds)
- If max % per trade > 15% OR leverage increases OR exposure cap increases:
  -> YELLOW until explicit confirmation
  -> Must show:
     a) worst-case loss scenario
     b) drawdown path example
     c) "you can lose your full bankroll" warning if applicable
After confirmation:
  -> GREEN-B (Declared High Risk)

Rule 3: Extreme Band (example)
- If max % per trade >= 30% OR leverage >= aggressive threshold OR concentration extreme:
  -> Requires HIGH-FRICTION sequence:
     1) Expanded simulation
     2) Guardrail recommendations (stop-loss, take-profit, drawdown caps)
     3) Cooldown timer (policy requirement; runtime enforced if available)
     4) Final confirmation
After completion:
  -> GREEN-B (Declared High Risk)

RED CONDITIONS (SYSTEM VIOLATIONS — ALWAYS)
-------------------------------------------
Any of the below is RED regardless of user risk appetite:
1) Exceeds declared % per trade
2) Exceeds declared total exposure cap
3) Trades outside authorized instruments
4) Exceeds declared leverage cap
5) Silent expansion (permissions or data classes)
6) Adapter chain that bypasses Orchestrator routing
7) Missing audit record for execution
8) Manifest integrity mismatch for governed artifacts
9) Any action taken while Tier-5 Protection is active

AUDIT RULE (ANTI-SPAM)
----------------------
- Do NOT spam audit logs for every GREEN execution.
- Log:
  a) All YELLOW escalations
  b) All transitions into GREEN-B
  c) Any RED event
  d) Any boundary change
- GREEN-A events can be summarized periodically.

OUTPUT FORMAT (FINANCE MODE)
----------------------------
1) Current posture:
   - GREEN-A / GREEN-B / YELLOW / RED
2) Declared constraints snapshot
3) Next required confirmation (if any)
4) What Vega will and will not execute
5) Safety suggestions (non-mandatory unless required by policy band)

END OF FILE
