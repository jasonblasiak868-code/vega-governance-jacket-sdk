========================================
VEGA — ADAPTER CHAIN TRANSPARENCY PROTOCOL
ACTP — V1
========================================
STATUS:
Locked • Spine-Level • Runtime Governance

PROBLEM
-------
A user may attempt to launder prohibited behavior by:
Vega -> Adapter A (declared "clean") -> Adapter B (hidden) -> prohibited system.

This is indirection-based governance bypass.

RULE (TRANSITIVE DISCLOSURE)
----------------------------
Any Adapter MUST disclose:
- all downstream adapters/services it calls,
- all domains/endpoints it contacts,
- all delegated execution layers,
- any dynamic routing logic.

NO OPAQUE PROXIES
-----------------
Adapters may NOT be declared as "opaque proxy only" unless:
- the downstream chain is fully enumerated,
- and the chain is governed under the same manifest and audit rules.

If downstream behavior is not inspectable:
- Adapter cannot be GREEN.
- Minimum is YELLOW, often RED depending on domain and consequence.

DOWNSTREAM LIABILITY ATTRIBUTION
--------------------------------
Vega treats downstream execution as an extension of the adapter’s authority.
If Adapter A causes prohibited behavior through Adapter B,
Adapter A is treated as having caused it.

ENFORCEMENT
-----------
Failure to disclose downstream chain triggers:
- Silent Expansion violation
- Tier-5 Protection posture
- Adapter execution disable
- Mandatory incident triad (per Tier-5 protocol)

END OF FILE
