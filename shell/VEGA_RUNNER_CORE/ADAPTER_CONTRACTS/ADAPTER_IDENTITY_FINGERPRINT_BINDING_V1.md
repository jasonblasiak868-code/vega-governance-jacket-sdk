========================================
VEGA — ADAPTER IDENTITY & FINGERPRINT BINDING
AIFB — V1
========================================
STATUS:
Locked • Spine-Level • Runtime Governance

PURPOSE
-------
Prevent adapter swapping, impersonation, and scope drift under the same name.
Adapters must be uniquely identifiable and bound to manifest snapshots.

DEFINITIONS
-----------
Adapter_ID:
- Unique immutable identifier (string) assigned at adapter creation.

Adapter_Fingerprint:
- Hash-derived identity from:
  - adapter package/file checksums,
  - declared permission scope,
  - environment target,
  - declared data-classes,
  - adapter version_id.

Manifest Binding:
- The Governance Manifest MUST record Adapter_ID + Adapter_Fingerprint
  for any adapter allowed to Execute.

NON-NEGOTIABLE RULES
--------------------
1) No Execute Without Binding:
   - An adapter may NOT perform any Execute action unless:
     a) Adapter_ID exists,
     b) Adapter_Fingerprint exists,
     c) Both appear in current GOV_MANIFEST snapshot.

2) Any Fingerprint Change = Trust Reset:
   - If adapter bytes/config change, fingerprint changes.
   - Vega MUST:
     - mark adapter as NEW,
     - reset trust score,
     - require offline validation,
     - reclassify risk,
     - re-enter stability window.

3) Name Is Not Identity:
   - Human-readable adapter name is cosmetic.
   - Security identity is Adapter_ID + Fingerprint.

4) Anti-Impersonation:
   - If an adapter claims an Adapter_ID already used by a different fingerprint:
     -> Tier-5 Protection Mode
     -> execution freeze
     -> mandatory incident triad

REQUIRED METADATA (MINIMUM)
---------------------------
Each adapter contract MUST include:
- Adapter_ID
- adapter_version_id
- environment_target
- permission_scope (read/write/execute)
- data_class_declaration
- fingerprint (SHA-256 recommended)
- build_timestamp
- manifest_snapshot_id (when activated)

ENFORCEMENT
-----------
- Sentinel must treat missing/invalid binding as RED.
- Orchestrator must refuse Execute and fall back to:
  - Read-only analysis
  - Clarifying questions
  - Safe alternatives

END OF FILE
