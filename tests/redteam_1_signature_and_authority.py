"""RED TEAM PASS 1 (jacket): attacks on the signature itself and on what counts as human-only authority."""
import threading
import unittest

import fixture_jacket as fx
from vega_jacket import humanauth
from vega_jacket.commit.commit import CommitRefused
from vega_jacket.gate.exit_gate import Denied
from vega_jacket.humanauth import human_signer
from vega_jacket.humanauth.verify import HumanAuthError, message

P = {"to": "alice", "amount": 5}


class SignatureAttacks(unittest.TestCase):
    def setUp(self):
        self.f = fx.build()

    def test_field_separator_cannot_be_smuggled_into_any_signed_field(self):
        """Attack: '|' separates fields, so 'a|b' in one field could line up with two fields of another tuple. Refused at the shared message builder."""
        for kw in ({"action": "send|x"}, {"device": "d|e"}, {"surface": "s\nt"}, {"nonce": "n|1"}, {"action": ""}, {"nonce": "a\x00b"}):
            args = dict(device="dev", surface="surf", action="act", a_hash="h" * 64, nonce="n" * 8, expiry=100)
            args.update({("a_hash" if k == "action_hash" else k): v for k, v in kw.items()})
            with self.assertRaises(HumanAuthError):
                message(**args)
        with self.assertRaises(HumanAuthError):
            self.f.ver.check("send|x", P, self.f.sign("send", P))
        with self.assertRaises(HumanAuthError):
            self.f.sign("send|x", P)

    def test_one_approval_used_by_many_threads_at_once_passes_exactly_once(self):
        """Attack: race the check-then-burn. Sixteen threads present the same approval together."""
        signed = self.f.sign("send_email", P)
        import time

        class Slow:                                   # widens the check-then-burn window so the race is deterministic, not luck
            def __init__(self, inner):
                self.inner = inner

            def verify(self, sig, msg):
                time.sleep(0.05)
                return self.inner.verify(sig, msg)
        self.f.ver._pub = Slow(self.f.ver._pub)
        barrier, results = threading.Barrier(16), []

        def go():
            barrier.wait()
            try:
                self.f.ver.check("send_email", P, signed)
                results.append("ok")
            except HumanAuthError:
                results.append("refused")
        ts = [threading.Thread(target=go) for _ in range(16)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("refused"), 15)

    def test_malformed_approvals_raise_only_the_documented_error(self):
        good = self.f.sign("send_email", P)
        bad = [None, [], "x", 5, {}, dict(good, nonce=5), dict(good, signature=5), dict(good, signature="zz"), dict(good, expiry="abc"), dict(good, expiry="1e9"),
               dict(good, expiry=True), dict(good, expiry=None), dict(good, expiry=1.5), dict(good, expiry=-1), dict(good, expiry=10 ** 30), dict(good, signature=good["signature"][:-2])]
        for b in bad:
            with self.assertRaises(HumanAuthError, msg=repr(b)[:70]):
                self.f.ver.check("send_email", P, b)

    def test_parameters_that_are_not_canonical_json_are_refused(self):
        for params in ({"x": float("nan")}, {"x": {1, 2}}, {"x": object()}):
            with self.assertRaises(HumanAuthError):
                humanauth.action_hash(params)

    def test_approval_is_bound_to_action_params_device_and_surface(self):
        signed = self.f.sign("send_email", P)
        with self.assertRaises(HumanAuthError):
            self.f.ver.check("send_email", dict(P, amount=6), signed)
        with self.assertRaises(HumanAuthError):
            self.f.ver.check("delete_file", P, signed)
        other = humanauth.Verifier(self.f.pub, "other-device", fx.SURF)
        with self.assertRaises(HumanAuthError):
            other.check("send_email", P, signed)
        other2 = humanauth.Verifier(self.f.pub, fx.DEV, "other-surface")
        with self.assertRaises(HumanAuthError):
            other2.check("send_email", P, signed)

    def test_key_order_in_parameters_does_not_matter_but_content_does(self):
        signed = self.f.sign("send_email", {"a": 1, "b": 2})
        self.f.ver.check("send_email", {"b": 2, "a": 1}, signed)      # same content, different order: accepted once

    def test_wildcard_actions_never_verify(self):
        for a in ("*", "", "any", "all", "release_*", "*_public"):
            with self.assertRaises(HumanAuthError):
                self.f.ver.check(a, P, {"nonce": "n", "expiry": 9999999999, "signature": "00"})

    def test_the_honest_signer_refuses_leases_outside_one_to_the_cap(self):
        for lease in (0, -1, 901, 86400, True, 1.5, "300"):
            with self.assertRaises(HumanAuthError, msg=str(lease)):
                self.f.sign("send_email", P, lease)


class AuthorityAttacks(unittest.TestCase):
    def setUp(self):
        self.f = fx.build()

    def test_a_card_cannot_carry_human_only_power_in_any_spelling_or_shape(self):
        """Attack: a bare string is read letter by letter; other spellings of the same action slip past an exact-match test."""
        for caps in ("release_public", b"release_public", ["Release_Public"], [" release_public "], ["release-public"], ["RELEASE PUBLIC"], ["mint_commitment"],
                     ["read", 5], ["read", None], ["rel*"], 7, {"a": 1}):
            with self.assertRaises(HumanAuthError, msg=repr(caps)):
                humanauth.check_card_capabilities({"capabilities": caps})
        for card in (None, [], "card", 3):
            with self.assertRaises(HumanAuthError):
                humanauth.check_card_capabilities(card)
        humanauth.check_card_capabilities({"capabilities": ["read_file", "summarize"]})      # honest cards pass
        humanauth.check_card_capabilities({})

    def test_odd_spellings_of_human_only_actions_are_refused_on_every_route(self):
        for odd in ("Release_Public", "release-public", " release_public", "RELEASE_PUBLIC"):
            signed = self.f.sign(odd, P) if "|" not in odd else None
            with self.assertRaises(CommitRefused):
                self.f.commit.commit(odd, P, signed, route="card")
            with self.assertRaises(Denied):
                self.f.gate.release(odd, P, signed, route="human")

    def test_human_only_on_card_or_model_route_is_denied_even_with_a_valid_signature(self):
        for route in ("card", "model", "weird"):
            signed = self.f.sign("release_public", P)
            with self.assertRaises((Denied, CommitRefused)):
                self.f.gate.release("release_public", P, signed, route=route)
        self.f.gate.release("release_public", P, self.f.sign("release_public", P), route="human")


if __name__ == "__main__":
    unittest.main()
