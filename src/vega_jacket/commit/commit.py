"""commit.py - turns a human signature into a commitment of record. Built so the model has no path around it:
  - signature check is the human-key verifier (public key only), HUMAN_ONLY actions go through require_human
  - the nonce is burned DURABLY (written to the DAG before anything else), so a restart cannot replay it
  - a commitment that crosses a boundary is minted by this code (ledger.mint), not by anything the model calls
  - routes: a card or model route can never carry a HUMAN_ONLY action
Raises CommitRefused on any failure; there is no partial success."""
import os
import sys

from vega_jacket import humanauth  # noqa: E402
from vega_custody.dag.dag import DagError, sha256_hex  # noqa: E402
from vega_custody.ledger.ledger import LedgerError  # noqa: E402

ROUTES = ("human", "card", "model")


class CommitRefused(Exception):
    pass


class Commit:
    def __init__(self, verifier, ledger, dag):
        self.verifier, self.ledger, self.dag = verifier, ledger, dag
        # nonces burned in earlier runs are reloaded from the DAG: a restart is not a replay window
        self._burned = {e["payload"]["nonce_sha256"] for e in dag.content.entries() if e["kind"] == "NONCE_BURNED"}

    @staticmethod
    def _nonce_hash(signed: dict) -> str:
        if not isinstance(signed, dict) or "nonce" not in signed:
            raise CommitRefused("signed approval has no nonce")
        return sha256_hex(str(signed["nonce"]).encode("utf-8"))

    def assert_unburned(self, signed: dict) -> None:
        if self._nonce_hash(signed) in self._burned:
            raise CommitRefused("replay: this approval was already used (durable record)")

    def mint_checked(self, action: str, params: dict, signed: dict, boundary_crossing: bool = True) -> dict:
        """Precondition: the caller has verified the signature. Burns the nonce, mints, records."""
        nonce_hash = self._nonce_hash(signed)
        try:
            burn = self.dag.record("NONCE_BURNED", {"nonce_sha256": nonce_hash, "action": action})
        except DagError as exc:
            raise CommitRefused(f"could not record nonce burn, refusing: {exc}") from exc
        self._burned.add(nonce_hash)
        commitment = {"kind": "WCOMMIT", "device": self.verifier.device, "surface": self.verifier.surface,
                      "action": action, "action_hash": humanauth.action_hash(params),
                      "expiry": int(signed["expiry"]), "nonce_sha256": nonce_hash, "nonce": signed["nonce"], "signature": signed["signature"]}
        receipt = None
        if boundary_crossing:
            try:
                receipt = self.ledger.mint(commitment)
            except LedgerError as exc:
                raise CommitRefused(f"mint refused: {exc}") from exc
        try:
            entry = self.dag.record("COMMIT", {"commitment": commitment, "minted": receipt is not None,
                                               "leaf": receipt["leaf"] if receipt else None},
                                    parents=[burn["entry_hash"]])
        except DagError as exc:
            raise CommitRefused(f"commitment minted but DAG record failed: {exc}") from exc
        return {"commitment": commitment, "receipt": receipt, "entry": entry["entry_hash"]}

    def commit(self, action: str, params: dict, signed: dict, route: str = "human",
               boundary_crossing: bool = True) -> dict:
        if route not in ROUTES:
            raise CommitRefused(f"unknown route {route!r}")
        try:
            humanauth.refuse_odd_spelling(action)
        except humanauth.HumanAuthError as exc:
            raise CommitRefused(str(exc)) from exc
        if humanauth.is_human_only(action) and route != "human":
            raise CommitRefused(f"{action!r} is HUMAN_ONLY and cannot arrive on the {route} route")
        self.assert_unburned(signed)
        try:
            if action in humanauth.HUMAN_ONLY:
                humanauth.require_human(self.verifier, action, params, signed)
            else:
                self.verifier.check(action, params, signed)
        except humanauth.HumanAuthError as exc:
            raise CommitRefused(f"human authority check failed: {exc}") from exc
        return self.mint_checked(action, params, signed, boundary_crossing)
