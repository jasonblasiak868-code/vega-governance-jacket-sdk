"""Package face of the humanauth module. Verification side only; the signer (human_signer.py, human_cli.py)
is deliberately not re-exported: agent and gate code must have no import path to it."""
import os
import sys

from vega_jacket.humanauth.human_only import HUMAN_ONLY, check_card_capabilities, is_human_only, refuse_odd_spelling, require_human  # noqa: E402,F401
from vega_jacket.humanauth.verify import MAX_LEASE_SECONDS, HumanAuthError, Verifier, action_hash  # noqa: E402,F401
