# vega-governance-jacket-sdk — Specification

Spec v1.0 — 2026-10-19 — describes the published reference implementation as tested; where this document and the source disagree, the source wins.

## 1. Purpose and scope

This specification covers the governance jacket: the authority layer (layer 1) that owns human-only actions, single-use signed commitments, and entry/exit gates. It specifies the behavior of four modules: humanauth (verification + signer), commit, gate (entry + exit), and shell (runner scripts). The jacket depends on vega-custody-sdk (layer 0) for capsules, DAG, and ledger primitives. Out of scope: hardware key integration (TPM, FIDO2) — designed only, not built; the umbrella registry and cross-kit audit; training, reasoning, knowledge graph, and deliberation layers above.

## 2. Vocabulary

- **Commitment (WCOMMIT)**: A signed record binding a human's key to one exact action, parameters, device, surface, nonce, and expiry. Format: `WCOMMIT|device|surface|action|action_hash|nonce|expiry`.
- **Nonce burn**: Durable recording of a nonce's SHA-256 to the DAG before minting, so a process restart cannot reopen a replay window.
- **Mint**: Writing a commitment to the ledger with a leaf hash; only the ledger's `mint()` does this, not the model.
- **Entry gate**: Admits a capsule only if it verifies and its card metadata claims no HUMAN_ONLY or wildcard capabilities.
- **Exit gate**: Releases an action only after route policy, nonce burn, human signature verification, mint, and ledger re-verification all pass. Fail-closed.
- **HUMAN_ONLY**: The frozen set of 11 actions that can only arrive on the `human` route with a valid human signature.
- **Route**: One of `human`, `card`, `model`. HUMAN_ONLY actions are refused on `card` and `model` routes.
- **Lease**: The validity window of a commitment, capped at 15 minutes (MAX_LEASE_SECONDS = 900).
- **Action hash**: SHA-256 of canonical JSON (sorted keys, no whitespace, ASCII-only) of the action's parameters.
- **Verifier**: Gate-side object holding only a public key; checks signatures, burns nonces in memory, enforces lease cap.
- **Human signer**: Human-side code (not re-exported) that holds the encrypted private key, requires interactive TTY and passphrase per signing session.

## 3. Components

### 3.1 humanauth.verify

**Role**: Gate-side verification. Holds only a public key; nothing in this module can mint a signature.

**Public interface**:
- `MAX_LEASE_SECONDS = 900`
- `WILDCARDS = ("*", "any", "all", "")`
- `HumanAuthError` exception
- `canonical(params: dict) -> bytes`
- `action_hash(params: dict) -> str`
- `message(device, surface, action, a_hash, nonce, expiry) -> bytes`
- `Verifier(public_key_bytes, device, surface, used_nonces=None, clock=time.time)`
  - `check(action, params, signed) -> None` (raises HumanAuthError)
  - `used_nonces() -> list[str]`
- `commitment_signature_checker(public_key_bytes) -> callable[[dict], bool]`

**Behavior**: `Verifier.check` refuses wildcards, missing fields, malformed expiry, expired leases, leases over cap, replayed nonces (in-memory), and signatures that don't match the exact action/params/device/surface/nonce/expiry tuple. On success it burns the nonce in memory. `commitment_signature_checker` returns a function the ledger uses to verify a WCOMMIT's own signature before minting or verifying.

**Invariants**: The verifier never holds private key material. A nonce is burned in memory only after a successful cryptographic verify. The message format uses `|` as a field separator; no field may contain `|`, newline, NUL, or non-printable ASCII.

### 3.2 humanauth.human_only

**Role**: The permanent list of actions only a human signature can authorize, and the checks that keep cards and models away from it.

**Public interface**:
- `HUMAN_ONLY` frozenset of 11 action names
- `normalize(action) -> str` (Unicode NFKC, strip invisibles, case-fold, spaces/hyphens to underscores)
- `is_human_only(action) -> bool`
- `refuse_odd_spelling(action) -> None` (raises HumanAuthError if a HUMAN_ONLY action arrives non-canonically)
- `require_human(verifier, action, params, signed) -> None`
- `check_card_capabilities(card: dict) -> None`

**Behavior**: `is_human_only` uses `normalize` so full-width, zero-width, soft-hyphen, and Cyrillic look-alikes are recognized as HUMAN_ONLY. `refuse_odd_spelling` demands the exact canonical spelling for HUMAN_ONLY actions. `check_card_capabilities` validates that capabilities is a list of strings, no wildcards, and no HUMAN_ONLY entries (under any spelling).

**Invariants**: HUMAN_ONLY is a frozenset — changing it is a code change requiring human review. Cards are checked at mint time AND at gate entry.

### 3.3 humanauth.human_signer (human-side only)

**Role**: Creates encrypted key blobs and signs approvals. Runs only in an interactive terminal.

**Public interface**:
- `generate(passphrase) -> (encrypted_blob, public_key_bytes)`
- `sign(blob, passphrase, device, surface, action, params, lease_seconds=300) -> dict` (returns `{nonce, expiry, signature}`)

**Behavior**: Private key encrypted with scrypt (N=2^15, r=8, p=1) + AES-256-GCM. Passphrase read via getpass, never from argv/env/file. Lease validated 1..MAX_LEASE_SECONDS. Nonce is 16-byte hex. Signature is Ed25519 over the `message()` format.

**Invariants**: The key file is written owner-only (0o600 on POSIX) with O_EXCL — never overwrites. The signer is deliberately not re-exported from `vega_jacket.humanauth.__init__`.

### 3.4 humanauth.human_cli (human-side only)

**Role**: Command-line launcher for keygen and sign. Refuses to run without a TTY.

**Public interface**: `keygen --out`, `sign --key --device --surface --action --params/--params-file --lease --out`

**Behavior**: Shows the exact action and parameters, requires typing the action name back, enforces 5-second cooldown between approvals (stamp in `~/.vega_human_last_sign`, not in package). Refuses wildcard/empty action, lease over cap, non-interactive stdin/stdout.

### 3.5 commit.commit

**Role**: Turns a verified human signature into a commitment of record. Burns the nonce durably, mints to ledger for boundary crossings, records to DAG.

**Public interface**:
- `ROUTES = ("human", "card", "model")`
- `CommitRefused` exception
- `Commit(verifier, ledger, dag)`
  - `assert_unburned(signed) -> None`
  - `mint_checked(action, params, signed, boundary_crossing=True) -> dict`
  - `commit(action, params, signed, route="human", boundary_crossing=True) -> dict`

**Behavior**: `commit()` validates route, refuses odd spellings, enforces HUMAN_ONLY route policy, checks `assert_unburned`, then calls `require_human` (HUMAN_ONLY) or `verifier.check` (ordinary). `mint_checked` burns the nonce to DAG first (durable), then mints to ledger if `boundary_crossing`, then records COMMIT to DAG linked to the burn entry. Any failure raises `CommitRefused` — no partial success.

**Invariants**: Nonce burn is durable (DAG) — survives restart. HUMAN_ONLY actions cannot arrive on card/model routes. A commitment is minted by the architecture (`ledger.mint`), not by the model.

### 3.6 gate.entry_gate

**Role**: Admits only verified capsules whose cards claim no HUMAN_ONLY power.

**Public interface**:
- `Refused` exception
- `EntryGate(dag)`
  - `admit(capsule: dict) -> dict`

**Behavior**: Verifies capsule via `vega_custody.capsule.verify`. If the capsule's metadata.card exists, runs `humanauth.check_card_capabilities` on it. Records ENTRY_ADMITTED or ENTRY_REFUSED to DAG. On refusal, raises `Refused`.

**Invariants**: A capsule whose card claims a HUMAN_ONLY or wildcard capability is refused. Admission is recorded.

### 3.7 gate.exit_gate

**Role**: Releases an action only with a minted, verified commitment for exactly that action. Fail-closed.

**Public interface**:
- `Denied` exception
- `ExitGate(commit, ledger, verifier, dag)`
  - `release(action, params, signed, route="human") -> dict`

**Behavior**: Ordered checks: (1) route policy, (2) nonce unburned, (3) odd spelling, (4) HUMAN_ONLY route check, (5) signature verification via commit path, (6) mint, (7) ledger re-verify. Every denial records EXIT_DENIED to DAG; if that record fails, the action is still denied (fail-closed, REVIEW.md info finding). On success, records EXIT_RELEASED to DAG linked to the commit entry.

**Invariants**: Fail-closed — a denial is a denial even if the DAG write fails. Ledger re-verify ensures the commitment is really in the chain.

### 3.8 shell (runner scripts)

**Role**: Shell-level entry gate, execution gate, and hard-stop scripts (Termux-era runner core).

**Public interface**: Scripts in `shell/VEGA_RUNNER_CORE/` and `shell/03_RUNTIME_GOVERNANCE/`
- `vega_run.sh` — orchestrates access gate enforcer, then execution gate
- `runner.sh` — registry-based module/action permission check with tier enforcement
- `orchestrator.sh` — routing table + heuristic fallback, lane validation, preflight gates, module dispatch
- `gate.sh` — execution gate with hard stop, tier ranking, secure folder unlock requirement for write actions
- `access_gate_enforcer.sh` — hard stop check, manifest verification, minimal sanity
- `hard_stop_on/off.sh` — toggle HARD_STOP.flag

**Behavior**: All scripts are deny-by-default, log to audit log, enforce registry registration and tier requirements. Hard stop is a global kill switch checked first. Secure folder unlock (`.unlocked` file) required for write-tier actions.

**Invariants**: No action proceeds without registry entry, allowed action list, sufficient tier, and gate pass. Hard stop overrides everything.

## 4. Guarantees and non-guarantees

| Guarantee | Module | Test |
|-----------|--------|------|
| A HUMAN_ONLY action cannot be authorized without a valid human signature | humanauth.verify, humanauth.human_only, commit, gate | test_commit.py, redteam_1, redteam_2, redteam_3 |
| A used nonce cannot be replayed, even after process restart | commit.Commit.assert_unburned, humanauth.Verifier | test_commit.py lines 79-80, redteam_2 test_an_approval_cannot_be_replayed_after_a_restart |
| A commitment minted to the ledger carries a human signature the ledger verifies | commit.mint_checked, verify.commitment_signature_checker | redteam_3 J4 tests |
| A capsule whose card claims HUMAN_ONLY capability is refused at entry | gate.entry_gate, humanauth.check_card_capabilities | test_commit.py line 102-103, redteam_2 test_a_capsule_whose_card_claims_human_only_power_is_refused |
| Exit gate fails closed: denial stands even if DAG recording fails | gate.exit_gate | REVIEW.md info finding, redteam_2 test_a_failing_denial_record_still_denies |
| Odd spellings of HUMAN_ONLY actions are refused on every route | humanauth.human_only.refuse_odd_spelling | redteam_1 test_odd_spellings, redteam_3 J1 |
| Wildcard actions are never accepted | humanauth.verify.Verifier.check | redteam_1 test_wildcard_actions_never_verify |
| Human signer refuses to run without an interactive TTY | humanauth.human_cli | redteam_2 test_the_signer_refuses_to_run_without_an_interactive_terminal |

| Non-guarantee | Why |
|---------------|-----|
| Protection against an agent that can type into the human's terminal | The signer checks TTY but cannot prevent keystroke injection |
| OS-level sandbox / kernel containment | Process-level only; a side door bypassing the gate voids the guarantee |
| Hardware key (TPM, FIDO2) support | Designed only; software key with passphrase is what's built |
| Independent cryptographic audit | Not performed; reference implementation only |
| Legal enforceability of the licence | Licence text is a draft not reviewed by an attorney |

## 5. Failure modes

| Failure mode | Behavior | Test |
|--------------|----------|------|
| Tampered capsule | Entry gate refuses, records ENTRY_REFUSED | test_commit.py line 100-101, redteam_2 test_garbage_and_forged_capsules_are_refused_cleanly |
| Missing commitment | Exit gate denies at nonce burn or signature check, records EXIT_DENIED | test_commit.py lines 66-71 |
| Expired commitment | Verifier.check refuses (expiry <= now) | support_humanauth_checks #5, redteam_1 |
| Replay (same nonce) | Verifier.check refuses (in-memory); Commit.assert_unburned refuses (durable) | test_commit.py line 67, redteam_2 test_an_approval_cannot_be_replayed_after_a_restart |
| Corrupt DAG record | DAG.verify() fails; commit.mint_checked refuses if burn record fails | test_commit.py line 105, redteam_2 test_the_record_stays_valid_after_all_of_it |
| Forged commitment minted directly to ledger file | Ledger.verify() refuses (signature check) | redteam_3 J4 test_a_mint_record_appended_straight_into_the_ledger_file_still_does_not_verify |
| HUMAN_ONLY action on card/model route | Commit.commit and ExitGate.release deny before signature check | test_commit.py lines 68-69, redteam_1 test_human_only_on_card_or_model_route_is_denied |
| Lease over 15-minute cap | Verifier.check refuses (expiry - now > MAX_LEASE_SECONDS) | support_humanauth_checks #6, redteam_1 test_the_honest_signer_refuses_leases_outside_one_to_the_cap |
| Odd spelling of HUMAN_ONLY action | refuse_odd_spelling raises HumanAuthError | redteam_1 test_odd_spellings, redteam_3 J1 |
| Hard stop active | All shell gates deny immediately | shell scripts check HARD_STOP.flag first |

## 6. Dependencies and layer rules

Registry entry (verbatim from vega-umbrella-sdk registry):
- Layer: 1 authority
- Requires: [vega-custody-sdk]
- Status: BUILT

Dependencies point down layers only, never up or sideways. This kit uses vega-custody-sdk for capsules, DAG, ledger. It does not import from layers 2+. Layers 2+ (superproof, pareah, two-gate, harness, terminal, umbrella) depend on this kit.

## 7. Conformance

A third party can verify by running the test suite:
```bash
python -m tests.test_humanauth
python -m tests.test_commit
python -m tests.redteam_1_signature_and_authority
python -m tests.redteam_2_commit_gate_cli
python -m tests.redteam_3_audit_findings
```

Passing means: all 75 tests across 5 files pass (STATUS.md). The REVIEW.md scan found zero high/medium/low findings and one informational (exit_gate fail-closed denial recording).

What passing does NOT mean: independently security-reviewed, crypto expert-reviewed, production-hardened, hardware key support, legal compliance, protection against keystroke injection at the human's terminal.