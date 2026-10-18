# vega-governance-jacket-sdk

![vega-governance-jacket-sdk](assets/tile.svg)

The governance jacket: nothing leaves without a human-signed commitment for exactly that action.

> **Licensing.** Source-available, not open source. Free for personal use; free for registered small businesses (under US$1M revenue and valuation); everyone else needs a commercial license (see LICENSE; for a commercial license write to jasonblasiak.ai.mail@gmail.com). Patent pending. Draft licence text, not yet reviewed by an attorney.

Package: `vega_jacket` (src layout). Depends on: vega-custody-sdk.

## Modules

| Module | What it does |
|---|---|
| `humanauth` | Human-only actions. The gate holds a public key only; it can verify, never sign. Single use, exact action and parameters, 15-minute lease cap. |
| `commit` | Turns a signature into a commitment of record; the nonce is burned durably so a restart is not a replay window. |
| `gate` | Entry gate (verified capsules only) and exit gate (a minted, verified commitment for exactly this action, or nothing leaves). Fail closed. |
| `shell` | Shell-level entry gate, execution gate and hard stop scripts (Termux-era runner core). |

## What it does NOT do (read this)

- The signer must run in the human's own terminal; an agent that can type into that terminal defeats it.
- Process containment is not an operating-system sandbox.
- Gates guard the paths they are wired into: a side door that bypasses the gate voids the guarantee.

## Status

See STATUS.md. Tests: 64 tests in 5 files, all passing.  See SECURITY.md for the threat model.

## Run the tests

Put `src` of this repo and of the repos it depends on on PYTHONPATH, then run each file in `tests/`.
