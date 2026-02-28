from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

import edmc_hotkeys.settings_ui as settings_ui
from edmc_hotkeys.settings_state import ActionOption
from edmc_hotkeys.settings_ui import hotkey_from_event, hotkey_from_parts


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
        "Removed",
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
