"""RED TEAM PASS 2 (jacket): attacks on state (restart, failing disk), on the gates, and on the human-side launcher."""
import os
import subprocess
import sys
import unittest

import fixture_jacket as fx
from vega_custody.capsule import capsule as cap
from vega_custody.dag.dag import DagError
from vega_jacket import humanauth
from vega_jacket.commit.commit import Commit, CommitRefused
from vega_jacket.gate.entry_gate import Refused
from vega_jacket.gate.exit_gate import Denied
from vega_jacket.humanauth import human_cli

P = {"to": "bob", "amount": 9}


class StateAttacks(unittest.TestCase):
    def setUp(self):
        self.f = fx.build()

    def test_an_approval_cannot_be_replayed_after_a_restart(self):
        signed = self.f.sign("send_email", P)
        self.f.commit.commit("send_email", P, signed)
        fresh_verifier = humanauth.Verifier(self.f.pub, fx.DEV, fx.SURF)       # the process restarted: in-memory nonces are gone
        fresh_commit = Commit(fresh_verifier, self.f.led, self.f.dag)
        with self.assertRaises(CommitRefused) as cm:
            fresh_commit.commit("send_email", P, signed)
        self.assertIn("replay", str(cm.exception))

    def test_if_the_burn_cannot_be_recorded_nothing_is_minted(self):
        orig = self.f.dag.record

        def failing(kind, payload, parents=None):
            if kind == "NONCE_BURNED":
                raise DagError("disk full")
            return orig(kind, payload, parents)
        self.f.dag.record = failing
        before = len(self.f.led.chain.entries())
        with self.assertRaises(CommitRefused):
            self.f.commit.commit("send_email", P, self.f.sign("send_email", P))
        self.assertEqual(len(self.f.led.chain.entries()), before)

    def test_a_failing_denial_record_still_denies(self):
        def failing(*a, **k):
            raise DagError("disk full")
        self.f.dag.record = failing
        with self.assertRaises(Denied):
            self.f.gate.release("send_email", P, {"nonce": "n", "expiry": 1, "signature": "00"}, route="human")

    def test_an_approval_for_other_parameters_or_another_action_never_releases(self):
        signed = self.f.sign("send_email", P)
        with self.assertRaises(Denied):
            self.f.gate.release("send_email", dict(P, amount=10), signed)
        with self.assertRaises(Denied):
            self.f.gate.release("delete_file", P, signed)
        out = self.f.gate.release("send_email", P, signed)                      # the genuine use still works, once
        self.assertTrue(self.f.led.verify(out["commitment"]))
        with self.assertRaises(Denied):
            self.f.gate.release("send_email", P, signed)

    def test_the_readonly_ledger_cannot_substitute_for_the_commit_step(self):
        out = self.f.commit.commit("send_email", P, self.f.sign("send_email", P))
        r = self.f.led.reader()
        self.assertTrue(r.verify(out["commitment"]))
        self.assertFalse(hasattr(r, "mint"))

    def test_the_record_stays_valid_after_all_of_it(self):
        self.f.commit.commit("send_email", P, self.f.sign("send_email", P))
        self.assertTrue(self.f.dag.verify()[0])


class EntryGateAttacks(unittest.TestCase):
    def setUp(self):
        self.f = fx.build()

    def test_garbage_and_forged_capsules_are_refused_cleanly(self):
        good = cap.make("hi", {"source": "u"})
        for bad in (None, [], "x", {}, dict(good, data_b64="AAAA"), dict(good, prefix_hash="0" * 64)):
            with self.assertRaises(Refused):
                self.f.entry.admit(bad)

    def test_a_capsule_whose_card_claims_human_only_power_is_refused(self):
        for caps in (["release_public"], "mint_commitment", ["Spend-Funds"]):
            c = cap.make("hi", {"source": "u", "card": {"capabilities": caps}})
            with self.assertRaises(Refused):
                self.f.entry.admit(c)
        self.f.entry.admit(cap.make("hi", {"source": "u", "card": {"capabilities": ["read"]}}))


class LauncherAttacks(unittest.TestCase):
    def test_the_signer_refuses_to_run_without_an_interactive_terminal(self):
        r = subprocess.run([sys.executable, "-W", "ignore", "-m", "vega_jacket.humanauth.human_cli", "sign", "--key", "nope", "--device", "d", "--surface", "s", "--action", "send_email"],
                           capture_output=True, text=True, input="", timeout=60)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSED", r.stderr + r.stdout)

    def test_the_cooldown_stamp_lives_in_the_users_home_not_in_the_package(self):
        self.assertTrue(human_cli._STAMP.startswith(os.path.expanduser("~")))
        self.assertNotIn("site-packages", human_cli._STAMP)


if __name__ == "__main__":
    unittest.main()
