"""exit_gate.py - nothing leaves without a minted, verified commitment for exactly this action. Fail closed.

Order, every time:
  1. route policy: a HUMAN_ONLY action on a card or model route is denied before anything else
  2. the approval has not been used (durable, survives restart)
  3. human signature check - HUMAN_ONLY actions through humanauth.require_human
  4. burn nonce + mint commitment (architecture, not the model)
  5. ledger.verify: re-read the ledger off disk and confirm the commitment is really there
Every denial is recorded to the DAG; if recording the denial fails the action is still denied."""
import os
import sys

from vega_jacket import humanauth  # noqa: E402
from vega_jacket.commit.commit import ROUTES, CommitRefused  # noqa: E402


class Denied(Exception):
    pass


class ExitGate:
    def __init__(self, commit, ledger, verifier, dag):
        self.commit, self.ledger, self.verifier, self.dag = commit, ledger, verifier, dag

    def _deny(self, action, reason):
        try:
            self.dag.record("EXIT_DENIED", {"action": action, "reason": reason})
        except Exception:  # reviewed: the action is denied below whether or not the denial could be recorded (fail closed)
            pass
        raise Denied(reason)

    def release(self, action: str, params: dict, signed: dict, route: str = "human") -> dict:
        if route not in ROUTES:
            self._deny(action, f"unknown route {route!r}")
        try:
            humanauth.refuse_odd_spelling(action)
        except humanauth.HumanAuthError as exc:
            self._deny(action, str(exc))
        if humanauth.is_human_only(action) and route != "human":
            self._deny(action, f"HUMAN_ONLY action on the {route} route")
        try:
            self.commit.assert_unburned(signed)
            if action in humanauth.HUMAN_ONLY:
                humanauth.require_human(self.verifier, action, params, signed)
            else:
                self.verifier.check(action, params, signed)
            out = self.commit.mint_checked(action, params, signed, boundary_crossing=True)
        except (CommitRefused, humanauth.HumanAuthError) as exc:
            self._deny(action, str(exc))
        if not self.ledger.verify(out["commitment"]):
            self._deny(action, "commitment minted but not verifiable in the ledger")
        self.dag.record("EXIT_RELEASED", {"action": action, "action_hash": out["commitment"]["action_hash"],
                                          "leaf": out["receipt"]["leaf"]}, parents=[out["entry"]])
        return out
