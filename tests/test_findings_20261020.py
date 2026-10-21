"""Regression tests (2026-10-20) for the legacy shell layer: the shell gate matched module names as regular expressions (so '.*' was ALLOWED), and hard_stop_off.sh
lifted the hard stop with no authority at all. The shell layer is not the strong path (the Python gates are), but it must not be weaker than it claims."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import fixture_jacket as fx
from vega_jacket import humanauth
from vega_jacket.commit.commit import Commit, CommitRefused
from vega_jacket.gate.exit_gate import Denied, ExitGate

HERE = pathlib.Path(__file__).resolve().parent.parent
GATE_DIR = HERE / "shell" / "03_RUNTIME_GOVERNANCE" / "EXECUTION_GATE"
BASH = shutil.which("bash")


@unittest.skipUnless(BASH, "bash is not available")
class ShellGate(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.d.name)
        (self.root / "rg").mkdir()
        (self.root / "rg" / "modules.jsonl").write_text('{"name":"alpha","tier":"read","allowed":["run","view"]}\n{"name":"beta","tier":"write","allowed":["run"]}\n', encoding="utf-8")

    def tearDown(self):
        self.d.cleanup()

    def gate(self, module, action):
        env = dict(os.environ, REGISTRY=str(self.root / "rg" / "modules.jsonl"), AUDIT=str(self.root / "rg" / "audit.log"), VEGA_ROOT=str(self.root))
        # the two words travel in environment variables: Windows cuts a newline out of a command-line argument, which would hide exactly the case being tested
        env.update(GATE_TEST_MODULE=module, GATE_TEST_ACTION=action)
        r = subprocess.run([BASH, "-c", 'bash "$1" "$GATE_TEST_MODULE" "$GATE_TEST_ACTION"', "_", str(GATE_DIR / "gate.sh")], capture_output=True, text=True, env=env, timeout=30)
        return r.returncode, r.stdout

    def test_a_registered_module_and_allowed_action_is_allowed(self):
        self.assertEqual(self.gate("alpha", "run")[0], 0)

    def test_an_unregistered_module_is_denied(self):
        self.assertEqual(self.gate("gamma", "run")[0], 1)

    def test_a_regular_expression_is_not_a_module_name(self):
        for bad in (".*", "a.pha", "al*", "^", "alpha|beta", "[a-z]lpha", "alph[a]", "(alpha)"):
            code, out = self.gate(bad, "run")
            self.assertEqual(code, 1, "%r was allowed: %s" % (bad, out))
            self.assertIn("DENY", out)

    def test_an_action_is_not_an_expression_or_a_second_line_either(self):
        for bad in (".*", "run|view", "ru.", "run\nview"):
            self.assertEqual(self.gate("alpha", bad)[0], 1, repr(bad))

    def test_a_newline_in_a_name_cannot_forge_an_audit_line(self):
        self.gate("alpha\n2026 | beta | write | ALLOW | forged", "run")
        log = (self.root / "rg" / "audit.log").read_text(encoding="utf-8") if (self.root / "rg" / "audit.log").exists() else ""
        self.assertNotIn("forged", log)

    def test_two_registry_lines_for_one_name_are_denied_as_ambiguous(self):
        (self.root / "rg" / "modules.jsonl").write_text('{"name":"dup","tier":"read","allowed":["run"]}\n{"name":"dup","tier":"core","allowed":["run"]}\n', encoding="utf-8")
        self.assertEqual(self.gate("dup", "run")[0], 1)


@unittest.skipUnless(BASH, "bash is not available")
class ShellHardStopOff(unittest.TestCase):
    def test_the_shell_cannot_lift_the_hard_stop(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            eg = root / "03_RUNTIME_GOVERNANCE" / "EXECUTION_GATE"
            eg.mkdir(parents=True)
            for f in ("hard_stop_off.sh", "hard_stop_on.sh", "hard_stop_path.conf"):
                shutil.copy(GATE_DIR / f, eg / f)
            env = dict(os.environ, VEGA_ROOT=str(root))
            subprocess.run([BASH, str(eg / "hard_stop_on.sh")], env=env, capture_output=True, timeout=30)
            flag = eg / "HARD_STOP.flag"
            self.assertTrue(flag.exists())
            r = subprocess.run([BASH, str(eg / "hard_stop_off.sh")], env=env, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(flag.exists(), "the shell script lifted the hard stop")
            self.assertIn("human", (r.stdout + r.stderr).lower())


class OneApprovalOneUseAcrossGateObjects(unittest.TestCase):
    """The burned-nonce set was loaded once per Commit object, so a second Commit sharing the DAG (with its own Verifier) accepted an approval the first had used,
    whenever no ledger mint was there to catch the duplicate (boundary_crossing=False)."""

    def second_commit(self, f):
        return Commit(humanauth.Verifier(f.pub, fx.DEV, fx.SURF), f.led, f.dag)

    def test_a_second_commit_object_refuses_an_approval_the_first_used(self):
        f = fx.build()
        other = self.second_commit(f)                          # built BEFORE the approval is used, as a long-lived second gate would be
        signed = f.sign("send_email", {"to": "bob"})
        f.commit.commit("send_email", {"to": "bob"}, signed, boundary_crossing=False)
        with self.assertRaises(CommitRefused):
            other.commit("send_email", {"to": "bob"}, signed, boundary_crossing=False)
        self.assertEqual(len([e for e in f.dag.content.entries() if e["kind"] == "NONCE_BURNED"]), 1)

    def test_the_same_holds_through_the_exit_gate(self):
        f = fx.build()
        other = self.second_commit(f)
        signed = f.sign("send_email", {"to": "bob"})
        f.gate.release("send_email", {"to": "bob"}, signed)
        with self.assertRaises(CommitRefused):
            other.commit("send_email", {"to": "bob"}, signed, boundary_crossing=False)

    def test_two_threads_with_one_approval_through_separate_commit_objects_commit_once(self):
        import threading
        f = fx.build()
        signed = f.sign("send_email", {"to": "bob"})
        commits = [f.commit, self.second_commit(f)]
        gate, out, lock = threading.Barrier(2), [], threading.Lock()

        def go(c):
            gate.wait()
            try:
                c.commit("send_email", {"to": "bob"}, signed, boundary_crossing=False)
                r = "committed"
            except CommitRefused:
                r = "refused"
            with lock:
                out.append(r)
        ts = [threading.Thread(target=go, args=(c,)) for c in commits]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        self.assertEqual(sorted(out), ["committed", "refused"], out)


class SigningCliMessages(unittest.TestCase):
    def test_a_refused_signature_input_is_reported_as_such_not_as_a_wrong_passphrase(self):
        import io
        from unittest import mock
        from vega_jacket.humanauth import human_cli
        blob, _ = __import__("vega_jacket.humanauth.human_signer", fromlist=["x"]).generate("correct horse battery")
        with tempfile.TemporaryDirectory() as d:
            key = os.path.join(d, "k.bin")
            open(key, "wb").write(blob)
            a = mock.Mock(action="send_email", lease=0, device="d", surface="s", params="{}", params_file=None, key=key, out=None)
            with mock.patch.object(human_cli, "_need_tty"), mock.patch.object(human_cli, "_STAMP", os.path.join(d, "stamp")),                  mock.patch("builtins.input", return_value="send_email"), mock.patch.object(human_cli, "_passphrase", return_value="correct horse battery"):
                with self.assertRaises(SystemExit) as cm:
                    human_cli.sign(a)
        self.assertIn("lease", str(cm.exception).lower())
        self.assertNotIn("passphrase", str(cm.exception).lower())


if __name__ == "__main__":
    unittest.main()
