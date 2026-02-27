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
    cardinality: str = "single",
) -> Action:
    return Action(
        id=action_id,
        label=action_id,
        plugin=plugin,
        callback=lambda **_kwargs: None,
        enabled=enabled,
        cardinality=cardinality,
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


def test_validation_reports_hotkey_conflict_for_generic_modifiers() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("a.one"), _action("a.two")])
    state.rows = [
        BindingRow(id="b1", hotkey="Ctrl+Shift+O", plugin="plugin", action_id="a.one", enabled=True),
        BindingRow(id="b2", hotkey="ctrl+shift+o", plugin="plugin", action_id="a.two", enabled=True),
    ]

    issues = state.validate()

    assert any(issue.field == "hotkey" and issue.level == "error" for issue in issues)
    assert any("Hotkey conflicts with 'b1'" in issue.message for issue in issues)


def test_validation_allows_generic_modifier_hotkey_rows() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action", enabled=True)])
    state.rows = [
        BindingRow(id="b1", hotkey="Ctrl+Alt+M", plugin="plugin", action_id="known.action", enabled=True),
    ]

    issues = state.validate()

    assert issues == []


def test_validation_rejects_mixed_generic_and_side_specific_family_modifiers() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action", enabled=True)])
    state.rows = [
        BindingRow(id="b1", hotkey="Ctrl+LCtrl+O", plugin="plugin", action_id="known.action", enabled=True),
    ]

    issues = state.validate()

    assert any(issue.field == "hotkey" and issue.level == "error" for issue in issues)
    assert any("Do not mix generic and side-specific modifiers in the same family." in issue.message for issue in issues)


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


def test_from_document_exposes_generic_modifier_hotkeys_as_pretty_text() -> None:
    document = BindingsDocument(
        version=3,
        active_profile="Default",
        profiles={
            "Default": [
                BindingRecord(
                    id="b1",
                    plugin="plugin",
                    modifiers=("ctrl", "shift"),
                    key="o",
                    action_id="known.action",
                    enabled=True,
                )
            ]
        },
    )
    state = SettingsState.from_document(document=document, actions=[_action("known.action", enabled=True)])

    assert len(state.rows) == 1
    assert state.rows[0].hotkey == "Ctrl+Shift+O"


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


def test_to_document_round_trip_preserves_generic_modifiers() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action")])
    state.rows = [
        BindingRow(
            id="b1",
            hotkey="Ctrl+Alt+O",
            plugin="plugin",
            action_id="known.action",
            enabled=True,
        ),
    ]

    updated = state.to_document()
    binding = updated.profiles["Default"][0]
    assert binding.modifiers == ("ctrl", "alt")
    assert binding.key == "o"


def test_validation_requires_plugin() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action")])
    state.rows = [
        BindingRow(id="b1", hotkey="LCtrl+LShift+O", plugin="", action_id="known.action", enabled=True),
    ]

    issues = state.validate()

    assert any(issue.field == "plugin" and issue.level == "error" for issue in issues)


def test_from_document_sets_action_option_cardinality_default_single() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("known.action")])

    assert state.action_options[0].cardinality == "single"


def test_from_document_sets_action_option_cardinality_multi() -> None:
    document = default_document()
    state = SettingsState.from_document(
        document=document,
        actions=[_action("known.action", cardinality="multi")],
    )

    assert state.action_options[0].cardinality == "multi"


def test_from_document_normalizes_invalid_action_cardinality_to_single() -> None:
    document = default_document()
    state = SettingsState.from_document(
        document=document,
        actions=[_action("known.action", cardinality="invalid-cardinality")],
    )

    assert state.action_options[0].cardinality == "single"


def test_from_document_normalizes_mixed_case_action_cardinality_to_multi() -> None:
    document = default_document()
    state = SettingsState.from_document(
        document=document,
        actions=[_action("known.action", cardinality="MuLtI")],
    )

    assert state.action_options[0].cardinality == "multi"


def test_validation_warns_for_duplicate_enabled_single_action_usage() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("single.action", cardinality="single")])
    state.rows = [
        BindingRow(id="b1", hotkey="Ctrl+Alt+A", plugin="plugin", action_id="single.action", enabled=True),
        BindingRow(id="b2", hotkey="Ctrl+Alt+B", plugin="plugin", action_id="single.action", enabled=True),
    ]

    issues = state.validate()

    assert any(
        issue.field == "action_id"
        and issue.level == "warning"
        and "single-use" in issue.message
        for issue in issues
    )


def test_validation_ignores_disabled_rows_for_single_action_cardinality_warning() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("single.action", cardinality="single")])
    state.rows = [
        BindingRow(id="b1", hotkey="Ctrl+Alt+A", plugin="plugin", action_id="single.action", enabled=False),
        BindingRow(id="b2", hotkey="Ctrl+Alt+B", plugin="plugin", action_id="single.action", enabled=True),
    ]

    issues = state.validate()

    assert not any(
        issue.field == "action_id"
        and issue.level == "warning"
        and "single-use" in issue.message
        for issue in issues
    )


def test_validation_warns_for_duplicate_enabled_multi_action_payload() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("multi.action", cardinality="multi")])
    state.rows = [
        BindingRow(
            id="b1",
            hotkey="Ctrl+Alt+A",
            plugin="plugin",
            action_id="multi.action",
            payload_text='{"color":"red"}',
            enabled=True,
        ),
        BindingRow(
            id="b2",
            hotkey="Ctrl+Alt+B",
            plugin="plugin",
            action_id="multi.action",
            payload_text='{"color":"red"}',
            enabled=True,
        ),
    ]

    issues = state.validate()

    assert any(
        issue.field == "payload"
        and issue.level == "warning"
        and "requires unique payloads" in issue.message
        for issue in issues
    )


def test_validation_allows_multi_action_with_distinct_payloads() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("multi.action", cardinality="multi")])
    state.rows = [
        BindingRow(
            id="b1",
            hotkey="Ctrl+Alt+A",
            plugin="plugin",
            action_id="multi.action",
            payload_text='{"color":"red"}',
            enabled=True,
        ),
        BindingRow(
            id="b2",
            hotkey="Ctrl+Alt+B",
            plugin="plugin",
            action_id="multi.action",
            payload_text='{"color":"blue"}',
            enabled=True,
        ),
    ]

    issues = state.validate()

    assert not any(
        issue.field == "payload"
        and issue.level == "warning"
        and "requires unique payloads" in issue.message
        for issue in issues
    )


def test_validation_ignores_disabled_rows_for_multi_payload_uniqueness_warning() -> None:
    document = default_document()
    state = SettingsState.from_document(document=document, actions=[_action("multi.action", cardinality="multi")])
    state.rows = [
        BindingRow(
            id="b1",
            hotkey="Ctrl+Alt+A",
            plugin="plugin",
            action_id="multi.action",
            payload_text='{"color":"red"}',
            enabled=False,
        ),
        BindingRow(
            id="b2",
            hotkey="Ctrl+Alt+B",
            plugin="plugin",
            action_id="multi.action",
            payload_text='{"color":"red"}',
            enabled=True,
        ),
    ]

    issues = state.validate()

    assert not any(
        issue.field == "payload"
        and issue.level == "warning"
        and "requires unique payloads" in issue.message
        for issue in issues
    )
