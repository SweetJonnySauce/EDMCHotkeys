from __future__ import annotations

from edmc_hotkeys.backends.base import BackendCapabilities
from edmc_hotkeys.bindings import BindingRecord, BindingsDocument
from edmc_hotkeys.hotkey import canonical_hotkey_text, parse_hotkey, pretty_hotkey_text
from edmc_hotkeys.settings_ui import hotkey_from_parts
import load as plugin_load


class _NoSideSpecificPlugin:
    def backend_capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_side_specific_modifiers=False)

    def backend_name(self) -> str:
        return "linux-wayland-keyd"


def test_hotkey_parser_accepts_canonical_and_pretty_side_specific_forms() -> None:
    pretty = parse_hotkey("RCtrl+LShift+A")
    canonical = parse_hotkey("ctrl_r+shift_l+a")

    assert pretty is not None
    assert canonical is not None
    assert pretty.modifiers == ("ctrl_r", "shift_l")
    assert pretty.key == "a"
    assert canonical == pretty
    assert canonical_hotkey_text(modifiers=pretty.modifiers, key=pretty.key) == "ctrl_r+shift_l+a"
    assert pretty_hotkey_text(modifiers=pretty.modifiers, key=pretty.key) == "RCtrl+LShift+A"


def test_hotkey_parser_accepts_generic_modifier_tokens() -> None:
    parsed = parse_hotkey("Ctrl+Shift+A")
    assert parsed is not None
    assert parsed.modifiers == ("ctrl", "shift")
    assert parsed.key == "a"

    alt_parsed = parse_hotkey("Alt+1")
    assert alt_parsed is not None
    assert alt_parsed.modifiers == ("alt",)
    assert alt_parsed.key == "1"


def test_hotkey_parser_rejects_mixed_generic_and_side_specific_modifiers() -> None:
    assert parse_hotkey("Ctrl+LCtrl+A") is None
    assert parse_hotkey("Shift+RShift+F2") is None


def test_settings_capture_uses_active_left_right_modifier_state() -> None:
    captured = hotkey_from_parts(
        state=0x0000,
        keysym="a",
        char="a",
        active_modifiers=("ctrl_r", "shift_l"),
    )

    assert captured == "RCtrl+LShift+A"


def test_auto_disable_marks_side_specific_bindings_disabled_when_backend_lacks_support() -> None:
    document = BindingsDocument(
        version=3,
        active_profile="Default",
        profiles={
            "Default": [
                BindingRecord(
                    id="b-side",
                    plugin="PluginA",
                    modifiers=("ctrl_l",),
                    key="a",
                    action_id="test.action",
                    enabled=True,
                ),
                BindingRecord(
                    id="b-generic",
                    plugin="PluginA",
                    modifiers=("ctrl",),
                    key="b",
                    action_id="test.action",
                    enabled=True,
                ),
                BindingRecord(
                    id="b-plain",
                    plugin="PluginA",
                    modifiers=(),
                    key="f1",
                    action_id="test.action",
                    enabled=True,
                ),
            ]
        },
    )

    updated, reasons = plugin_load._auto_disable_unsupported_bindings(document, _NoSideSpecificPlugin())

    assert updated.profiles["Default"][0].enabled is False
    assert updated.profiles["Default"][1].enabled is True
    assert updated.profiles["Default"][2].enabled is True
    assert reasons and "Auto-disabled binding 'b-side'" in reasons[0]
    assert len(reasons) == 1
    assert all("b-generic" not in reason for reason in reasons)


def test_binding_requires_side_specific_capabilities_helper() -> None:
    side_specific = BindingRecord(
        id="b-side",
        plugin="PluginA",
        modifiers=("ctrl_l",),
        key="a",
        action_id="test.action",
        enabled=True,
    )
    no_modifier = BindingRecord(
        id="b-plain",
        plugin="PluginA",
        modifiers=(),
        key="f1",
        action_id="test.action",
        enabled=True,
    )
    generic_modifier = BindingRecord(
        id="b-generic",
        plugin="PluginA",
        modifiers=("ctrl",),
        key="g",
        action_id="test.action",
        enabled=True,
    )

    assert plugin_load._binding_requires_side_specific_capabilities(side_specific) is True
    assert plugin_load._binding_requires_side_specific_capabilities(no_modifier) is False
    assert plugin_load._binding_requires_side_specific_capabilities(generic_modifier) is False
