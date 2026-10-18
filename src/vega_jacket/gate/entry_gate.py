"""entry_gate.py - nothing is admitted unless it is a verified capsule that claims no human-only authority.
Admission is recorded; a capsule whose card metadata claims a HUMAN_ONLY or wildcard capability is refused."""
import os
import sys

from vega_jacket import humanauth  # noqa: E402
from vega_custody.capsule import capsule as capsule_mod  # noqa: E402


class Refused(Exception):
    pass


class EntryGate:
    def __init__(self, dag):
        self.dag = dag

    def admit(self, c: dict) -> dict:
        try:
            capsule_mod.verify(c)
            card = c.get("metadata", {}).get("card")
            if card is not None:
                humanauth.check_card_capabilities(card)
        except (capsule_mod.CapsuleError, humanauth.HumanAuthError) as exc:
            try:
                self.dag.record("ENTRY_REFUSED", {"reason": str(exc), "claimed_prefix_hash": c.get("prefix_hash")})
            except Exception:
                pass
            raise Refused(str(exc)) from exc
        self.dag.record("ENTRY_ADMITTED", {"capsule_prefix_hash": c["prefix_hash"], "data_sha256": c["data_sha256"]})
        return c
