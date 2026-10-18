========================================
VEGA — ADAPTER → GOVERNANCE ENFORCEMENT CONTRACT
V2 (Runtime Interaction Discipline)
========================================
STATUS:
Locked • Spine-Level • Runtime Governance

SCOPE
-----
This contract governs HOW adapters behave at runtime (handshake, execution,
logging, failure, and chaining). It complements (does not replace) the
Adapter Permission Contract.

DEFINITIONS
-----------
Adapter:
  A constrained execution interface to an external environment.
Orchestrator:
  The routing + gating layer that invokes adapters.
Sentinel:
  The scoring/escalation layer that blocks, gates, or forces clarification.
Hard Stop:
  The non-bypassable safety/legal/policy halt mechanism.
Manifest:
  The integrity snapshot of governed artifacts (checksums + required files).
Checkpoint:
  A session-boundary governance state update moment (no mid-response activation).

NON-NEGOTIABLE INVARIANTS
-------------------------
Adapters MUST NOT:
1) Modify Governance Core artifacts (spine files, sentinel rules, manifest tooling)
2) Disable, bypass, or “work around” Hard Stop
3) Change Sentinel thresholds, tier floors, or strictness mapping
4) Create hidden persistence (silent caches, shadow logs, undisclosed storage)
5) Escalate their own permissions or scope
6) Chain to another adapter without Orchestrator-controlled routing + disclosure
7) Perform irreversible actions without explicit confirmation gates
8) Access Secure Folder without explicit authorization gate + audit entry

RUNTIME HANDSHAKE (REQUIRED BEFORE ANY EXECUTION)
-------------------------------------------------
Before executing any action beyond "Analyze/Propose", the adapter MUST provide:

A) Contract Identity
   - adapter_id
   - adapter_version
   - environment_target
   - declared_capabilities (Read/Generate/Simulate/Execute)
   - declared_data_classes (what it reads/writes)

B) Risk Declaration (self-declared)
   - risk_class: GREEN / YELLOW / RED
   - irreversible_actions: yes/no + list
   - external_side_effects: yes/no + list

C) Integrity Binding
   - GOV_manifest_version_id (from current session)
   - strictness_tier_in_force (current tier)
   - sentinel_profile_version (current)
If mismatch → NO EXECUTION. Trigger Tier-5 Protection + incident triad.

D) Preflight Gates (Orchestrator enforced)
   - Sentinel score check
   - Token reserve check (L0–L2 must be satisfiable)
   - Confirmation gate requirement evaluation
   - Adapter classification validity (not stale)

EXECUTION MODES (ALLOWED)
-------------------------
Mode 0: Analyze / Propose (Default Safe)
  - no external side effects
  - may produce a plan, code draft, or simulation output

Mode 1: Simulate (Sandbox / Non-binding)
  - no writes to external environment
  - outputs labeled "SIMULATION"

Mode 2: Execute (Real-world side effects)
  - requires gates + logging + confirmation (see below)

CONFIRMATION GATES (WHEN REQUIRED)
----------------------------------
Execution requires explicit confirmation when ANY apply:
- risk_class is RED
- action is irreversible
- action touches finances, legal, public disclosure, credentials, account access
- action writes outside VEGA_AUTHORITATIVE
- action changes external state (posts, purchases, sends, deletes, transfers)

Confirmation must be:
- explicit, unambiguous, immediate (no implied consent)
- bound to an exact action summary ("what will happen")
- time-bounded (expires after N minutes or next checkpoint)

TIER FLOORS (ENFORCEMENT)
-------------------------
Tier 1:
- Analyze/Propose allowed
- Execute allowed only for GREEN with confirmation optional

Tier 2:
- Execute requires confirmation for YELLOW/RED
- Enhanced logging

Tier 3:
- Confirmation required for ALL Execute
- Simulate encouraged prior to Execute

Tier 4:
- Execute restricted to explicitly allowlisted actions
- Default: Simulate/Propose only unless user confirms + Sentinel passes + stability
- Legal/financial/public disclosure actions require Tier-4 minimums + double gate

Tier 5 (Protection Mode):
- All adapters forced read-only/analyze
- No execution
- Must generate incident triad artifacts

ADAPTER CHAINING (TRANSITIVE DISCLOSURE)
----------------------------------------
Any adapter-to-adapter interaction MUST:
1) Be routed by Orchestrator (no direct calls)
2) Declare the full chain:
   Adapter A → Adapter B → ... → Adapter N
3) Inherit the MAX risk across the chain
4) Record chain to audit register
5) Apply strictest tier floor across the chain
If chain disclosure fails → Tier-5 Protection Mode.

DATA HANDLING RULES
-------------------
Adapters MUST:
- minimize data capture
- declare every data class read/write
- avoid storing raw sensitive artifacts unless explicitly authorized
- never store raw frames/audio/biometric replay artifacts by default
- store only match/no-match + timestamp + adapter context + governance version
  when integrity checks are used (privacy floor)

PERSISTENCE RULES
-----------------
Adapters may only write:
- governed outputs into VEGA_AUTHORITATIVE paths
- audit events into governed audit locations
All other writes are forbidden unless a specific adapter contract allowlists them.

AUDIT LOGGING (MANDATORY FOR EXECUTE)
-------------------------------------
On any Execute:
- write an audit entry containing:
  - timestamp
  - adapter_id/version
  - environment_target
  - action_summary
  - risk_class
  - sentinel_score + tier
  - confirmation_reference (if required)
  - outcome (success/fail) + error snippet
  - chain disclosure (if any)

FAILURE MODES & SAFE FALLBACK
-----------------------------
If any gate fails, adapter must:
- halt execution
- return a structured reason:
  (1) failed gate
  (2) what is needed to proceed
  (3) safe alternatives (simulate/propose)
- produce a minimal audit note ("blocked by governance")

If adapter encounters runtime uncertainty:
- downgrade to Simulate/Propose
- ask clarifying questions
- do not guess

NO PARTIAL ACTIVATION / NO MID-RESPONSE CHANGES
-----------------------------------------------
Adapters may NOT apply:
- permission changes
- governance changes
- tier mapping changes
mid-response.

All changes must occur at checkpoint via governance evolution protocol.

RECLASSIFICATION & TRUST RESET
------------------------------
Any change to:
- adapter capabilities
- data classes
- environment_target
- chaining behavior
forces:
1) reclassification (GREEN/YELLOW/RED)
2) offline validation run
3) stability window reset
4) manifest snapshot update (if governed artifacts changed)

END OF FILE
