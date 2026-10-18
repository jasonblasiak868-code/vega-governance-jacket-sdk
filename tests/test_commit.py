"""Selftest for commit + the two gates: exit 0 only if every check passes.
Signing here uses the human-side signer library directly (a test stands in for the human at a console)."""
import os
import pathlib
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from vega_jacket.humanauth import human_signer  # noqa: E402  (human side; only tests import it)
from vega_jacket import humanauth  # noqa: E402
from vega_custody.capsule import capsule as cap  # noqa: E402
from vega_jacket.commit.commit import Commit, CommitRefused  # noqa: E402
from vega_custody.dag.dag import Dag  # noqa: E402
from vega_jacket.gate.entry_gate import EntryGate, Refused  # noqa: E402
from vega_jacket.gate.exit_gate import Denied, ExitGate  # noqa: E402
from vega_custody.ledger.backend_local import LocalBackend  # noqa: E402
from vega_custody.ledger.ledger import Ledger  # noqa: E402

fails, N = [], 0
PW, DEV, SURF = "correct horse battery", "dev-t", "surf-t"
P = {"to": "ledger", "amount": 1}


def check(name, cond):
    global N
    N += 1
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    return False


blob, pub = human_signer.generate(PW)


def rig(root):
    d = Dag([root / "dag" / "c.jsonl"], [root / "dag" / "l.jsonl"])
    led = Ledger([LocalBackend(root / "led" / "l.jsonl")])
    v = humanauth.Verifier(pub, DEV, SURF)
    c = Commit(v, led, d)
    return d, led, v, c, ExitGate(c, led, v, d)


def sign(action, params=P, lease=300):
    return human_signer.sign(blob, PW, DEV, SURF, action, params, lease)


root = pathlib.Path(tempfile.mkdtemp())
d, led, v, c, gate = rig(root)

# --- exit gate, genuine human approval
s = sign("spend_funds")
out = gate.release("spend_funds", P, s, route="human")
check("genuine human approval released and minted", out["receipt"]["leaf"] and led.verify(out["commitment"]))
check("release recorded in DAG", any(e["kind"] == "EXIT_RELEASED" for e in d.content.entries()))
check("ledger holds hashes and metadata, not params",
      b"amount" not in (root / "led" / "l.jsonl").read_bytes())

# --- attacks
check("replay refused", raises(Denied, lambda: gate.release("spend_funds", P, s, route="human")))
check("HUMAN_ONLY on card route refused", raises(Denied, lambda: gate.release("spend_funds", P, sign("spend_funds"), route="card")))
check("HUMAN_ONLY on model route refused", raises(Denied, lambda: gate.release("grant_authority", P, sign("grant_authority"), route="model")))
check("changed params refused", raises(Denied, lambda: gate.release("spend_funds", {**P, "amount": 9999}, sign("spend_funds"), route="human")))
check("unsigned approval refused", raises(Denied, lambda: gate.release("spend_funds", P, {"nonce": "n", "expiry": 1, "signature": "00"})))
check("every denial recorded", sum(e["kind"] == "EXIT_DENIED" for e in d.content.entries()) >= 4)

# --- durable replay: brand-new objects over the same files, only the DAG remembers the nonce
d2 = Dag([root / "dag" / "c.jsonl"], [root / "dag" / "l.jsonl"])
led2 = Ledger([LocalBackend(root / "led" / "l.jsonl")])
v2 = humanauth.Verifier(pub, DEV, SURF)  # fresh verifier: its in-memory nonce set is empty
gate2 = ExitGate(Commit(v2, led2, d2), led2, v2, d2)
check("replay refused after restart (nonce burn is durable)",
      raises(Denied, lambda: gate2.release("spend_funds", P, s, route="human")))

# the restart wrote to the files; continue with a clean view of them (single writer per ledger)
d, led, v, c, gate = rig(root)

# --- non-HUMAN_ONLY action still needs a commitment, and mints
out2 = gate.release("write_file", {"path": "x"}, sign("write_file", {"path": "x"}), route="model")
check("ordinary action on model route needs and gets a commitment", led.verify(out2["commitment"]))

# --- commit(): internal commitment (no boundary crossing) mints nothing but burns the nonce
out3 = c.commit("internal_step", {"k": 1}, sign("internal_step", {"k": 1}), route="model", boundary_crossing=False)
check("internal commit not minted to ledger", out3["receipt"] is None and out3["commitment"]["nonce_sha256"])
check("commit() refuses HUMAN_ONLY on card route",
      raises(CommitRefused, lambda: c.commit("release_public", P, sign("release_public"), route="card")))

# --- entry gate
eg = EntryGate(d)
good = cap.make("hello", {"source": "user"})
check("verified capsule admitted", eg.admit(good) is good)
bad = dict(good)
bad["data_b64"] = cap.make("evil")["data_b64"]
check("tampered capsule refused", raises(Refused, lambda: eg.admit(bad)))
card = cap.make("x", {"card": {"capabilities": ["propose_commitment", "spend_funds"]}})
check("capsule whose card claims HUMAN_ONLY refused", raises(Refused, lambda: eg.admit(card)))

check("DAG intact after all of it", d.verify()[0])
print(f"{N - len(fails)}/{N} passed" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)
