"""The permanent list of actions only a human signature can authorize, and the checks that keep cards and models
away from it. This list is code, not configuration: changing it is a code change that goes through human review."""
import unicodedata

from vega_jacket.humanauth.verify import HumanAuthError, Verifier

HUMAN_ONLY = frozenset({
    "mint_commitment",
    "change_gate_config",
    "change_key_registry",
    "raise_scope_cap",
    "disable_hard_stop",
    "restore_after_hard_stop",
    "release_public",
    "spend_funds",
    "grant_authority",
    "revoke_authority",
})


def normalize(action) -> str:
    """The comparison form of an action name: Unicode compatibility folding (so full-width letters become ordinary ones), invisible and format characters removed, case-folded, spaces and hyphens as underscores."""
    folded = unicodedata.normalize("NFKC", str(action))
    folded = "".join(c for c in folded if unicodedata.category(c) not in ("Cf", "Cc") or c in " 	")
    return folded.strip().casefold().replace("-", "_").replace(" ", "_")


def is_human_only(action) -> bool:
    """True for a HUMAN_ONLY action under any spelling (case, spaces, hyphens)."""
    return normalize(action) in HUMAN_ONLY


def refuse_odd_spelling(action) -> None:
    """A HUMAN_ONLY action must arrive spelled exactly as listed: 'Release_Public' or 'release-public' is refused, never quietly treated as an ordinary action."""
    if is_human_only(action) and action not in HUMAN_ONLY:
        raise HumanAuthError(f"{action!r} is a non-canonical spelling of a HUMAN_ONLY action")


def require_human(verifier: Verifier, action: str, params: dict, signed: dict) -> None:
    """Gate entry point for HUMAN_ONLY actions. Cards and models have no other route to these actions."""
    refuse_odd_spelling(action)
    if action not in HUMAN_ONLY:
        raise HumanAuthError(f"{action!r} is not a HUMAN_ONLY action; use the normal commitment path")
    verifier.check(action, params, signed)


def check_card_capabilities(card: dict) -> None:
    """A card may never carry a HUMAN_ONLY capability. Run at card mint time AND at gate time."""
    if not isinstance(card, dict):
        raise HumanAuthError("a card is an object")
    raw = card.get("capabilities", ())
    if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple, set, frozenset)):
        raise HumanAuthError("capabilities must be a list of strings (a bare string would be read letter by letter)")
    if any(not isinstance(c, str) for c in raw):
        raise HumanAuthError("every capability must be a string")
    bad = sorted(c for c in raw if is_human_only(c))
    if bad:
        raise HumanAuthError(f"card carries HUMAN_ONLY capability: {bad}")
    if any("*" in c for c in raw):
        raise HumanAuthError("card carries a wildcard capability")
