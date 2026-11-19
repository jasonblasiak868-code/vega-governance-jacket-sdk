"""commit.py - turns a human signature into a commitment of record. Built so the model has no path around it:
  - signature check is the human-key verifier (public key only), HUMAN_ONLY actions go through require_human
  - the nonce is burned DURABLY (written to the DAG before anything else), so a restart cannot replay it
  - a commitment that crosses a boundary is minted by this code (ledger.mint), not by anything the model calls
  - routes: a card or model route can never carry a HUMAN_ONLY action
Raises CommitRefused on any failure; there is no partial success."""
import os
import sys
import threading

from vega_jacket import humanauth  # noqa: E402
from vega_custody.dag.dag import DagError, sha256_hex  # noqa: E402
from vega_custody.ledger.ledger import LedgerError  # noqa: E402
from vega_jacket.commit.burnmirror import BurnMirror, BurnMirrorError  # noqa: E402

ROUTES = ("human", "card", "model")
_GUARD = threading.Lock()


def _lock_for(dag):
    """One re-entrant lock per DAG object, shared by every Commit and ExitGate built on it, so two of them can never both pass with one approval."""
    with _GUARD:
        lk = getattr(dag, "_vega_commit_lock", None)
        if lk is None:
            lk = threading.RLock()
            dag._vega_commit_lock = lk
        return lk


class CommitRefused(Exception):
    pass


class Commit:
    def __init__(self, verifier, ledger, dag, mirror_path: str = None):
        self.verifier, self.ledger, self.dag = verifier, ledger, dag
        # One lock around "is it burned?" and "burn it", shared by every gate object built on this DAG: two callers can never both pass with one approval.
        self.lock = _lock_for(dag)
        self._burned, self._seen = set(), 0
        # TAMPER ALARM (fail closed, loud): every construction verifies the chain
        # FIRST. A tampered store refuses all commits loudly at startup - the
        # mismatch is an exception, never a silent tuple.
        try:
            ok, bad = dag.verify()
        except Exception as exc:
            raise CommitRefused(f"TAMPER ALARM: chain verification could not run: {exc}") from exc
        if not ok:
            raise CommitRefused(f"TAMPER ALARM: chain verification FAILED on restart - commits refused: {bad[:3]}")
        # BURN MIRROR (second independent store): a restart is not a replay window
        # EVEN IF the DAG store is reset, moved or recreated. Erasing one store
        # cannot erase the record; a DAG/mirror disagreement is a tamper alarm.
        if mirror_path is None:
            cp = getattr(dag.content, "paths", [None])[0] or os.path.abspath("dag_store")
            mirror_path = os.path.join(os.path.dirname(cp), "burns.mirror.jsonl")
        self.mirror = BurnMirror(mirror_path)
        self._refresh()          # nonces burned in earlier runs are reloaded from DAG + mirror: a restart is not a replay window

    def _refresh(self):
        """Read the NONCE_BURNED entries added to the DAG since the last look, UNION the mirror's burns.
        Called on EVERY check. A nonce burned on the DAG but missing from the mirror is treated
        as tamper (someone deleted the mirror), NOT as a replay opportunity - fail closed."""
        rows = self.dag.content.entries()
        for e in rows[self._seen:]:
            if e["kind"] == "NONCE_BURNED":
                self._burned.add(e["payload"]["nonce_sha256"])
        self._seen = len(rows)
        try:
            mirrored = self.mirror.load()
        except BurnMirrorError as exc:
            raise CommitRefused(f"TAMPER ALARM: burn mirror integrity failed: {exc}") from exc
        dag_burns = set()
        for e in rows:
            if e["kind"] == "NONCE_BURNED":
                dag_burns.add(e["payload"]["nonce_sha256"])
        missing = dag_burns - mirrored
        if missing:
            raise CommitRefused(f"TAMPER ALARM: {len(missing)} DAG burns missing from the burn mirror - mirror deleted or truncated; commits refused")
        self._burned |= mirrored

    @staticmethod
    def _nonce_hash(signed: dict) -> str:
        if not isinstance(signed, dict) or "nonce" not in signed:
            raise CommitRefused("signed approval has no nonce")
        return sha256_hex(str(signed["nonce"]).encode("utf-8"))

    def assert_unburned(self, signed: dict) -> None:
        with self.lock:
            self._refresh()
            if self._nonce_hash(signed) in self._burned:
                raise CommitRefused("replay: this approval was already used (durable record)")

    def mint_checked(self, action: str, params: dict, signed: dict, boundary_crossing: bool = True) -> dict:
        """Precondition: the caller has verified the signature. Burns the nonce, mints, records."""
        nonce_hash = self._nonce_hash(signed)
        with self.lock:
            self._refresh()
            if nonce_hash in self._burned:                      # re-checked at the moment of burning, not only at the start of the call
                raise CommitRefused("replay: this approval was already used (durable record)")
            try:
                burn = self.dag.record("NONCE_BURNED", {"nonce_sha256": nonce_hash, "action": action})
            except DagError as exc:
                raise CommitRefused(f"could not record nonce burn, refusing: {exc}") from exc
            self._burned.add(nonce_hash)
            try:
                self.mirror.append(nonce_hash, action)   # second independent store, fsync'd
            except OSError as exc:
                raise CommitRefused(f"burn mirror write failed, refusing (no single-store burn): {exc}") from exc
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
        with self.lock:                                         # check, verify and burn as one step
            self.assert_unburned(signed)
            try:
                if action in humanauth.HUMAN_ONLY:
                    humanauth.require_human(self.verifier, action, params, signed)
                else:
                    self.verifier.check(action, params, signed)
            except humanauth.HumanAuthError as exc:
                raise CommitRefused(f"human authority check failed: {exc}") from exc
            return self.mint_checked(action, params, signed, boundary_crossing)
