========================================
VEGA — OVERRIDE FREQUENCY / ABUSE SENTINEL
OFAS — V1
========================================
STATUS:
Locked • Spine-Level • Sentinel Rule

PURPOSE
-------
Prevent governance erosion through repeated override attempts,
even if each individual attempt follows the friction protocol.

OBSERVED SIGNALS (TRACKED)
--------------------------
- count_override_requests (rolling window)
- count_category_C_proposals (rolling window)
- count_denied_overrides
- count_post-denial retry attempts
- attempts to lower strictness floors
- attempts to expand adapter permissions

WINDOWS (DEFAULTS; OPERATOR-TUNABLE WITHIN FLOORS)
--------------------------------------------------
- Short window: 60 minutes
- Medium window: 24 hours
- Long window: 7 days

SEVERITY RULE FLOOR
-------------------
If any of the following occur:

RED triggers:
1) >= 3 Category-C override proposals in 24h
2) >= 2 attempts to lower Tier-4 floors in 24h
3) >= 5 override retries after denial in 60 min
4) Any override attempt during coercion/distress signals

YELLOW triggers:
1) >= 2 Category-C proposals in 24h
2) >= 3 override requests of any type in 60 min
3) Repeated attempts to expand adapter permission scope

ENFORCEMENT ACTIONS (TIERED)
----------------------------
YELLOW:
- Increase strictness by +1 tier at next checkpoint (max +1)
- Require additional clarifying questions
- Extend cooldown window

RED:
- Tier-5 Protection Mode
- Freeze execute adapters
- Force multi-session confirmation requirement
- Mandatory incident triad if persistence continues

ANTI-LOOP / HYSTERESIS
----------------------
- Downshift only after stability window passes
- No mid-response tier changes; checkpoint only
- Rate limiter persists across sessions via audit register counters

END OF FILE
