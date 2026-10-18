"""Red-team: every attack below must be REFUSED. run_all() returns [(name, refused: bool, detail)]."""
import os
import sys
import time

from cryptography.exceptions import InvalidTag  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from vega_jacket.humanauth import human_signer  # noqa: E402
from vega_jacket.humanauth.human_only import HUMAN_ONLY, check_card_capabilities, require_human  # noqa: E402
from vega_jacket.humanauth.verify import HumanAuthError, Verifier, action_hash, message  # noqa: E402

DEV, SURF = "dev-test", "surface-test"
PARAMS = {"target": "ledger/mint", "commitment": "abc123"}


def _fresh():
    blob, pub = human_signer.generate("correct horse battery")
    return blob, pub, Verifier(pub, DEV, SURF)


def _refused(fn):
    try:
        fn()
    except (HumanAuthError, InvalidTag) as e:
        return True, f"{type(e).__name__}: {e}"
    return False, "ACCEPTED - this is a bypass"


def raw_sign(blob, passphrase, device, surface, action, params, lease_seconds):
    """Simulates a MODIFIED signer that ignores the lease cap (the honest signer now refuses). Used only to prove the verifier still refuses such approvals."""
    import secrets, time
    sk = human_signer._load(blob, passphrase)
    nonce, expiry = secrets.token_hex(16), int(time.time()) + int(lease_seconds)
    return {"nonce": nonce, "expiry": expiry, "signature": sk.sign(message(device, surface, action, action_hash(params), nonce, expiry)).hex()}


def run_all():
    out = []
    blob, pub, v = _fresh()

    # 0. control: a genuine human signature is accepted exactly once
    good = human_signer.sign(blob, "correct horse battery", DEV, SURF, "mint_commitment", PARAMS)
    try:
        require_human(v, "mint_commitment", PARAMS, good)
        ok0 = True
    except HumanAuthError:
        ok0 = False
    out.append(("control: genuine human signature accepted", ok0, "single use"))

    # 1. replay of the same signature
    out.append(("replay same nonce", *_refused(lambda: require_human(v, "mint_commitment", PARAMS, good))))

    # 2. forged signature by an attacker key
    atk = Ed25519PrivateKey.generate()
    nonce, exp = "f" * 32, int(time.time()) + 60
    forged = {"nonce": nonce, "expiry": exp,
              "signature": atk.sign(message(DEV, SURF, "mint_commitment", action_hash(PARAMS), nonce, exp)).hex()}
    out.append(("forged by attacker key", *_refused(lambda: require_human(v, "mint_commitment", PARAMS, forged))))

    # 3. signature reused for different parameters
    s = human_signer.sign(blob, "correct horse battery", DEV, SURF, "mint_commitment", PARAMS)
    out.append(("params changed after signing", *_refused(
        lambda: require_human(v, "mint_commitment", {**PARAMS, "commitment": "EVIL"}, s))))

    # 4. signature reused for a different action
    s2 = human_signer.sign(blob, "correct horse battery", DEV, SURF, "mint_commitment", PARAMS)
    out.append(("action swapped after signing", *_refused(lambda: require_human(v, "spend_funds", PARAMS, s2))))

    # 5. expired
    old = raw_sign(blob, "correct horse battery", DEV, SURF, "spend_funds", PARAMS, -5)
    out.append(("expired lease", *_refused(lambda: require_human(v, "spend_funds", PARAMS, old))))

    # 6. lease above the cap (blanket-ish authority)
    long = raw_sign(blob, "correct horse battery", DEV, SURF, "spend_funds", PARAMS, 86400)
    out.append(("lease above cap", *_refused(lambda: require_human(v, "spend_funds", PARAMS, long))))

    # 7. wildcard action
    out.append(("wildcard action", *_refused(lambda: v.check("*", PARAMS, good))))

    # 8. non-HUMAN_ONLY action smuggled through the human-only door
    out.append(("action not on HUMAN_ONLY list", *_refused(
        lambda: require_human(v, "read_file", PARAMS, human_signer.sign(blob, "correct horse battery", DEV, SURF, "read_file", PARAMS)))))

    # 9. a card claiming a HUMAN_ONLY capability
    out.append(("card claims HUMAN_ONLY capability", *_refused(
        lambda: check_card_capabilities({"capabilities": ["propose_commitment", "mint_commitment"]}))))

    # 10. the encrypted key file without the passphrase cannot sign
    out.append(("key file without passphrase", *_refused(
        lambda: human_signer.sign(blob, "guess", DEV, SURF, "mint_commitment", PARAMS))))

    # 11. nothing on the verifier side can sign: no private material reachable from the gate object
    leak = any(isinstance(getattr(v, a), Ed25519PrivateKey) for a in dir(v) if not a.startswith("__"))
    out.append(("gate object holds no private key", not leak, "public key only"))
    assert HUMAN_ONLY, "HUMAN_ONLY list must not be empty"
    return out


if __name__ == "__main__":
    for name, ok, detail in run_all():
        print(("PASS " if ok else "FAIL ") + name + " | " + detail)
