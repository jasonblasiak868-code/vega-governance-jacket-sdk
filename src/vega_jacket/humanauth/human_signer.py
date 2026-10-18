"""HUMAN-SIDE ONLY. Run this in a console the agent cannot drive. Never import it from agent or gate code.

The private key is stored encrypted under a passphrase (scrypt + AES-256-GCM). The file alone is useless; the
passphrase is typed per signing session and never written to disk. The gate only ever gets the public key."""
import getpass
import hashlib
import os
import secrets
import sys
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from vega_jacket.humanauth.verify import MAX_LEASE_SECONDS, HumanAuthError, action_hash, message  # noqa: E402


def _kdf(passphrase: str, salt: bytes) -> bytes:
    return hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=2 ** 15, r=8, p=1, dklen=32, maxmem=2 ** 28)


def generate(passphrase: str):
    """Returns (encrypted_private_blob, public_key_bytes)."""
    sk = Ed25519PrivateKey.generate()
    raw = sk.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    blob = salt + nonce + AESGCM(_kdf(passphrase, salt)).encrypt(nonce, raw, b"vega-human-key-v1")
    pub = sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return blob, pub


def _load(blob: bytes, passphrase: str) -> Ed25519PrivateKey:
    salt, nonce, ct = blob[:16], blob[16:28], blob[28:]
    raw = AESGCM(_kdf(passphrase, salt)).decrypt(nonce, ct, b"vega-human-key-v1")  # wrong passphrase -> InvalidTag
    return Ed25519PrivateKey.from_private_bytes(raw)


def sign(blob: bytes, passphrase: str, device: str, surface: str, action: str, params: dict, lease_seconds: int = 300) -> dict:
    if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int) or not 0 < lease_seconds <= MAX_LEASE_SECONDS:
        raise HumanAuthError(f"lease must be a whole number of seconds between 1 and {MAX_LEASE_SECONDS}")
    sk = _load(blob, passphrase)
    nonce = secrets.token_hex(16)
    expiry = int(time.time()) + int(lease_seconds)
    sig = sk.sign(message(device, surface, action, action_hash(params), nonce, expiry))
    return {"nonce": nonce, "expiry": expiry, "signature": sig.hex()}


if __name__ == "__main__":
    print("Run keygen/sign from your own script in a separate console; see test_humanauth.py for the call pattern.")
    _ = getpass  # interactive prompts are wired by the owner's launcher, not here
