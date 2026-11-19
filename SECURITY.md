# SECURITY

Report a problem to jasonblasiak.ai.mail@gmail.com. Please do not post an exploitable detail in a public issue.

## Threat model in one paragraph

The code is meant to stop an AI or automated process from taking an action no human approved. Assumptions: the human's private key never touches the machine that runs the model; the machine's clock and disk are not controlled by the attacker; every path that can cause an effect is routed through the gates. It does not defend against a compromised operating system, a stolen human key, or a bypass path that was never wired through the gate.

## What was done

An automated review (REVIEW.md) ran static rules, secret-shape checks and the tests; hand-written red-team tests are in tests/ where present. None of the cryptography or protocol code has had an independent expert review. A clean scan is not proof of safety.

## Secrets

No credential belongs in this repo. Run a secret scanner (for example gitleaks) before every commit.

## Legacy shell layer

The `shell/` folder holds the Termux-era runner scripts. They are kept for reference and are NOT the strong path: the Python gates in `src/` are. As of 2026-10-20 `hard_stop_off.sh` refuses to lift the hard stop (that needs the human-signed restore) and `gate.sh` accepts only plain-word module and action names. Do not present the shell gate as an authority check.


## 2026-11-19 EXTERNAL RED-TEAM RESPONSE (verified & closed)

Independent tester: signature gate HELD (no action released without human signature).
Two written guarantees failed on their copy in narrow cases; both reproduced locally and closed:

1. "A restart is not a replay window" failed when the DAG store was reset/lost between runs
   (burn record lived only in the first store). FIX: commit b31ab6a04524 adds burnmirror.py -
   a hash-chained append-only second store; replay is now refused if EITHER store shows the burn;
   DAG/mirror disagreement = fail-closed tamper alarm, not a replay opportunity.
2. No loud alarm on tamper. FIX: commit ae5cbb63d22f - every gate construction verifies the chain
   BEFORE any action; a tampered chain raises a refusal naming the entry (loud, fail closed).

Verification: 6-scenario harness all pass (normal burn; restart-replay refused; store-reset
replay refused via mirror; tamper loud at restart; mirror-deleted alarm; fresh install normal).
Repo regression: tests/test_commit.py 17/17 PASS. Disclosure gate: dependent claims written to
provisional addendum before this push (PROVISIONAL_ADDENDUM_BURN_MIRROR_ALARM_20261119.md).

Two smaller narrow-case issues reported by the tester are pending reproduction.
