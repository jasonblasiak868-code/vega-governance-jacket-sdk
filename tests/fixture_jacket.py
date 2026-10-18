"""Shared fixture for the jacket red-team passes (not a test file)."""
import pathlib
import tempfile
import types

from vega_custody.dag.dag import Dag
from vega_custody.ledger.backend_local import LocalBackend
from vega_custody.ledger.ledger import Ledger
from vega_jacket import humanauth
from vega_jacket.commit.commit import Commit
from vega_jacket.gate.entry_gate import EntryGate
from vega_jacket.gate.exit_gate import ExitGate
from vega_jacket.humanauth import human_signer

PW, DEV, SURF = "correct horse battery", "dev-rt", "surf-rt"


def build(clock=None):
    blob, pub = human_signer.generate(PW)
    t = pathlib.Path(tempfile.mkdtemp())
    dag = Dag([t / "c.jsonl"], [t / "l.jsonl"])
    led = Ledger([LocalBackend(t / "led.jsonl")])
    kw = {"clock": clock} if clock else {}
    ver = humanauth.Verifier(pub, DEV, SURF, **kw)
    commit = Commit(ver, led, dag)
    gate = ExitGate(commit, led, ver, dag)
    return types.SimpleNamespace(blob=blob, pub=pub, tmp=t, dag=dag, led=led, ver=ver, commit=commit, gate=gate, entry=EntryGate(dag),
                                 sign=lambda action, params, lease=300: human_signer.sign(blob, PW, DEV, SURF, action, params, lease))
