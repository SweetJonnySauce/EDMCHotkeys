from __future__ import annotations

from types import SimpleNamespace

from edmc_hotkeys.settings_ui import hotkey_from_event, hotkey_from_parts


def test_hotkey_from_parts_captures_modifier_combo() -> None:
    result = hotkey_from_parts(state=0x0005, keysym="x", char="x")
    assert result == "LCtrl+LShift+X"


def test_hotkey_from_parts_captures_ctrl_letter_when_char_is_control_code() -> None:
    result = hotkey_from_parts(state=0x0004, keysym="a", char="\x01")
    assert result == "LCtrl+A"


def test_hotkey_from_parts_captures_alt_shift_number() -> None:
    result = hotkey_from_parts(state=0x0009, keysym="exclam", char="!")
    assert result == "LAlt+LShift+1"


def test_hotkey_from_parts_captures_ctrl_shift_number() -> None:
    result = hotkey_from_parts(state=0x0005, keysym="exclam", char="!")
    assert result == "LCtrl+LShift+1"


def test_hotkey_from_parts_captures_function_key() -> None:
    result = hotkey_from_parts(state=0x0004, keysym="F10", char="")
    assert result == "LCtrl+F10"


def test_hotkey_from_parts_ignores_modifier_only_keypress() -> None:
    result = hotkey_from_parts(state=0x0004, keysym="Control_L", char="")
    assert result is None


def test_hotkey_from_event_captures_special_key() -> None:
    event = SimpleNamespace(state=0x0000, keysym="Escape", char="")
    result = hotkey_from_event(event)
    assert result == "Esc"


def test_hotkey_from_parts_returns_none_for_unsupported_key() -> None:
    result = hotkey_from_parts(state=0x0000, keysym="BracketLeft", char="[")
    assert result is None
