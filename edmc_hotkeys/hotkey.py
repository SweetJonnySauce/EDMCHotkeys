"""Canonical and display helpers for hotkey tokens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


CANONICAL_MODIFIER_ORDER = (
    "ctrl_l",
    "ctrl_r",
    "alt_l",
    "alt_r",
    "shift_l",
    "shift_r",
    "win_l",
    "win_r",
)
_CANONICAL_MODIFIER_SET = set(CANONICAL_MODIFIER_ORDER)

_PRETTY_BY_CANONICAL = {
    "ctrl_l": "LCtrl",
    "ctrl_r": "RCtrl",
    "alt_l": "LAlt",
    "alt_r": "RAlt",
    "shift_l": "LShift",
    "shift_r": "RShift",
    "win_l": "LWin",
    "win_r": "RWin",
}

_MODIFIER_ALIASES = {
    "lctrl": "ctrl_l",
    "ctrll": "ctrl_l",
    "ctrl_l": "ctrl_l",
    "controll": "ctrl_l",
    "control_l": "ctrl_l",
    "rctrl": "ctrl_r",
    "ctrlr": "ctrl_r",
    "ctrl_r": "ctrl_r",
    "controlr": "ctrl_r",
    "control_r": "ctrl_r",
    "lalt": "alt_l",
    "altl": "alt_l",
    "alt_l": "alt_l",
    "ralt": "alt_r",
    "altr": "alt_r",
    "alt_r": "alt_r",
    "lshift": "shift_l",
    "shiftl": "shift_l",
    "shift_l": "shift_l",
    "rshift": "shift_r",
    "shiftr": "shift_r",
    "shift_r": "shift_r",
    "lwin": "win_l",
    "winl": "win_l",
    "win_l": "win_l",
    "superl": "win_l",
    "super_l": "win_l",
    "metal": "win_l",
    "meta_l": "win_l",
    "rwin": "win_r",
    "winr": "win_r",
    "win_r": "win_r",
    "superr": "win_r",
    "super_r": "win_r",
    "metar": "win_r",
    "meta_r": "win_r",
}

_GENERIC_MODIFIER_TOKENS = {
    "ctrl",
    "control",
    "alt",
    "shift",
    "win",
    "super",
    "meta",
}


@dataclass(frozen=True)
class ParsedHotkey:
    modifiers: tuple[str, ...]
    key: str


def canonicalize_modifiers(modifiers: Iterable[str]) -> Optional[tuple[str, ...]]:
    mapped: set[str] = set()
    for token in modifiers:
        normalized = _normalize_modifier_token(token)
        if normalized is None:
            return None
        mapped.add(normalized)
    return tuple(token for token in CANONICAL_MODIFIER_ORDER if token in mapped)


def normalize_key_token(key: str) -> Optional[str]:
    token = key.strip()
    if not token:
        return None
    if len(token) == 1 and token.isalnum():
        return token.lower()

    upper = token.upper()
    if upper.startswith("F") and upper[1:].isdigit():
        number = int(upper[1:])
        if 1 <= number <= 24:
            return f"f{number}"

    specials = {
        "SPACE": "space",
        "TAB": "tab",
        "ENTER": "enter",
        "RETURN": "enter",
        "ESC": "esc",
        "ESCAPE": "esc",
    }
    return specials.get(upper)


def parse_hotkey(hotkey: str) -> Optional[ParsedHotkey]:
    if not hotkey:
        return None
    parts = [part.strip() for part in hotkey.split("+")]
    if not parts or any(not part for part in parts):
        return None

    modifier_tokens: list[str] = []
    key_token: Optional[str] = None
    for part in parts:
        modifier = _normalize_modifier_token(part)
        if modifier is not None:
            modifier_tokens.append(modifier)
            continue
        if _is_generic_modifier_token(part):
            return None
        if key_token is not None:
            return None
        key_token = normalize_key_token(part)
        if key_token is None:
            return None

    if key_token is None:
        return None

    ordered = canonicalize_modifiers(modifier_tokens)
    if ordered is None:
        return None
    return ParsedHotkey(modifiers=ordered, key=key_token)


def canonical_hotkey_text(*, modifiers: Iterable[str], key: str) -> Optional[str]:
    ordered = canonicalize_modifiers(modifiers)
    normalized_key = normalize_key_token(key)
    if ordered is None or normalized_key is None:
        return None
    if ordered:
        return "+".join([*ordered, normalized_key])
    return normalized_key


def pretty_hotkey_text(*, modifiers: Iterable[str], key: str) -> Optional[str]:
    ordered = canonicalize_modifiers(modifiers)
    normalized_key = normalize_key_token(key)
    if ordered is None or normalized_key is None:
        return None

    pretty_tokens = [_PRETTY_BY_CANONICAL[token] for token in ordered]
    pretty_key = _pretty_key(normalized_key)
    if pretty_tokens:
        return "+".join([*pretty_tokens, pretty_key])
    return pretty_key


def pretty_hotkey_from_text(hotkey: str) -> Optional[str]:
    parsed = parse_hotkey(hotkey)
    if parsed is None:
        return None
    return pretty_hotkey_text(modifiers=parsed.modifiers, key=parsed.key)


def has_side_specific_modifiers(hotkey: str) -> bool:
    parsed = parse_hotkey(hotkey)
    if parsed is None:
        return False
    return bool(parsed.modifiers)


def _normalize_modifier_token(token: str) -> Optional[str]:
    normalized = token.strip().lower().replace(" ", "")
    if normalized in _CANONICAL_MODIFIER_SET:
        return normalized
    return _MODIFIER_ALIASES.get(normalized)


def _is_generic_modifier_token(token: str) -> bool:
    return token.strip().lower() in _GENERIC_MODIFIER_TOKENS


def _pretty_key(key: str) -> str:
    if len(key) == 1 and key.isalpha():
        return key.upper()
    if len(key) == 1 and key.isdigit():
        return key
    if key.startswith("f") and key[1:].isdigit():
        return f"F{key[1:]}"

    special = {
        "space": "Space",
        "tab": "Tab",
        "enter": "Enter",
        "esc": "Esc",
    }
    return special.get(key, key)
