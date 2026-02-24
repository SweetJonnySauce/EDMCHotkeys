from __future__ import annotations

from edmc_hotkeys.bindings import BindingRecord, BindingsDocument, default_document
from edmc_hotkeys.registry import Action
from edmc_hotkeys.settings_state import BindingRow, SettingsState


def _action(action_id: str, *, plugin: str = "plugin", enabled: bool = True) -> Action:
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
        BindingRow(id="b1", hotkey="Ctrl+Shift+O", plugin="plugin", action_id="a.one", enabled=True),
        BindingRow(id="b2", hotkey="ctrl+shift+o", plugin="plugin", action_id="a.two", enabled=True),
    ]

    issues = state.validate()

    assert any(issue.field == "hotkey" and issue.level == "error" for issue in issues)


def test_validation_reports_unknown_action() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action")])
    state.rows = [
        BindingRow(id="b1", hotkey="Ctrl+Shift+O", plugin="plugin", action_id="unknown.action", enabled=True),
    ]

    issues = state.validate()

    assert any(issue.field == "action_id" and issue.level == "error" for issue in issues)


def test_validation_reports_disabled_action_warning() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action", enabled=False)])
    state.rows = [
        BindingRow(id="b1", hotkey="Ctrl+Shift+O", plugin="plugin", action_id="known.action", enabled=True),
    ]

    issues = state.validate()

    assert any(issue.field == "action_id" and issue.level == "warning" for issue in issues)


def test_validation_allows_empty_rows_list() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action", enabled=True)])
    state.rows = []

    issues = state.validate()

    assert issues == []


def test_to_document_preserves_non_active_profiles() -> None:
    document = BindingsDocument(
        version=1,
        active_profile="Default",
        profiles={
            "Default": [BindingRecord(id="old", hotkey="F1", action_id="a.old", enabled=True)],
            "Mining": [BindingRecord(id="m1", hotkey="F2", action_id="a.mine", enabled=True)],
        },
    )
    state = SettingsState.from_document(document=document, actions=[_action("a.new")])
    state.rows = [
        BindingRow(id="new", hotkey="Ctrl+Shift+N", plugin="plugin", action_id="a.new", enabled=True),
    ]

    updated = state.to_document()

    assert "Mining" in updated.profiles
    assert updated.profiles["Mining"][0].id == "m1"
    assert updated.profiles["Default"][0].id == "new"
