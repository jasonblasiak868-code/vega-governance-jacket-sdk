"""Regression tests for the security-audit pass over the governance jacket (2026-10-17)."""
import os
import pathlib
import tempfile
import unittest

from vega_custody.dag.dag import Dag
from vega_custody.ledger.backend_local import LocalBackend
from vega_custody.ledger.ledger import Ledger
from vega_jacket import humanauth
from vega_jacket.commit.commit import Commit, CommitRefused
from vega_jacket.humanauth import human_only, human_signer, verify

PW, DEV, SURF = "correct horse battery", "dev-audit", "surf-audit"


def rig():
    blob, pub = human_signer.generate(PW)
    t = pathlib.Path(tempfile.mkdtemp())
    return blob, pub, t


def fresh_commit(pub, t):
    """A new Commit over the SAME files, as a second process would build it."""
    dag = Dag([t / "c.jsonl"], [t / "l.jsonl"])
    led = Ledger([LocalBackend(t / "led.jsonl")])
    return Commit(humanauth.Verifier(pub, DEV, SURF), led, dag)


class J1_LookAlikeActionNames(unittest.TestCase):
    """MEDIUM. A human-only action spelled with full-width letters or invisible characters was not recognised as human-only by the gate and could be signed and run as an ordinary action, while a
    downstream tool that folds Unicode would have executed the human-only action."""

    FULLWIDTH = "ｒｅｌｅａｓｅ_ｐｕｂｌｉｃ"
    ZERO_WIDTH = "release​_public"
    SOFT_HYPHEN = "re­lease_public"
    CYRILLIC = "rеlease_public"                       # Cyrillic small ie

    def test_compatibility_and_invisible_spellings_are_recognised_as_human_only(self):
        for name in (self.FULLWIDTH, self.ZERO_WIDTH, self.SOFT_HYPHEN, "Release_Public", "release-public", " RELEASE PUBLIC "):
            self.assertTrue(human_only.is_human_only(name), repr(name))
            with self.assertRaises(humanauth.HumanAuthError, msg=repr(name)):
                human_only.refuse_odd_spelling(name)

    def test_non_ascii_names_can_never_be_signed_or_verified(self):
        blob, pub, t = rig()
        for name in (self.FULLWIDTH, self.ZERO_WIDTH, self.SOFT_HYPHEN, self.CYRILLIC, "emoji\U0001F600action", "tab\taction"):
            with self.assertRaises(humanauth.HumanAuthError, msg=repr(name)):
                human_signer.sign(blob, PW, DEV, SURF, name, {})
            with self.assertRaises(humanauth.HumanAuthError):
                verify.message(DEV, SURF, name, "0" * 64, "n", 1)
        self.assertTrue(verify.message(DEV, SURF, "release_public", "0" * 64, "n", 1).startswith(b"WCOMMIT|"))

    def test_the_commit_path_refuses_a_look_alike_human_only_name_outright(self):
        blob, pub, t = rig()
        c = fresh_commit(pub, t)
        for name in (self.FULLWIDTH, self.ZERO_WIDTH, "Release_Public"):
            with self.assertRaises(CommitRefused, msg=repr(name)):
                c.commit(name, {}, {"nonce": "n", "expiry": 1, "signature": "00"}, route="human")

    def test_cards_cannot_carry_a_look_alike_human_only_capability(self):
        for cap in (self.FULLWIDTH, self.ZERO_WIDTH, self.SOFT_HYPHEN):
            with self.assertRaises(humanauth.HumanAuthError):
                humanauth.check_card_capabilities({"capabilities": [cap]})


class J2_OneSignatureTwoProcesses(unittest.TestCase):
    """The candidate was a double spend across two live processes (each keeps its own used-nonce set). The chain refuses a writer whose view is stale, so the second spend is refused. Kept as a
    regression test so that protection cannot be removed unnoticed."""

    def test_the_same_approval_cannot_be_committed_by_two_live_commit_objects(self):
        blob, pub, t = rig()
        a, b = fresh_commit(pub, t), fresh_commit(pub, t)                      # both loaded before either spends
        signed = human_signer.sign(blob, PW, DEV, SURF, "conductor_step:x", {}, 300)
        a.commit("conductor_step:x", {}, signed, route="human")
        with self.assertRaises(CommitRefused):
            b.commit("conductor_step:x", {}, signed, route="human")
        burned = [e for e in Dag([t / "c.jsonl"], [t / "l.jsonl"]).content.entries() if e["kind"] == "NONCE_BURNED"]
        self.assertEqual(len(burned), 1)

    def test_a_new_process_loads_the_burned_nonces_from_the_record(self):
        blob, pub, t = rig()
        signed = human_signer.sign(blob, PW, DEV, SURF, "conductor_step:x", {}, 300)
        fresh_commit(pub, t).commit("conductor_step:x", {}, signed, route="human")
        with self.assertRaises(CommitRefused):
            fresh_commit(pub, t).commit("conductor_step:x", {}, signed, route="human")


class J3_KeyFilePermissions(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_a_new_key_file_is_owner_only(self):
        from vega_jacket.humanauth import human_cli

        class A:
            out = str(pathlib.Path(tempfile.mkdtemp()) / "k.bin")
        import sys
        old_tty, old_pass = human_cli._need_tty, human_cli._passphrase
        human_cli._need_tty, human_cli._passphrase = (lambda: None), (lambda confirm=False: PW)
        try:
            human_cli.keygen(A)
        finally:
            human_cli._need_tty, human_cli._passphrase = old_tty, old_pass
        self.assertEqual(oct(os.stat(A.out).st_mode & 0o777), "0o600")

    def test_an_existing_key_file_is_never_overwritten(self):
        from vega_jacket.humanauth import human_cli

        class A:
            out = str(pathlib.Path(tempfile.mkdtemp()) / "k.bin")
        pathlib.Path(A.out).write_bytes(b"precious")
        old_tty, old_pass = human_cli._need_tty, human_cli._passphrase
        human_cli._need_tty, human_cli._passphrase = (lambda: None), (lambda confirm=False: PW)
        try:
            with self.assertRaises(SystemExit):
                human_cli.keygen(A)
        finally:
            human_cli._need_tty, human_cli._passphrase = old_tty, old_pass
        self.assertEqual(pathlib.Path(A.out).read_bytes(), b"precious")


class J4_ForgedMint(unittest.TestCase):
    """HIGH (design). The ledger trusted whoever held mint(): the commitment had no human signature in it, so anything with the ledger object could fabricate a commitment that every gate then
    accepted. Now a ledger built with the human key's signature checker refuses to mint or verify a WCOMMIT the human did not sign."""

    def keyed(self):
        blob, pub = human_signer.generate(PW)
        t = pathlib.Path(tempfile.mkdtemp())
        led = Ledger([LocalBackend(t / "led.jsonl")], commitment_check=verify.commitment_signature_checker(pub))
        dag = Dag([t / "c.jsonl"], [t / "l.jsonl"])
        return blob, pub, t, led, dag, Commit(humanauth.Verifier(pub, DEV, SURF), led, dag)

    def forged(self, **kw):
        c = {"kind": "WCOMMIT", "device": DEV, "surface": SURF, "action": "run_job", "action_hash": "ab" * 32, "expiry": 9999999999, "nonce_sha256": "cd" * 32}
        c.update(kw)
        return c

    def test_a_commitment_fabricated_by_whoever_holds_the_ledger_is_refused(self):
        from vega_custody.ledger.ledger import LedgerRefused
        blob, pub, t, led, dag, commit = self.keyed()
        for c in (self.forged(), self.forged(nonce="n", signature="00" * 64), self.forged(nonce="n", signature="zz"), self.forged(signature="ab" * 64)):
            with self.assertRaises(LedgerRefused, msg=repr(c)[:80]):
                led.mint(c)
            self.assertFalse(led.verify(c))

    def test_a_signature_from_a_different_key_is_refused(self):
        from vega_custody.ledger.ledger import LedgerRefused
        blob, pub, t, led, dag, commit = self.keyed()
        other_blob, other_pub = human_signer.generate(PW)
        signed = human_signer.sign(other_blob, PW, DEV, SURF, "run_job", {"x": 1}, 300)
        import hashlib
        c = self.forged(action_hash=humanauth.action_hash({"x": 1}), expiry=signed["expiry"], nonce=signed["nonce"], signature=signed["signature"], nonce_sha256=hashlib.sha256(signed["nonce"].encode()).hexdigest())
        with self.assertRaises(LedgerRefused):
            led.mint(c)

    def test_a_commitment_edited_after_minting_no_longer_verifies(self):
        blob, pub, t, led, dag, commit = self.keyed()
        signed = human_signer.sign(blob, PW, DEV, SURF, "run_job", {"x": 1}, 300)
        c = commit.commit("run_job", {"x": 1}, signed, route="human")["commitment"]
        self.assertTrue(led.verify(c))
        for field, value in (("action", "release_public"), ("action_hash", "00" * 32), ("expiry", c["expiry"] + 600), ("device", "other")):
            self.assertFalse(led.verify(dict(c, **{field: value})), field)

    def test_the_real_path_still_works_end_to_end_and_the_read_only_view_verifies(self):
        blob, pub, t, led, dag, commit = self.keyed()
        signed = human_signer.sign(blob, PW, DEV, SURF, "run_job", {"x": 1}, 300)
        out = commit.commit("run_job", {"x": 1}, signed, route="human")
        self.assertTrue(led.verify(out["commitment"]))
        self.assertTrue(led.reader().verify(out["commitment"]))

    def test_a_mint_record_appended_straight_into_the_ledger_file_still_does_not_verify(self):
        """Someone who can write the ledger file can append a hash-valid MINT record without going through mint(): verify() must still demand the human signature."""
        from vega_custody.dag.dag import Chain, canonical, sha256_hex
        blob, pub, t, led, dag, commit = self.keyed()
        c = self.forged()
        other = Chain([str(t / "led.jsonl")])
        other.record("MINT", {"leaf": sha256_hex(canonical(c)), "commitment": c})
        self.assertFalse(led.verify(c))

    def test_other_kinds_are_not_affected(self):
        blob, pub, t, led, dag, commit = self.keyed()
        led.mint({"kind": "SUPERPROOF_ROOT", "action": "seal_tier0", "action_hash": "aa" * 32, "expiry": 0, "nonce_sha256": "bb" * 32})


if __name__ == "__main__":
    unittest.main()
