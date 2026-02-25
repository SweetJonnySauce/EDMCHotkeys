from __future__ import annotations

import json

from edmc_hotkeys.bindings import BindingRecord, BindingsDocument, default_document
from edmc_hotkeys.registry import Action
from edmc_hotkeys.settings_state import BindingRow, SettingsState


def _action(
    action_id: str,
    *,
    plugin: str = "plugin",
    enabled: bool = True,
) -> Action:
    return Action(
        id=action_id,
        label=action_id,
        plugin=plugin,
        callback=lambda **_kwargs: None,
        enabled=enabled,
    )


def test_validation_reports_hotkey_conflict() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("a.one"), _action("a.two")])
    state.rows = [
        BindingRow(id="b1", hotkey="LCtrl+LShift+O", plugin="plugin", action_id="a.one", enabled=True),
        BindingRow(id="b2", hotkey="ctrl_l+shift_l+o", plugin="plugin", action_id="a.two", enabled=True),
    ]

    issues = state.validate()

    assert any(issue.field == "hotkey" and issue.level == "error" for issue in issues)


def test_validation_reports_unknown_action() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action")])
    state.rows = [
        BindingRow(id="b1", hotkey="LCtrl+LShift+O", plugin="plugin", action_id="unknown.action", enabled=True),
    ]

    issues = state.validate()

    assert any(issue.field == "action_id" and issue.level == "warning" for issue in issues)


def test_validation_reports_disabled_action_warning() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action", enabled=False)])
    state.rows = [
        BindingRow(id="b1", hotkey="LCtrl+LShift+O", plugin="plugin", action_id="known.action", enabled=True),
    ]

    issues = state.validate()

    assert any(issue.field == "action_id" and issue.level == "warning" for issue in issues)


def test_validation_allows_empty_rows_list() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action", enabled=True)])
    state.rows = []

    issues = state.validate()

    assert issues == []


def test_from_document_exposes_payload_text() -> None:
    document = BindingsDocument(
        version=3,
        active_profile="Default",
        profiles={
            "Default": [
                BindingRecord(
                    id="b1",
                    plugin="plugin",
                    modifiers=("ctrl_l", "shift_l"),
                    key="o",
                    action_id="known.action",
                    payload={"color": "red", "level": 2},
                    enabled=True,
                )
            ]
        },
    )
    state = SettingsState.from_document(document=document, actions=[_action("known.action", enabled=True)])

    assert len(state.rows) == 1
    assert json.loads(state.rows[0].payload_text) == {"color": "red", "level": 2}


def test_validation_reports_invalid_payload() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action")])
    state.rows = [
        BindingRow(
            id="b1",
            hotkey="LCtrl+LShift+O",
            plugin="plugin",
            action_id="known.action",
            payload_text="{oops",
            enabled=True,
        ),
    ]

    issues = state.validate()

    assert any(issue.field == "payload" and issue.level == "error" for issue in issues)


def test_to_document_preserves_non_active_profiles() -> None:
    document = BindingsDocument(
        version=3,
        active_profile="Default",
        profiles={
            "Default": [BindingRecord(id="old", plugin="plugin", modifiers=(), key="f1", action_id="a.old", enabled=True)],
            "Mining": [BindingRecord(id="m1", plugin="plugin", modifiers=(), key="f2", action_id="a.mine", enabled=True)],
        },
    )
    state = SettingsState.from_document(document=document, actions=[_action("a.new")])
    state.rows = [
        BindingRow(id="new", hotkey="LCtrl+LShift+N", plugin="plugin", action_id="a.new", enabled=True),
    ]

    updated = state.to_document()

    assert "Mining" in updated.profiles
    assert updated.profiles["Mining"][0].id == "m1"
    assert updated.profiles["Default"][0].id == "new"


def test_to_document_parses_payload_text() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action")])
    state.rows = [
        BindingRow(
            id="b1",
            hotkey="LCtrl+LShift+O",
            plugin="plugin",
            action_id="known.action",
            payload_text='{"color":"lime"}',
            enabled=True,
        ),
    ]

    updated = state.to_document()
    assert updated.profiles["Default"][0].payload == {"color": "lime"}


def test_validation_requires_plugin() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action")])
    state.rows = [
        BindingRow(id="b1", hotkey="LCtrl+LShift+O", plugin="", action_id="known.action", enabled=True),
    ]

    issues = state.validate()

    assert any(issue.field == "plugin" and issue.level == "error" for issue in issues)
