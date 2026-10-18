"""Verification side of human authority. Holds ONLY a public key - nothing in this module can mint a signature.

Signed message format (filed, 64/168,948):
    WCOMMIT|<device_fingerprint>|<surface_id>|<action>|<action_hash>|<nonce>|<expiry>
where action_hash is the SHA-256 of the action's exact canonical arguments.
"""
import hashlib
import json
import threading
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_LEASE_SECONDS = 15 * 60  # a commitment may live at most 15 minutes; raising this needs a human-signed config change
WILDCARDS = ("*", "any", "all", "")


class HumanAuthError(Exception):
    pass


def canonical(params: dict) -> bytes:
    try:
        return json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HumanAuthError(f"parameters are not canonical JSON: {exc}") from exc


def action_hash(params: dict) -> str:
    return hashlib.sha256(canonical(params)).hexdigest()


_BAD_CHARS = ("|", "\n", "\r", "\x00")


def message(device: str, surface: str, action: str, a_hash: str, nonce: str, expiry: int) -> bytes:
    """The signed bytes. '|' is the field separator, so no field may contain it (or a line break or NUL): otherwise two different (action, nonce, ...) tuples could
    produce the same bytes and a signature for one would verify for the other. Checked here so the signer and the verifier can never disagree."""
    for name, v in (("device", device), ("surface", surface), ("action", action), ("action_hash", a_hash), ("nonce", nonce)):
        if not isinstance(v, str) or not v or any(c in v for c in _BAD_CHARS):
            raise HumanAuthError(f"{name} must be a non-empty string without '|', line breaks or NUL")
        if any(not 32 <= ord(c) < 127 for c in v):
            raise HumanAuthError(f"{name} must be plain printable ASCII: a look-alike or invisible character could name a different action downstream than the one the human read")
    if isinstance(expiry, bool) or not isinstance(expiry, int):
        raise HumanAuthError("expiry must be an integer")
    return f"WCOMMIT|{device}|{surface}|{action}|{a_hash}|{nonce}|{expiry}".encode("utf-8")


class Verifier:
    """Gate-side verifier. Constructed from the public key only."""

    def __init__(self, public_key_bytes: bytes, device: str, surface: str, used_nonces=None, clock=time.time):
        self._pub = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        self.device, self.surface = device, surface
        self._used = set(used_nonces or ())
        self._clock = clock
        self._lock = threading.Lock()      # check, verify and burn happen as one step: two threads can never both pass with one approval

    def check(self, action: str, params: dict, signed: dict) -> None:
        """Raise HumanAuthError unless `signed` is a fresh, single-use, exact-action human signature."""
        if not isinstance(action, str) or action in WILDCARDS or "*" in action:
            raise HumanAuthError("wildcard action refused: authority is never blanket")
        if not isinstance(signed, dict):
            raise HumanAuthError("the approval must be an object")
        for k in ("nonce", "expiry", "signature"):
            if k not in signed:
                raise HumanAuthError(f"missing field: {k}")
        if not isinstance(signed["nonce"], str) or not isinstance(signed["signature"], str):
            raise HumanAuthError("nonce and signature must be strings")
        try:
            if isinstance(signed["expiry"], bool) or not isinstance(signed["expiry"], (int, str)) or (isinstance(signed["expiry"], str) and not signed["expiry"].isdigit()):
                raise ValueError
            expiry = int(signed["expiry"])
            now = int(self._clock())
        except (ValueError, TypeError, OverflowError):
            raise HumanAuthError("expiry must be a whole number of seconds")
        if expiry <= now:
            raise HumanAuthError("commitment expired")
        if expiry - now > MAX_LEASE_SECONDS:
            raise HumanAuthError("lease longer than the cap")
        with self._lock:
            if signed["nonce"] in self._used:
                raise HumanAuthError("replay: nonce already used")
            msg = message(self.device, self.surface, action, action_hash(params), signed["nonce"], expiry)
            try:
                self._pub.verify(bytes.fromhex(signed["signature"]), msg)
            except (InvalidSignature, ValueError):
                raise HumanAuthError("signature does not match this exact action")
            self._used.add(signed["nonce"])  # single use: burned only after a successful verify

    def used_nonces(self):
        return sorted(self._used)


def commitment_signature_checker(public_key_bytes: bytes):
    """A function for Ledger(commitment_check=...): True only if the commitment's own fields, with its raw nonce, were signed by the human key. Makes the ledger refuse a WCOMMIT that anyone
    holding the ledger object tried to fabricate, because only the human's private key can produce the signature."""
    pub = Ed25519PublicKey.from_public_bytes(public_key_bytes)

    def check(c: dict) -> bool:
        try:
            if hashlib.sha256(str(c["nonce"]).encode("utf-8")).hexdigest() != c["nonce_sha256"]:
                return False
            pub.verify(bytes.fromhex(c["signature"]), message(c["device"], c["surface"], c["action"], c["action_hash"], c["nonce"], int(c["expiry"])))
            return True
        except Exception:  # noqa: BLE001 - anything that does not verify is not a human commitment
            return False
    return check
