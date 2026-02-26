"""Shared hotkey string parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..hotkey import parse_hotkey as parse_canonical_hotkey


@dataclass(frozen=True)
class ParsedHotkey:
    modifiers: tuple[str, ...]
    key: str


def parse_hotkey(hotkey: str) -> Optional[ParsedHotkey]:
    """Parse canonical/pretty hotkeys into normalized components."""
    parsed = parse_canonical_hotkey(hotkey)
    if parsed is None:
        return None
    return ParsedHotkey(modifiers=parsed.modifiers, key=parsed.key)
