from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

import edmc_hotkeys.settings_ui as settings_ui
from edmc_hotkeys.settings_state import ActionOption
from edmc_hotkeys.settings_ui import (
    KEYD_ALERT_STATE_AUTO_HINT,
    KEYD_ALERT_STATE_EXPORT_REQUIRED,
    KEYD_ALERT_STATE_INACTIVE,
    KEYD_ALERT_STATE_INTEGRATION_MISSING,
    KEYD_ALERT_STATE_KEYD_MISSING,
    KEYD_ALERT_STATE_READY,
    KEYD_ALERT_STATE_X11_KEYD_CONFLICT,
    KeydAlertAction,
    KeydAlertActionOutcome,
    KeydAlertViewModel,
    build_keyd_copy_commands,
    hotkey_from_event,
    hotkey_from_parts,
    keyd_alert_view_for_state,
)


def _set_platform(monkeypatch: pytest.MonkeyPatch, *, is_windows: bool) -> None:
    monkeypatch.setattr(settings_ui, "_is_windows_platform", lambda: is_windows)


def _build_panel(*, logger: logging.Logger, supports_side_specific_modifiers: bool = True) -> settings_ui.SettingsPanel:
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    panel._logger = logger
    panel._supports_side_specific_modifiers = supports_side_specific_modifiers
    panel._active_modifier_tokens = {}
    panel._suppress_var_trace_handlers = False
    panel._refreshing_action_options = False
    return panel


class _DummyVar:
    def __init__(self) -> None:
        self.value: str | None = None

    def set(self, value: str) -> None:
        self.value = value


class _DummyStringVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value

    def trace_add(self, _mode: str, _callback: object) -> str:
        return "trace"


class _DummyCombo:
    def __init__(self) -> None:
        self.values: tuple[str, ...] = ()

    def configure(self, **kwargs: object) -> None:
        if "values" in kwargs:
            configured = kwargs["values"]
            if isinstance(configured, tuple):
                self.values = configured
            else:
                self.values = tuple(configured)

    def __setitem__(self, key: str, value: object) -> None:
        if key == "values":
            if isinstance(value, tuple):
                self.values = value
            else:
                self.values = tuple(value)


class _DummyGridWidget:
    def __init__(self) -> None:
        self.visible = False

    def grid(self, **_kwargs) -> None:
        self.visible = True

    def grid_remove(self) -> None:
        self.visible = False


class _DummyLogger:
    def __init__(self) -> None:
        self.debug_calls: list[str] = []

    def debug(self, message: str, **_kwargs: object) -> None:
        self.debug_calls.append(message)


def _action_option(
    action_id: str,
    *,
    plugin: str,
    label: str | None = None,
    enabled: bool = True,
    cardinality: str = "single",
) -> ActionOption:
    return ActionOption(
        action_id=action_id,
        label=label if label is not None else action_id,
        plugin=plugin,
        enabled=enabled,
        cardinality=cardinality,
    )


def _row_for_dropdown(*, plugin: str = "", action: str = "", payload: str = "", enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        plugin_var=_DummyStringVar(plugin),
        action_id_var=_DummyStringVar(action),
        action_display_var=_DummyStringVar(""),
        action_display_to_id={},
        action_label_by_id={},
        payload_var=_DummyStringVar(payload),
        enabled_var=_DummyStringVar("Yes" if enabled else "No"),
        action_combo=_DummyCombo(),
    )


def _build_dropdown_panel(*, action_options: list[ActionOption], rows: list[SimpleNamespace]) -> settings_ui.SettingsPanel:
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    panel._state = SimpleNamespace(action_options=action_options)
    panel._row_widgets = rows
    panel._refreshing_action_options = False
    panel._suppress_var_trace_handlers = False
    return panel


def test_hotkey_from_parts_captures_modifier_combo(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_platform(monkeypatch, is_windows=False)
    result = hotkey_from_parts(state=0x0005, keysym="x", char="x")
    assert result == "LCtrl+LShift+X"


def test_hotkey_from_parts_captures_ctrl_letter_when_char_is_control_code(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_platform(monkeypatch, is_windows=False)
    result = hotkey_from_parts(state=0x0004, keysym="a", char="\x01")
    assert result == "LCtrl+A"


def test_hotkey_from_parts_captures_alt_shift_number(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_platform(monkeypatch, is_windows=False)
    result = hotkey_from_parts(state=0x0009, keysym="exclam", char="!")
    assert result == "LAlt+LShift+1"


def test_hotkey_from_parts_captures_ctrl_shift_number(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_platform(monkeypatch, is_windows=False)
    result = hotkey_from_parts(state=0x0005, keysym="exclam", char="!")
    assert result == "LCtrl+LShift+1"


def test_hotkey_from_parts_captures_function_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_platform(monkeypatch, is_windows=False)
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


def test_hotkey_from_parts_uses_generic_modifiers_when_side_specific_is_unsupported() -> None:
    result = hotkey_from_parts(
        state=0x0005,
        keysym="x",
        char="x",
        supports_side_specific_modifiers=False,
    )
    assert result == "Ctrl+Shift+X"


def test_hotkey_from_parts_normalizes_active_side_specific_modifiers_to_generic_when_unsupported() -> None:
    result = hotkey_from_parts(
        state=0x0000,
        keysym="x",
        char="x",
        active_modifiers=("ctrl_r", "shift_l"),
        supports_side_specific_modifiers=False,
    )
    assert result == "Ctrl+Shift+X"


def test_hotkey_from_parts_linux_characterizes_state_only_alt_as_left_alt(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_platform(monkeypatch, is_windows=False)
    result = hotkey_from_parts(
        state=0x0008,
        keysym="x",
        char="x",
        active_modifiers=(),
        supports_side_specific_modifiers=True,
    )
    assert result == "LAlt+X"


def test_hotkey_from_parts_prefers_explicit_side_modifier_over_state_default() -> None:
    result = hotkey_from_parts(
        state=0x0008,
        keysym="x",
        char="x",
        active_modifiers=("alt_r",),
        supports_side_specific_modifiers=True,
    )
    assert result == "RAlt+X"


def test_hotkey_from_parts_windows_side_specific_requires_explicit_alt_side_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_platform(monkeypatch, is_windows=True)
    result = hotkey_from_parts(
        state=0x0008,
        keysym="x",
        char="x",
        active_modifiers=(),
        supports_side_specific_modifiers=True,
    )
    assert result == "X"


@pytest.mark.parametrize(
    ("state", "group"),
    (
        (0x0004, "ctrl"),
        (0x0008, "alt"),
        (0x0001, "shift"),
        (0x0040, "win"),
    ),
)
def test_hotkey_from_parts_windows_side_specific_requires_explicit_side_observation_for_all_groups(
    monkeypatch: pytest.MonkeyPatch,
    state: int,
    group: str,
) -> None:
    _set_platform(monkeypatch, is_windows=True)
    result = hotkey_from_parts(
        state=state,
        keysym="F1",
        char="",
        active_modifiers=(),
        supports_side_specific_modifiers=True,
    )
    assert result == "F1", f"Expected ambiguous '{group}' state-only modifier to be suppressed"


def test_hotkey_from_parts_windows_generic_mode_keeps_state_modifier_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_platform(monkeypatch, is_windows=True)
    result = hotkey_from_parts(
        state=0x0008,
        keysym="x",
        char="x",
        active_modifiers=(),
        supports_side_specific_modifiers=False,
    )
    assert result == "Alt+X"


def test_capture_hotkey_logs_warning_for_windows_ambiguous_modifier_state(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _set_platform(monkeypatch, is_windows=True)
    logger = logging.getLogger("tests.settings_ui.windows_ambiguous")
    panel = _build_panel(logger=logger, supports_side_specific_modifiers=True)
    hotkey_var = _DummyVar()
    widget = object()
    event = SimpleNamespace(keysym="x", char="x", state=0x0008)

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        result = panel._capture_hotkey(event, hotkey_var, widget)

    assert result == "break"
    assert hotkey_var.value == "X"
    assert "Hotkey capture resolved:" in caplog.text
    assert "Ambiguous Windows modifier state during hotkey capture" in caplog.text


def test_capture_hotkey_warning_lists_multiple_ambiguous_groups_in_order(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _set_platform(monkeypatch, is_windows=True)
    logger = logging.getLogger("tests.settings_ui.windows_multi_ambiguous")
    panel = _build_panel(logger=logger, supports_side_specific_modifiers=True)
    hotkey_var = _DummyVar()
    widget = object()
    event = SimpleNamespace(keysym="F2", char="", state=0x000C)  # ctrl + alt

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        result = panel._capture_hotkey(event, hotkey_var, widget)

    assert result == "break"
    assert hotkey_var.value == "F2"
    assert "groups=ctrl,alt" in caplog.text


def test_capture_hotkey_does_not_warn_when_side_modifier_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _set_platform(monkeypatch, is_windows=True)
    logger = logging.getLogger("tests.settings_ui.windows_explicit")
    panel = _build_panel(logger=logger, supports_side_specific_modifiers=True)
    hotkey_var = _DummyVar()
    widget = object()
    panel._active_modifier_tokens[str(widget)] = {"alt": "alt_r"}
    event = SimpleNamespace(keysym="x", char="x", state=0x0008)

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        result = panel._capture_hotkey(event, hotkey_var, widget)

    assert result == "break"
    assert hotkey_var.value == "RAlt+X"
    assert "Hotkey capture resolved:" in caplog.text
    assert "Ambiguous Windows modifier state during hotkey capture" not in caplog.text


def test_capture_hotkey_does_not_warn_on_linux_parity_path(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _set_platform(monkeypatch, is_windows=False)
    logger = logging.getLogger("tests.settings_ui.linux_parity")
    panel = _build_panel(logger=logger, supports_side_specific_modifiers=True)
    hotkey_var = _DummyVar()
    widget = object()
    event = SimpleNamespace(keysym="x", char="x", state=0x0008)

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        result = panel._capture_hotkey(event, hotkey_var, widget)

    assert result == "break"
    assert hotkey_var.value == "LAlt+X"
    assert "Hotkey capture resolved:" in caplog.text
    assert "Ambiguous Windows modifier state during hotkey capture" not in caplog.text


def test_capture_hotkey_allows_plain_text_editing_without_modifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_platform(monkeypatch, is_windows=False)
    logger = logging.getLogger("tests.settings_ui.manual_text_edit")
    panel = _build_panel(logger=logger, supports_side_specific_modifiers=True)
    hotkey_var = _DummyVar()
    widget = object()
    event = SimpleNamespace(keysym="x", char="x", state=0x0000)

    result = panel._capture_hotkey(event, hotkey_var, widget)

    assert result is None
    assert hotkey_var.value is None


def test_capture_hotkey_still_captures_special_keys_without_modifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_platform(monkeypatch, is_windows=False)
    logger = logging.getLogger("tests.settings_ui.special_capture")
    panel = _build_panel(logger=logger, supports_side_specific_modifiers=True)
    hotkey_var = _DummyVar()
    widget = object()
    event = SimpleNamespace(keysym="F2", char="", state=0x0000)

    result = panel._capture_hotkey(event, hotkey_var, widget)

    assert result == "break"
    assert hotkey_var.value == "F2"


def test_capture_hotkey_allows_plain_text_editing_with_shift_only_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_platform(monkeypatch, is_windows=False)
    logger = logging.getLogger("tests.settings_ui.shift_text_edit")
    panel = _build_panel(logger=logger, supports_side_specific_modifiers=True)
    hotkey_var = _DummyVar()
    widget = object()
    event = SimpleNamespace(keysym="plus", char="+", state=0x0001)

    result = panel._capture_hotkey(event, hotkey_var, widget)

    assert result is None
    assert hotkey_var.value is None


def test_capture_hotkey_still_captures_shift_modified_non_text_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_platform(monkeypatch, is_windows=False)
    logger = logging.getLogger("tests.settings_ui.shift_function_capture")
    panel = _build_panel(logger=logger, supports_side_specific_modifiers=True)
    hotkey_var = _DummyVar()
    widget = object()
    event = SimpleNamespace(keysym="F2", char="", state=0x0001)

    result = panel._capture_hotkey(event, hotkey_var, widget)

    assert result == "break"
    assert hotkey_var.value == "LShift+F2"


def test_action_dropdown_empty_when_plugin_unset() -> None:
    row = _row_for_dropdown(plugin="", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[_action_option("alpha.one", plugin="alpha")],
        rows=[row],
    )

    panel._refresh_row_action_options(row)

    assert row.action_combo.values == ()


def test_settings_columns_match_requested_order() -> None:
    assert [label for label, _width in settings_ui._COLUMN_SPECS] == [
        "Hotkey",
        "Plugin",
        "Action",
        "Payload",
        "Enabled",
        "",
    ]


def test_action_dropdown_filters_case_insensitive_plugin_match() -> None:
    row = _row_for_dropdown(plugin="ALPHA", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.one", plugin="alpha"),
            _action_option("beta.one", plugin="beta"),
        ],
        rows=[row],
    )

    panel._refresh_row_action_options(row)

    assert row.action_combo.values == ("alpha.one",)


def test_action_dropdown_shows_action_label_and_hides_action_id() -> None:
    row = _row_for_dropdown(plugin="alpha", action="alpha.one", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.one", plugin="alpha", label="Turn Overlay On"),
            _action_option("alpha.two", plugin="alpha", label="Turn Overlay Off"),
        ],
        rows=[row],
    )

    panel._refresh_row_action_options(row)

    assert row.action_combo.values == ("Turn Overlay On", "Turn Overlay Off")
    assert row.action_display_var.get() == "Turn Overlay On"
    assert row.action_id_var.get() == "alpha.one"


def test_action_dropdown_maps_selected_label_back_to_action_id() -> None:
    row = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[_action_option("alpha.one", plugin="alpha", label="Turn Overlay On")],
        rows=[row],
    )
    panel._refresh_row_action_options(row)

    row.action_display_var.set("Turn Overlay On")
    panel._on_action_value_changed(row)

    assert row.action_id_var.get() == "alpha.one"


def test_action_trace_handler_noops_when_suppressed() -> None:
    row = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[_action_option("alpha.one", plugin="alpha", label="Turn Overlay On")],
        rows=[row],
    )
    panel._refresh_row_action_options(row)

    panel._suppress_var_trace_handlers = True
    row.action_display_var.set("Turn Overlay On")
    panel._on_action_value_changed(row)

    assert row.action_id_var.get() == ""


def test_action_dropdown_excludes_actions_assigned_in_other_rows() -> None:
    row_one = _row_for_dropdown(plugin="alpha", action="alpha.one", payload="")
    row_two = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.one", plugin="alpha"),
            _action_option("alpha.two", plugin="alpha"),
        ],
        rows=[row_one, row_two],
    )

    panel._refresh_all_action_options()

    assert row_two.action_combo.values == ("alpha.two",)


def test_action_dropdown_ignores_actions_assigned_by_disabled_rows() -> None:
    disabled_row = _row_for_dropdown(plugin="alpha", action="alpha.one", payload="", enabled=False)
    other_row = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.one", plugin="alpha"),
            _action_option("alpha.two", plugin="alpha"),
        ],
        rows=[disabled_row, other_row],
    )

    panel._refresh_all_action_options()

    assert other_row.action_combo.values == ("alpha.one", "alpha.two")


def test_action_dropdown_multi_action_remains_available_when_assigned_in_other_row() -> None:
    row_one = _row_for_dropdown(plugin="alpha", action="alpha.multi", payload='{"color":"red"}')
    row_two = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.multi", plugin="alpha", cardinality="multi"),
            _action_option("alpha.single", plugin="alpha", cardinality="single"),
        ],
        rows=[row_one, row_two],
    )

    panel._refresh_all_action_options()

    assert row_two.action_combo.values == ("alpha.multi", "alpha.single")


def test_action_dropdown_treats_mixed_case_multi_cardinality_as_multi() -> None:
    row_one = _row_for_dropdown(plugin="alpha", action="alpha.multi", payload='{"color":"red"}')
    row_two = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.multi", plugin="alpha", cardinality="MuLtI"),
            _action_option("alpha.single", plugin="alpha", cardinality="single"),
        ],
        rows=[row_one, row_two],
    )

    panel._refresh_all_action_options()

    assert row_two.action_combo.values == ("alpha.multi", "alpha.single")


def test_action_dropdown_excludes_only_single_actions() -> None:
    row_one = _row_for_dropdown(plugin="alpha", action="alpha.single", payload="")
    row_two = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.single", plugin="alpha", cardinality="single"),
            _action_option("alpha.multi", plugin="alpha", cardinality="multi"),
        ],
        rows=[row_one, row_two],
    )

    panel._refresh_all_action_options()

    assert row_two.action_combo.values == ("alpha.multi",)


def test_action_dropdown_includes_disabled_actions() -> None:
    row = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.disabled", plugin="alpha", enabled=False),
            _action_option("alpha.enabled", plugin="alpha", enabled=True),
        ],
        rows=[row],
    )

    panel._refresh_row_action_options(row)

    assert row.action_combo.values == ("alpha.disabled", "alpha.enabled")


def test_action_clears_immediately_when_becomes_ineligible() -> None:
    row = _row_for_dropdown(plugin="alpha", action="alpha.one", payload='{"k":"v"}')
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.one", plugin="alpha"),
            _action_option("beta.one", plugin="beta"),
        ],
        rows=[row],
    )
    panel._refresh_all_action_options()

    row.plugin_var.set("beta")
    panel._on_plugin_value_changed(row)

    assert row.action_id_var.get() == ""


def test_payload_clears_when_action_is_auto_cleared() -> None:
    row = _row_for_dropdown(plugin="alpha", action="alpha.one", payload='{"k":"v"}')
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.one", plugin="alpha"),
            _action_option("beta.one", plugin="beta"),
        ],
        rows=[row],
    )
    panel._refresh_all_action_options()

    row.plugin_var.set("beta")
    panel._on_plugin_value_changed(row)

    assert row.payload_var.get() == ""


def test_action_dropdown_recomputes_on_plugin_change() -> None:
    row = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.one", plugin="alpha"),
            _action_option("beta.one", plugin="beta"),
        ],
        rows=[row],
    )
    panel._refresh_all_action_options()
    assert row.action_combo.values == ("alpha.one",)

    row.plugin_var.set("beta")
    panel._on_plugin_value_changed(row)

    assert row.action_combo.values == ("beta.one",)


def test_action_dropdown_recomputes_on_action_change() -> None:
    row_one = _row_for_dropdown(plugin="alpha", action="", payload="")
    row_two = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.one", plugin="alpha"),
            _action_option("alpha.two", plugin="alpha"),
        ],
        rows=[row_one, row_two],
    )
    panel._refresh_all_action_options()
    assert row_two.action_combo.values == ("alpha.one", "alpha.two")

    row_one.action_display_var.set("alpha.one")
    panel._on_action_value_changed(row_one)

    assert row_two.action_combo.values == ("alpha.two",)


def test_action_dropdown_recomputes_on_row_add_remove() -> None:
    row_one = _row_for_dropdown(plugin="alpha", action="alpha.one", payload="")
    row_two = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.one", plugin="alpha"),
            _action_option("alpha.two", plugin="alpha"),
        ],
        rows=[row_one, row_two],
    )
    panel._refresh_all_action_options()
    assert row_two.action_combo.values == ("alpha.two",)

    panel._row_widgets.remove(row_one)
    panel._refresh_all_action_options()
    assert row_two.action_combo.values == ("alpha.one", "alpha.two")


def test_action_dropdown_initial_render_applies_filtering() -> None:
    row_one = _row_for_dropdown(plugin="alpha", action="alpha.one", payload="")
    row_two = _row_for_dropdown(plugin="alpha", action="", payload="")
    panel = _build_dropdown_panel(
        action_options=[
            _action_option("alpha.one", plugin="alpha"),
            _action_option("alpha.two", plugin="alpha"),
            _action_option("beta.one", plugin="beta"),
        ],
        rows=[row_one, row_two],
    )

    panel._refresh_all_action_options()

    assert row_one.action_combo.values == ("alpha.one", "alpha.two")
    assert row_two.action_combo.values == ("alpha.two",)


def test_build_keyd_copy_commands_integration_missing_on_systemd_includes_restart() -> None:
    block = build_keyd_copy_commands(
        state=KEYD_ALERT_STATE_INTEGRATION_MISSING,
        install_command="sudo install helper",
        apply_command="sudo install config",
        systemd_available=True,
    )
    assert block == "sudo install helper\nsudo install config\nsudo systemctl restart keyd"


def test_build_keyd_copy_commands_non_systemd_adds_manual_restart_instruction() -> None:
    block = build_keyd_copy_commands(
        state=KEYD_ALERT_STATE_EXPORT_REQUIRED,
        install_command="unused",
        apply_command="sudo install config",
        systemd_available=False,
    )
    assert block == "sudo install config\n# Restart keyd manually for your init system."


def test_build_keyd_copy_commands_does_not_duplicate_restart_step() -> None:
    block = build_keyd_copy_commands(
        state=KEYD_ALERT_STATE_EXPORT_REQUIRED,
        install_command="unused",
        apply_command="sudo install config && sudo systemctl restart keyd",
        systemd_available=True,
    )
    assert block == "sudo install config && sudo systemctl restart keyd"


def test_keyd_alert_view_for_state_integration_missing_wires_actions_and_warnings() -> None:
    view = keyd_alert_view_for_state(
        KEYD_ALERT_STATE_INTEGRATION_MISSING,
        install_command="sudo install helper",
        apply_command="sudo install config",
        systemd_available=True,
        on_install=lambda: KeydAlertActionOutcome(success_message="ok"),
    )
    assert view.visible is True
    assert view.primary_action is not None
    assert view.primary_action.label == "Install Integration"
    assert view.show_copy_button is True
    assert "sudo systemctl restart keyd" in view.copy_commands
    assert view.show_privilege_warning is True
    assert view.show_terminal_warning is True


def test_format_keyd_warning_text_uses_primary_action_label() -> None:
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    alert = KeydAlertViewModel(
        state=KEYD_ALERT_STATE_INTEGRATION_MISSING,
        primary_action=KeydAlertAction(label="Install Integration", callback=lambda: None),
        show_privilege_warning=True,
        show_terminal_warning=True,
    )

    warning_text = panel._format_keyd_warning_text(alert)

    assert "Warning: Integration requires elevated privileges (sudo)." in warning_text
    assert "Warning: Install Integration opens a terminal/auth prompt." in warning_text


def test_keyd_alert_view_for_state_keyd_missing_uses_restart_install_summary() -> None:
    view = keyd_alert_view_for_state(KEYD_ALERT_STATE_KEYD_MISSING)
    assert view.summary == "Install keyd and restart EDMC."
    assert "not installed or not active" in view.body
    assert view.visible is True


def test_keyd_alert_view_for_state_auto_hint_uses_approved_text() -> None:
    view = keyd_alert_view_for_state(KEYD_ALERT_STATE_AUTO_HINT)
    assert view.summary == "Keyd is not active."
    assert "Wayland auto mode" in view.body
    assert "restart EDMC" in view.body
    assert view.visible is True


def test_keyd_alert_view_for_state_x11_keyd_conflict_is_info_only() -> None:
    view = keyd_alert_view_for_state(KEYD_ALERT_STATE_X11_KEYD_CONFLICT)
    assert view.summary == "Keyd may conflict with X11 hotkeys."
    assert "conflicts may cause hotkeys to not work" in view.body
    assert "remove /etc/keyd/edmchotkeys.conf and restart keyd" in view.body
    assert view.primary_action is None
    assert view.show_copy_button is False
    assert view.show_privilege_warning is False
    assert view.show_terminal_warning is False
    assert view.visible is True


def test_keyd_alert_view_for_state_ready_and_inactive_are_hidden() -> None:
    inactive = keyd_alert_view_for_state(KEYD_ALERT_STATE_INACTIVE)
    ready = keyd_alert_view_for_state(KEYD_ALERT_STATE_READY)
    assert inactive.visible is False
    assert ready.visible is False


def test_keyd_primary_action_applies_outcome() -> None:
    outcome = KeydAlertActionOutcome(success_message="done")
    captured: list[KeydAlertActionOutcome | None] = []
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    panel._keyd_alert_model = KeydAlertViewModel(
        state=KEYD_ALERT_STATE_EXPORT_REQUIRED,
        primary_action=KeydAlertAction(label="Export Config", callback=lambda: outcome),
    )
    panel._apply_keyd_action_outcome = lambda result: captured.append(result)
    panel._logger = logging.getLogger("tests.settings_ui.keyd_action")

    panel._on_keyd_primary_action()

    assert captured == [outcome]


def test_keyd_primary_action_exception_surfaces_inline_error(monkeypatch: pytest.MonkeyPatch) -> None:
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    panel._keyd_alert_model = KeydAlertViewModel(
        state=KEYD_ALERT_STATE_EXPORT_REQUIRED,
        primary_action=KeydAlertAction(
            label="Export Config",
            callback=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        ),
    )
    panel._logger = logging.getLogger("tests.settings_ui.keyd_action_error")
    captured: list[tuple[str, str]] = []
    panel.show_keyd_alert_error = lambda summary, details="": captured.append((summary, details))

    panel._on_keyd_primary_action()

    assert captured
    assert "Action failed" in captured[0][0]
    assert "boom" in captured[0][1]


def test_on_hotkey_commit_clears_modifiers_and_notifies_change_callback() -> None:
    callback_calls: list[str] = []
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    panel._active_modifier_tokens = {"widget-1": {"ctrl": "ctrl_l"}}
    panel._on_bindings_changed = lambda: callback_calls.append("changed")
    panel._logger = _DummyLogger()

    result = panel._on_hotkey_commit("widget-1")

    assert result is None
    assert "widget-1" not in panel._active_modifier_tokens
    assert callback_calls == ["changed"]


def test_notify_bindings_changed_logs_debug_on_callback_error() -> None:
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    panel._on_bindings_changed = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    panel._logger = _DummyLogger()

    panel._notify_bindings_changed()

    assert panel._logger.debug_calls == ["Failed to process settings change callback"]


def test_on_add_binding_clicked_adds_blank_row_without_immediate_notify() -> None:
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    captured: dict[str, object] = {}

    def _fake_add_row(row: settings_ui.BindingRow, *, notify_changes: bool = True) -> None:
        captured["row"] = row
        captured["notify_changes"] = notify_changes

    panel.add_row = _fake_add_row  # type: ignore[method-assign]

    panel._on_add_binding_clicked()

    added_row = captured["row"]
    assert isinstance(added_row, settings_ui.BindingRow)
    assert added_row.id == ""
    assert added_row.hotkey == ""
    assert added_row.plugin == ""
    assert added_row.action_id == ""
    assert added_row.payload is None
    assert added_row.enabled is True
    assert captured["notify_changes"] is False


def test_on_version_link_clicked_opens_repository_url(monkeypatch: pytest.MonkeyPatch) -> None:
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    panel._version_repo_url = "https://github.com/SweetJonnySauce/EDMCHotkeys"
    panel._logger = _DummyLogger()
    opened_urls: list[str] = []
    monkeypatch.setattr(settings_ui.webbrowser, "open", lambda url: opened_urls.append(url))

    result = panel._on_version_link_clicked(None)

    assert result == "break"
    assert opened_urls == ["https://github.com/SweetJonnySauce/EDMCHotkeys"]


def test_on_version_link_clicked_noops_when_repository_url_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    panel._version_repo_url = ""
    panel._logger = _DummyLogger()
    opened_urls: list[str] = []
    monkeypatch.setattr(settings_ui.webbrowser, "open", lambda url: opened_urls.append(url))

    result = panel._on_version_link_clicked(None)

    assert result is None
    assert opened_urls == []


def test_set_validation_issues_uses_hotkey_label_for_row_id() -> None:
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    panel._validation_var = _DummyVar()
    panel._row_widgets = [
        SimpleNamespace(
            row_id_var=_DummyStringVar("binding_a"),
            hotkey_var=_DummyStringVar("LCtrl+LShift+X"),
        )
    ]

    panel.set_validation_issues(
        [
            settings_ui.ValidationIssue(
                level="error",
                row_id="binding_a",
                field="hotkey",
                message="Hotkey conflicts with 'binding_b'",
            )
        ]
    )

    assert panel._validation_var.value is not None
    assert "LCtrl+LShift+X.hotkey" in panel._validation_var.value
    assert "binding_a.hotkey" not in panel._validation_var.value


def test_plugin_and_action_value_change_notifies_bindings_changed() -> None:
    callback_calls: list[str] = []
    row = _row_for_dropdown(plugin="alpha", action="", payload="")
    row.action_display_to_id = {"Turn Overlay On": "alpha.one"}
    row.action_display_var.set("Turn Overlay On")
    row.action_id_var.set("")
    panel = _build_dropdown_panel(
        action_options=[_action_option("alpha.one", plugin="alpha", label="Turn Overlay On")],
        rows=[row],
    )
    panel._on_bindings_changed = lambda: callback_calls.append("changed")

    panel._on_plugin_value_changed(row)
    panel._on_action_value_changed(row)

    assert len(callback_calls) == 2


def test_toggle_keyd_error_details_expands_and_collapses() -> None:
    panel = settings_ui.SettingsPanel.__new__(settings_ui.SettingsPanel)
    panel._keyd_alert_error_details_var = _DummyStringVar("traceback lines")
    panel._keyd_error_details_label = _DummyGridWidget()
    panel._keyd_alert_details_button_var = _DummyStringVar("Show details")
    panel._keyd_details_expanded = False

    panel._toggle_keyd_error_details()
    assert panel._keyd_error_details_label.visible is True
    assert panel._keyd_alert_details_button_var.get() == "Hide details"
    assert panel._keyd_details_expanded is True

    panel._toggle_keyd_error_details()
    assert panel._keyd_error_details_label.visible is False
    assert panel._keyd_alert_details_button_var.get() == "Show details"
    assert panel._keyd_details_expanded is False
