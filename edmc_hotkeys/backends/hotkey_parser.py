"""Shared hotkey string parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


_MODIFIER_ALIASES = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "win": "super",
    "super": "super",
    "meta": "super",
}


@dataclass(frozen=True)
class ParsedHotkey:
    modifiers: frozenset[str]
    key: str


def parse_hotkey(hotkey: str) -> Optional[ParsedHotkey]:
    """Parse `Ctrl+Shift+O` style strings into normalized components."""
    if not hotkey:
        return None
    tokens = [part.strip() for part in hotkey.split("+") if part.strip()]
    if not tokens:
        return None

    modifiers: set[str] = set()
    key: Optional[str] = None
    for token in tokens:
        normalized = token.lower()
        modifier = _MODIFIER_ALIASES.get(normalized)
        if modifier is not None:
            modifiers.add(modifier)
            continue
        if key is not None:
            return None
        key = token

    if key is None:
        return None
    return ParsedHotkey(modifiers=frozenset(modifiers), key=key)

