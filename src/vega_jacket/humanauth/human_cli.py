"""HUMAN-SIDE ONLY launcher. Run in your own console: python human_cli.py keygen|sign ...

Refuses to run without an interactive terminal, so a piped or scripted caller (an agent) gets nothing.
The passphrase is read with getpass, never from argv, env or a file. Every signing shows the exact action and
parameters first, requires typing the action name back, and enforces a cooldown between signatures."""
import argparse
import getpass
import json
import os
import sys
import time

from vega_jacket.humanauth import human_signer  # noqa: E402
from vega_jacket.humanauth.human_only import HUMAN_ONLY  # noqa: E402
from vega_jacket.humanauth.verify import MAX_LEASE_SECONDS, action_hash  # noqa: E402

COOLDOWN_SECONDS = 5
_STAMP = os.path.join(os.path.expanduser("~"), ".vega_human_last_sign")   # per user, not inside the package folder


def _need_tty():
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        sys.exit("REFUSED: needs an interactive terminal. Run this yourself in your own console.")


def _passphrase(confirm=False):
    p = getpass.getpass("Passphrase: ")
    if confirm and getpass.getpass("Again: ") != p:
        sys.exit("Passphrases differ. Nothing written.")
    if len(p) < 12:
        sys.exit("Passphrase under 12 characters. Use a longer one.")
    return p


def keygen(a):
    _need_tty()
    if os.path.exists(a.out):
        sys.exit(f"REFUSED: {a.out} exists. Will not overwrite a key file.")
    blob, pub = human_signer.generate(_passphrase(confirm=True))
    fd = os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)    # owner-only on POSIX; never overwrites
    with os.fdopen(fd, "wb") as f:
        f.write(blob)
    print(f"Encrypted key written: {a.out}")
    print("Public key (give this to the gate; it can only verify):")
    print(pub.hex())


def sign(a):
    _need_tty()
    if a.action == "*" or not a.action:
        sys.exit("REFUSED: wildcard or empty action.")
    if a.lease > MAX_LEASE_SECONDS:
        sys.exit(f"REFUSED: lease over cap of {MAX_LEASE_SECONDS}s.")
    try:
        raw = open(_STAMP).read()
    except OSError:
        raw = None                               # no stamp yet: first approval
    if raw is not None:
        try:
            last = float(raw)
        except ValueError:
            sys.exit("REFUSED: the cooldown stamp is unreadable; delete it yourself if you are sure.")
        if time.time() - last < COOLDOWN_SECONDS:
            sys.exit(f"REFUSED: cooldown, wait {COOLDOWN_SECONDS}s between approvals.")
    if a.params_file:
        with open(a.params_file, encoding="utf-8") as f:
            params = json.load(f)
    else:
        params = json.loads(a.params)
    if not isinstance(params, dict):
        sys.exit("REFUSED: parameters must be a JSON object.")
    print("\nYou are about to approve exactly this:")
    print(f"  device  : {a.device}")
    print(f"  surface : {a.surface}")
    print(f"  action  : {a.action}" + ("   [HUMAN_ONLY]" if a.action in HUMAN_ONLY else ""))
    print(f"  params  : {json.dumps(params, indent=2, sort_keys=True)}")
    print(f"  hash    : {action_hash(params)}")
    print(f"  valid   : {a.lease}s, single use\n")
    if input(f"Type the action name '{a.action}' to continue: ").strip() != a.action:
        sys.exit("Not approved.")
    with open(a.key, "rb") as f:
        blob = f.read()
    try:
        approval = human_signer.sign(blob, _passphrase(), a.device, a.surface, a.action, params, a.lease)
    except Exception:
        sys.exit("Wrong passphrase or unreadable key. Nothing signed.")
    try:
        with open(_STAMP, "w") as f:
            f.write(str(time.time()))
    except OSError:
        print("note: could not write the cooldown stamp; the approval below is still valid")
    out = json.dumps(approval)
    if a.out:
        with open(a.out, "w") as f:
            f.write(out)
        print(f"Approval written: {a.out}")
    else:
        print(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen")
    k.add_argument("--out", required=True)
    k.set_defaults(fn=keygen)
    s = sub.add_parser("sign")
    s.add_argument("--key", required=True)
    s.add_argument("--device", required=True)
    s.add_argument("--surface", required=True)
    s.add_argument("--action", required=True)
    s.add_argument("--params", default="{}", help="JSON object (quoting is awkward in PowerShell; prefer --params-file)")
    s.add_argument("--params-file", help="path to a JSON file holding the parameters")
    s.add_argument("--lease", type=int, default=300)
    s.add_argument("--out")
    s.set_defaults(fn=sign)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
