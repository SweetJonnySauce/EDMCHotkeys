"""Settings UI widgets for editing bindings."""

from __future__ import annotations

import logging
import sys
import uuid
from dataclasses import dataclass
from typing import Callable, Optional

from .hotkey import CANONICAL_MODIFIER_ORDER, normalize_key_token, pretty_hotkey_text
from .registry import ACTION_CARDINALITY_SINGLE, normalize_action_cardinality
from .settings_state import BindingRow, SettingsState, ValidationIssue

try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import font as tkfont
except Exception:  # pragma: no cover - exercised only in EDMC runtime without tkinter
    tk = None
    ttk = None
    tkfont = None


_SHIFT_MASK = 0x0001
_CONTROL_MASK = 0x0004
_ALT_MASK = 0x0008
_SUPER_MASK = 0x0040
_MODIFIER_STATE_FLAGS = (
    ("ctrl", _CONTROL_MASK),
    ("alt", _ALT_MASK),
    ("shift", _SHIFT_MASK),
    ("win", _SUPER_MASK),
)
_MODIFIER_STATE_MASK = _SHIFT_MASK | _CONTROL_MASK | _ALT_MASK | _SUPER_MASK
_MODIFIER_KEYSYMS = {
    "Shift_L",
    "Shift_R",
    "Control_L",
    "Control_R",
    "Alt_L",
    "Alt_R",
    "Super_L",
    "Super_R",
    "Meta_L",
    "Meta_R",
}
_EDITING_KEYSYMS = {
    "BackSpace",
    "Delete",
    "Left",
    "Right",
    "Up",
    "Down",
    "Home",
    "End",
    "Prior",
    "Next",
    "Insert",
    "Tab",
    "ISO_Left_Tab",
    "Return",
    "KP_Enter",
}
_MODIFIER_KEYSYM_TO_TOKEN = {
    "Control_L": ("ctrl", "ctrl_l"),
    "Control_R": ("ctrl", "ctrl_r"),
    "Alt_L": ("alt", "alt_l"),
    "Alt_R": ("alt", "alt_r"),
    "Shift_L": ("shift", "shift_l"),
    "Shift_R": ("shift", "shift_r"),
    "Super_L": ("win", "win_l"),
    "Super_R": ("win", "win_r"),
    "Meta_L": ("win", "win_l"),
    "Meta_R": ("win", "win_r"),
}
_SHIFTED_SYMBOL_TO_BASE_KEY = {
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "exclam": "1",
    "at": "2",
    "numbersign": "3",
    "dollar": "4",
    "percent": "5",
    "asciicircum": "6",
    "ampersand": "7",
    "asterisk": "8",
    "parenleft": "9",
    "parenright": "0",
}


_COLUMN_SPECS = (
    ("Hotkey", 14),
    ("Plugin", 16),
    ("Action", 24),
    ("Payload", 24),
    ("Enabled", 7),
    ("", 8),
)
_ENABLED_CHOICES = ("Yes", "No")
_CELL_PAD_X = (0, 6)
_CELL_PAD_Y = 2
_HEADER_PAD_Y = (0, 6)

KEYD_ALERT_STATE_INACTIVE = "Inactive"
KEYD_ALERT_STATE_KEYD_MISSING = "KeydMissing"
KEYD_ALERT_STATE_INTEGRATION_MISSING = "IntegrationMissing"
KEYD_ALERT_STATE_READY = "Ready"
KEYD_ALERT_STATE_EXPORT_REQUIRED = "ExportRequired"
KEYD_ALERT_STATE_AUTO_HINT = "AutoHint"

_KEYD_ALERT_VISIBLE_STATES = {
    KEYD_ALERT_STATE_KEYD_MISSING,
    KEYD_ALERT_STATE_INTEGRATION_MISSING,
    KEYD_ALERT_STATE_EXPORT_REQUIRED,
    KEYD_ALERT_STATE_AUTO_HINT,
}


@dataclass(frozen=True)
class KeydAlertActionOutcome:
    refreshed_alert: "KeydAlertViewModel | None" = None
    success_message: str = ""
    error_summary: str = ""
    error_details: str = ""


@dataclass(frozen=True)
class KeydAlertAction:
    label: str
    callback: Callable[[], KeydAlertActionOutcome | None]


@dataclass(frozen=True)
class KeydAlertViewModel:
    state: str
    summary: str = ""
    body: str = ""
    primary_action: KeydAlertAction | None = None
    copy_commands: str = ""
    show_copy_button: bool = False
    show_privilege_warning: bool = False
    show_terminal_warning: bool = False

    @property
    def visible(self) -> bool:
        return self.state in _KEYD_ALERT_VISIBLE_STATES


def _enabled_label(value: bool) -> str:
    return "Yes" if value else "No"


def _enabled_from_label(value: str) -> bool:
    return value.strip().lower() in {"yes", "true", "1"}


def _new_binding_id() -> str:
    return f"binding_{uuid.uuid4().hex[:8]}"


def _append_restart_step(command_steps: list[str], *, systemd_available: bool) -> None:
    if systemd_available:
        restart_cmd = "sudo systemctl restart keyd"
        if any("systemctl restart keyd" in step for step in command_steps):
            return
        command_steps.append(restart_cmd)
        return
    command_steps.append("# Restart keyd manually for your init system.")


def build_keyd_copy_commands(
    *,
    state: str,
    install_command: str,
    apply_command: str,
    systemd_available: bool,
) -> str:
    """Build copy-ready command block for keyd integration and export workflows."""
    command_steps: list[str] = []
    if state == KEYD_ALERT_STATE_INTEGRATION_MISSING:
        if install_command.strip():
            command_steps.append(install_command.strip())
        if apply_command.strip():
            command_steps.append(apply_command.strip())
        _append_restart_step(command_steps, systemd_available=systemd_available)
    elif state == KEYD_ALERT_STATE_EXPORT_REQUIRED:
        if apply_command.strip():
            command_steps.append(apply_command.strip())
        _append_restart_step(command_steps, systemd_available=systemd_available)
    return "\n".join(command_steps)


def keyd_alert_view_for_state(
    state: str,
    *,
    install_command: str = "",
    apply_command: str = "",
    systemd_available: bool = True,
    on_install: Callable[[], KeydAlertActionOutcome | None] | None = None,
    on_export: Callable[[], KeydAlertActionOutcome | None] | None = None,
) -> KeydAlertViewModel:
    """Return the default UI model for a keyd preferences alert state."""
    if state == KEYD_ALERT_STATE_KEYD_MISSING:
        return KeydAlertViewModel(
            state=state,
            summary="Install keyd and restart EDMC.",
            body=(
                "keyd is not installed or not active. Install and start keyd, restart EDMC, then return to this settings page "
                "for integration setup."
            ),
        )
    if state == KEYD_ALERT_STATE_INTEGRATION_MISSING:
        return KeydAlertViewModel(
            state=state,
            summary="EDMCHotkeys keyd integration is not installed yet.",
            body=(
                "Integration installs the helper script and keyd config so keyd can "
                "forward binding ids to EDMCHotkeys."
            ),
            primary_action=(
                KeydAlertAction(label="Install Integration", callback=on_install)
                if on_install is not None
                else None
            ),
            copy_commands=build_keyd_copy_commands(
                state=state,
                install_command=install_command,
                apply_command=apply_command,
                systemd_available=systemd_available,
            ),
            show_copy_button=True,
            show_privilege_warning=True,
            show_terminal_warning=True,
        )
    if state == KEYD_ALERT_STATE_EXPORT_REQUIRED:
        return KeydAlertViewModel(
            state=state,
            summary="Hotkey changes require exporting a new keyd config.",
            body="Export and apply the generated keyd config, then restart keyd.",
            primary_action=(
                KeydAlertAction(label="Export Config", callback=on_export)
                if on_export is not None
                else None
            ),
            copy_commands=build_keyd_copy_commands(
                state=state,
                install_command=install_command,
                apply_command=apply_command,
                systemd_available=systemd_available,
            ),
            show_copy_button=True,
            show_privilege_warning=True,
            show_terminal_warning=True,
        )
    if state == KEYD_ALERT_STATE_AUTO_HINT:
        return KeydAlertViewModel(
            state=state,
            summary="Keyd is not active.",
            body=(
                "EDMCHotkeys is running in Wayland auto mode, but keyd is not active. "
                "Install/start keyd, restart EDMC, then return to this settings page "
                "to enable keyd integration."
            ),
        )
    if state in {KEYD_ALERT_STATE_INACTIVE, KEYD_ALERT_STATE_READY}:
        return KeydAlertViewModel(state=state)
    return KeydAlertViewModel(state=KEYD_ALERT_STATE_INACTIVE)


@dataclass
class _RowWidgets:
    row_id_var: object
    hotkey_var: object
    plugin_var: object
    plugin_combo: object
    action_id_var: object
    action_display_var: object
    action_display_to_id: dict[str, str]
    action_label_by_id: dict[str, str]
    action_combo: object
    payload_var: object
    payload_entry: object
    payload: dict | None
    enabled_var: object
    widgets: tuple[object, ...]


class SettingsPanel:
    """Table-like settings editor for bindings."""

    def __init__(
        self,
        parent: object,
        state: SettingsState,
        *,
        logger: logging.Logger,
        notebook_widgets: object | None = None,
        supports_side_specific_modifiers: bool = True,
        on_bindings_changed: Callable[[], None] | None = None,
    ) -> None:
        if tk is None or ttk is None:
            raise RuntimeError("tkinter is unavailable")
        self._logger = logger
        self._state = state
        self._notebook_widgets = notebook_widgets
        self._supports_side_specific_modifiers = supports_side_specific_modifiers
        self._on_bindings_changed = on_bindings_changed
        self.frame = self._widget_class("Frame", ttk.Frame)(parent)
        self._row_widgets: list[_RowWidgets] = []
        self._active_modifier_tokens: dict[str, dict[str, str]] = {}
        self._header_font: object | None = None
        self._keyd_alert_summary_font: object | None = None
        self._refreshing_action_options = False
        self._suppress_var_trace_handlers = False
        self._keyd_alert_model: KeydAlertViewModel | None = None
        self._keyd_details_expanded = False
        self._rows_scrollable = False
        self._rows_scrollbar: object | None = None
        self._rows_body: object | None = None
        self._rows_scrollbar_width = 0

        self._plugin_values = sorted({option.plugin for option in state.action_options if option.plugin})

        self._build_layout()
        for row in state.rows:
            self.add_row(row, notify_changes=False)

    def add_row(self, row: BindingRow, *, notify_changes: bool = True) -> None:
        if tk is None or ttk is None:
            return

        row_id_var = tk.StringVar(value=row.id or _new_binding_id())
        hotkey_var = tk.StringVar(value=row.hotkey)
        plugin_var = tk.StringVar(value=row.plugin)
        action_id_var = tk.StringVar(value=row.action_id)
        action_display_var = tk.StringVar(value="")
        payload_var = tk.StringVar(value=row.payload_text)
        enabled_var = tk.StringVar(value=_enabled_label(row.enabled))

        row_index = len(self._row_widgets) + 1
        hotkey_entry = self._widget_class(
            "Entry",
            ttk.Entry,
        )(self._rows_inner, textvariable=hotkey_var, width=_COLUMN_SPECS[0][1])
        hotkey_entry.grid(
            row=row_index,
            column=0,
            padx=_CELL_PAD_X,
            pady=_CELL_PAD_Y,
            sticky="w",
        )
        hotkey_entry.bind("<KeyPress>", lambda event, var=hotkey_var, widget=hotkey_entry: self._capture_hotkey(event, var, widget))
        hotkey_entry.bind("<KeyRelease>", lambda event, widget=hotkey_entry: self._release_modifier(event, widget))
        hotkey_entry.bind("<FocusOut>", lambda _event, widget=hotkey_entry: self._on_hotkey_commit(widget))
        hotkey_entry.bind("<Return>", lambda _event, widget=hotkey_entry: self._on_hotkey_commit(widget))
        hotkey_entry.bind("<KP_Enter>", lambda _event, widget=hotkey_entry: self._on_hotkey_commit(widget))
        hotkey_entry.bind("<Tab>", lambda _event, widget=hotkey_entry: self._on_hotkey_commit(widget))
        plugin_combo = self._widget_class("Combobox", ttk.Combobox)(
            self._rows_inner,
            textvariable=plugin_var,
            values=self._plugin_values,
            state="readonly",
            width=_COLUMN_SPECS[1][1],
        )
        plugin_combo.grid(row=row_index, column=1, padx=_CELL_PAD_X, pady=_CELL_PAD_Y, sticky="w")
        action_combo = self._widget_class("Combobox", ttk.Combobox)(
            self._rows_inner,
            textvariable=action_display_var,
            values=(),
            state="readonly",
            width=_COLUMN_SPECS[2][1],
        )
        action_combo.grid(row=row_index, column=2, padx=_CELL_PAD_X, pady=_CELL_PAD_Y, sticky="w")
        payload_entry = self._widget_class("Entry", ttk.Entry)(
            self._rows_inner,
            textvariable=payload_var,
            width=_COLUMN_SPECS[3][1],
        )
        payload_entry.grid(
            row=row_index,
            column=3,
            padx=_CELL_PAD_X,
            pady=_CELL_PAD_Y,
            sticky="w",
        )
        payload_entry.bind("<FocusOut>", lambda _event: self._notify_bindings_changed())
        payload_entry.bind("<Return>", lambda _event: self._notify_bindings_changed())
        payload_entry.bind("<KP_Enter>", lambda _event: self._notify_bindings_changed())
        payload_entry.bind("<Tab>", lambda _event: self._notify_bindings_changed())
        enabled_combo = self._widget_class("Combobox", ttk.Combobox)(
            self._rows_inner,
            textvariable=enabled_var,
            values=_ENABLED_CHOICES,
            state="readonly",
            width=_COLUMN_SPECS[4][1],
        )
        enabled_combo.grid(row=row_index, column=4, padx=_CELL_PAD_X, pady=_CELL_PAD_Y, sticky="w")
        enabled_combo.bind("<<ComboboxSelected>>", lambda _event: self._notify_bindings_changed())
        remove_button = self._widget_class("Button", ttk.Button)(
            self._rows_inner,
            text="Remove",
            width=_COLUMN_SPECS[5][1],
        )
        try:
            remove_button.configure(style="Hotkeys.RowRemove.TButton")
        except Exception:
            pass
        remove_button.grid(row=row_index, column=5, pady=_CELL_PAD_Y, sticky="w")
        self._bind_mousewheel_recursive(self._rows_inner)

        row_widgets = _RowWidgets(
            row_id_var=row_id_var,
            hotkey_var=hotkey_var,
            plugin_var=plugin_var,
            plugin_combo=plugin_combo,
            action_id_var=action_id_var,
            action_display_var=action_display_var,
            action_display_to_id={},
            action_label_by_id={},
            action_combo=action_combo,
            payload_var=payload_var,
            payload_entry=payload_entry,
            payload=row.payload,
            enabled_var=enabled_var,
            widgets=(
                hotkey_entry,
                plugin_combo,
                action_combo,
                payload_entry,
                enabled_combo,
                remove_button,
            ),
        )
        plugin_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event, widgets=row_widgets: self._on_plugin_value_changed(widgets),
        )
        action_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event, widgets=row_widgets: self._on_action_value_changed(widgets),
        )
        remove_button.configure(command=lambda widgets=row_widgets: self._remove_row(widgets))
        self._row_widgets.append(row_widgets)
        self._refresh_row_positions()
        self._refresh_scroll_region()
        self._refresh_all_action_options()
        if notify_changes:
            self._notify_bindings_changed()

    def get_rows(self) -> list[BindingRow]:
        rows: list[BindingRow] = []
        for row in self._row_widgets:
            rows.append(
                BindingRow(
                    id=row.row_id_var.get().strip(),
                    hotkey=row.hotkey_var.get().strip(),
                    plugin=row.plugin_var.get().strip(),
                    action_id=row.action_id_var.get().strip(),
                    payload=row.payload,
                    payload_text=row.payload_var.get().strip(),
                    enabled=_enabled_from_label(str(row.enabled_var.get())),
                )
            )
        return rows

    def set_validation_issues(self, issues: list[ValidationIssue]) -> None:
        if tk is None:
            return
        if not issues:
            self._validation_var.set("No validation issues.")
            return
        lines = [
            f"[{issue.level}] {self._row_label_for_validation_issue(issue.row_id)}.{issue.field}: {issue.message}"
            for issue in issues
        ]
        self._validation_var.set("\n".join(lines))

    def _row_label_for_validation_issue(self, row_id: str) -> str:
        target_row_id = row_id.strip()
        if not target_row_id:
            return row_id
        for row in getattr(self, "_row_widgets", []):
            current_id = row.row_id_var.get().strip()
            if current_id != target_row_id:
                continue
            hotkey = row.hotkey_var.get().strip()
            return hotkey or row_id
        return row_id

    def set_keyd_alert(self, alert: KeydAlertViewModel | None) -> None:
        if tk is None:
            return
        self._keyd_alert_model = alert
        self._clear_keyd_feedback()
        if alert is None or not alert.visible:
            self._keyd_alert_frame.grid_remove()
            return
        self._keyd_alert_frame.grid()
        self._apply_keyd_summary_font()
        self._keyd_alert_var.set(alert.summary.strip())
        self._keyd_alert_body_var.set(alert.body.strip())
        self._keyd_alert_warning_var.set(self._format_keyd_warning_text(alert))
        self._keyd_details_expanded = False
        self._keyd_alert_details_button_var.set("Show details")
        self._keyd_error_details_label.grid_remove()

        if alert.primary_action is None:
            self._keyd_primary_button.grid_remove()
            self._keyd_primary_button.configure(text="")
        else:
            self._keyd_primary_button.configure(text=alert.primary_action.label)
            self._keyd_primary_button.grid()

        if alert.show_copy_button and alert.copy_commands.strip():
            self._keyd_copy_button.grid()
        else:
            self._keyd_copy_button.grid_remove()

    def show_keyd_alert_success(self, message: str) -> None:
        if tk is None:
            return
        self._keyd_alert_success_var.set(message.strip())
        self._keyd_alert_error_frame.grid_remove()
        self._keyd_alert_error_summary_var.set("")
        self._keyd_alert_error_details_var.set("")
        self._keyd_error_details_button.grid_remove()
        self._keyd_error_details_label.grid_remove()
        self._keyd_details_expanded = False

    def show_keyd_alert_error(self, summary: str, details: str = "") -> None:
        if tk is None:
            return
        self._keyd_alert_success_var.set("")
        self._keyd_alert_error_summary_var.set(summary.strip())
        self._keyd_alert_error_details_var.set(details.strip())
        self._keyd_alert_error_frame.grid()
        if details.strip():
            self._keyd_error_details_button.grid()
        else:
            self._keyd_error_details_button.grid_remove()
            self._keyd_error_details_label.grid_remove()
        self._keyd_details_expanded = False
        self._keyd_alert_details_button_var.set("Show details")

    def _build_layout(self) -> None:
        if tk is None or ttk is None:
            return

        self.frame.columnconfigure(0, weight=1)

        body = self._widget_class("Frame", ttk.Frame)(self.frame)
        self._rows_body = body
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        style = ttk.Style()
        style.configure("Hotkeys.TEntry", padding=0)
        style.configure("Hotkeys.TCombobox", padding=0)
        style.configure("Hotkeys.RowRemove.TButton", padding=(4, 0))

        header_font = None
        alert_summary_font = None
        if tkfont is not None:
            style = ttk.Style()
            font_name = style.lookup("TLabel", "font") or "TkDefaultFont"
            try:
                base_font = tkfont.nametofont(font_name)
            except Exception:
                base_font = tkfont.nametofont("TkDefaultFont")
            family = base_font.actual("family") or "TkDefaultFont"
            size = int(base_font.actual("size") or 9)
            header_font = (family, size, "bold")
            alert_summary_font = (family, size, "bold")
            self._header_font = header_font
            self._keyd_alert_summary_font = alert_summary_font
        else:
            self._header_font = ("TkDefaultFont", 9, "bold")
            self._keyd_alert_summary_font = ("TkDefaultFont", 9, "bold")

        self._canvas = tk.Canvas(body, borderwidth=0, highlightthickness=0, height=400)
        self._canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar = self._widget_class("Scrollbar", ttk.Scrollbar)(
            body,
            orient="vertical",
            command=self._canvas.yview,
        )
        self._rows_scrollbar = scrollbar
        scrollbar.grid(row=1, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar_width = scrollbar.winfo_reqwidth()
        self._rows_scrollbar_width = scrollbar_width
        body.columnconfigure(1, minsize=0)
        scrollbar.grid_remove()
        self._rows_inner = self._widget_class("Frame", ttk.Frame)(self._canvas)
        header_label_font = header_font or self._header_font
        for index, (label, width) in enumerate(_COLUMN_SPECS):
            label_kwargs = {
                "text": label,
                "width": width,
                "anchor": "w",
                "font": header_label_font,
            }
            tk.Label(self._rows_inner, **label_kwargs).grid(
                row=0,
                column=index,
                padx=_CELL_PAD_X if index < len(_COLUMN_SPECS) - 1 else 0,
                pady=_HEADER_PAD_Y,
                sticky="w",
            )
        self._canvas_window = self._canvas.create_window((0, 0), window=self._rows_inner, anchor="nw")
        self._rows_inner.bind("<Configure>", lambda _evt: self._refresh_scroll_region())
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        controls = self._widget_class("Frame", ttk.Frame)(self.frame)
        controls.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self._widget_class("Button", ttk.Button)(
            controls,
            text="Add Binding",
            command=lambda: self.add_row(
                BindingRow(id="", hotkey="", plugin="", action_id="", payload=None, enabled=True)
            ),
        ).grid(row=0, column=0, sticky="w")

        self._keyd_alert_var = tk.StringVar(value="")
        self._keyd_alert_body_var = tk.StringVar(value="")
        self._keyd_alert_warning_var = tk.StringVar(value="")
        self._keyd_alert_success_var = tk.StringVar(value="")
        self._keyd_alert_error_summary_var = tk.StringVar(value="")
        self._keyd_alert_error_details_var = tk.StringVar(value="")
        self._keyd_alert_details_button_var = tk.StringVar(value="Show details")

        self._keyd_alert_frame = self._widget_class("Frame", ttk.Frame)(self.frame)
        self._keyd_alert_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self._keyd_alert_frame.grid_remove()
        self._keyd_alert_frame.columnconfigure(0, weight=1)

        summary_label_kwargs = {
            "textvariable": self._keyd_alert_var,
            "justify": "left",
            "wraplength": 640,
        }
        summary_label_kwargs["font"] = alert_summary_font or self._keyd_alert_summary_font
        # Use a plain tk.Label with explicit font so bold rendering does not depend on ttk/myNotebook style mapping.
        self._keyd_alert_summary_label = tk.Label(self._keyd_alert_frame, anchor="w", **summary_label_kwargs)
        self._keyd_alert_summary_label.grid(
            row=0,
            column=0,
            sticky="ew",
        )
        self._apply_keyd_summary_font()
        self._widget_class(
            "Label",
            ttk.Label,
        )(self._keyd_alert_frame, textvariable=self._keyd_alert_body_var, justify="left", wraplength=640).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(4, 0),
        )

        self._widget_class(
            "Label",
            ttk.Label,
        )(self._keyd_alert_frame, textvariable=self._keyd_alert_warning_var, justify="left", wraplength=640).grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(4, 0),
        )

        self._keyd_alert_actions = self._widget_class("Frame", ttk.Frame)(self._keyd_alert_frame)
        self._keyd_alert_actions.grid(row=3, column=0, sticky="w", pady=(6, 0))
        self._keyd_primary_button = self._widget_class(
            "Button",
            ttk.Button,
        )(self._keyd_alert_actions, text="", command=self._on_keyd_primary_action)
        self._keyd_primary_button.grid(row=0, column=0, sticky="w")
        self._keyd_primary_button.grid_remove()
        self._keyd_copy_button = self._widget_class(
            "Button",
            ttk.Button,
        )(self._keyd_alert_actions, text="Copy Commands", command=self._on_keyd_copy_commands)
        self._keyd_copy_button.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self._keyd_copy_button.grid_remove()

        self._widget_class(
            "Label",
            ttk.Label,
        )(self._keyd_alert_frame, textvariable=self._keyd_alert_success_var, justify="left", wraplength=640).grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(4, 0),
        )

        self._keyd_alert_error_frame = self._widget_class("Frame", ttk.Frame)(self._keyd_alert_frame)
        self._keyd_alert_error_frame.grid(row=5, column=0, sticky="ew", pady=(4, 0))
        self._keyd_alert_error_frame.columnconfigure(0, weight=1)
        self._keyd_alert_error_frame.grid_remove()
        self._widget_class(
            "Label",
            ttk.Label,
        )(
            self._keyd_alert_error_frame,
            textvariable=self._keyd_alert_error_summary_var,
            justify="left",
            wraplength=640,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
        )
        self._keyd_error_details_button = self._widget_class(
            "Button",
            ttk.Button,
        )(
            self._keyd_alert_error_frame,
            textvariable=self._keyd_alert_details_button_var,
            command=self._toggle_keyd_error_details,
        )
        self._keyd_error_details_button.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._keyd_error_details_button.grid_remove()
        self._keyd_error_details_label = self._widget_class(
            "Label",
            ttk.Label,
        )(
            self._keyd_alert_error_frame,
            textvariable=self._keyd_alert_error_details_var,
            justify="left",
            wraplength=640,
        )
        self._keyd_error_details_label.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self._keyd_error_details_label.grid_remove()

        self._validation_var = tk.StringVar(value="")
        self._widget_class("Label", ttk.Label)(self.frame, textvariable=self._validation_var, justify="left").grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(6, 0),
        )

        self._bind_mousewheel_recursive(self.frame)

    def _clear_keyd_feedback(self) -> None:
        self._keyd_alert_success_var.set("")
        self._keyd_alert_error_summary_var.set("")
        self._keyd_alert_error_details_var.set("")
        self._keyd_alert_error_frame.grid_remove()
        self._keyd_error_details_button.grid_remove()
        self._keyd_error_details_label.grid_remove()

    def _apply_keyd_summary_font(self) -> None:
        font = self._keyd_alert_summary_font
        label = getattr(self, "_keyd_alert_summary_label", None)
        if font is None or label is None:
            return
        try:
            label.configure(font=font)
            return
        except Exception:
            pass
        try:
            label["font"] = font
            return
        except Exception:
            self._logger.debug("Unable to apply keyd summary font", exc_info=True)

    def _format_keyd_warning_text(self, alert: KeydAlertViewModel) -> str:
        warnings: list[str] = []
        action_label = "this action"
        privilege_subject = "This action"
        if alert.primary_action is not None and alert.primary_action.label.strip():
            action_label = alert.primary_action.label.strip()
            lower_label = action_label.casefold()
            if "integration" in lower_label:
                privilege_subject = "Integration"
            elif "export" in lower_label:
                privilege_subject = "Export"
            else:
                privilege_subject = action_label
        if alert.show_privilege_warning:
            warnings.append(f"Warning: {privilege_subject} requires elevated privileges (sudo).")
        if alert.show_terminal_warning:
            warnings.append(f"Warning: {action_label} opens a terminal/auth prompt.")
        return "\n".join(warnings)

    def _on_keyd_primary_action(self) -> None:
        if self._keyd_alert_model is None or self._keyd_alert_model.primary_action is None:
            return
        callback = self._keyd_alert_model.primary_action.callback
        try:
            outcome = callback()
        except Exception as exc:
            self._logger.exception("Keyd alert primary action failed")
            self.show_keyd_alert_error(
                "Action failed. See details for troubleshooting output.",
                str(exc),
            )
            return
        self._apply_keyd_action_outcome(outcome)

    def _on_keyd_copy_commands(self) -> None:
        if self._keyd_alert_model is None:
            return
        commands = self._keyd_alert_model.copy_commands.strip()
        if not commands:
            self.show_keyd_alert_error("No commands available to copy.")
            return
        try:
            owner = self.frame.winfo_toplevel() if hasattr(self.frame, "winfo_toplevel") else self.frame
            owner.clipboard_clear()
            owner.clipboard_append(commands)
            self.show_keyd_alert_success("Commands copied to clipboard.")
        except Exception as exc:
            self._logger.debug("Clipboard copy failed", exc_info=exc)
            self.show_keyd_alert_error(
                "Unable to copy commands to clipboard.",
                str(exc),
            )

    def _apply_keyd_action_outcome(self, outcome: KeydAlertActionOutcome | None) -> None:
        if outcome is None:
            self.show_keyd_alert_success("Action completed.")
            return
        if outcome.refreshed_alert is not None:
            self.set_keyd_alert(outcome.refreshed_alert)
        if outcome.error_summary.strip():
            self.show_keyd_alert_error(outcome.error_summary, outcome.error_details)
            return
        if outcome.success_message.strip():
            self.show_keyd_alert_success(outcome.success_message)
            return
        if outcome.refreshed_alert is None:
            self.show_keyd_alert_success("Action completed.")

    def _toggle_keyd_error_details(self) -> None:
        details = self._keyd_alert_error_details_var.get().strip()
        if not details:
            return
        if self._keyd_details_expanded:
            self._keyd_error_details_label.grid_remove()
            self._keyd_alert_details_button_var.set("Show details")
            self._keyd_details_expanded = False
            return
        self._keyd_error_details_label.grid()
        self._keyd_alert_details_button_var.set("Hide details")
        self._keyd_details_expanded = True

    def _remove_row(self, target_row: _RowWidgets) -> None:
        remaining: list[_RowWidgets] = []
        for row in self._row_widgets:
            if row is target_row:
                for widget in row.widgets:
                    if hasattr(widget, "destroy"):
                        widget.destroy()
                continue
            remaining.append(row)
        self._row_widgets = remaining
        self._refresh_row_positions()
        self._refresh_scroll_region()
        self._refresh_all_action_options()
        self._notify_bindings_changed()

    def _on_plugin_value_changed(self, row: _RowWidgets) -> None:
        if self._suppress_var_trace_handlers:
            return
        self._refresh_all_action_options()
        self._notify_bindings_changed()

    def _on_action_value_changed(self, row: _RowWidgets) -> None:
        if self._suppress_var_trace_handlers:
            return
        selected_label = row.action_display_var.get().strip()
        selected_action_id = row.action_display_to_id.get(selected_label, "")
        if row.action_id_var.get().strip() != selected_action_id:
            row.action_id_var.set(selected_action_id)
        self._refresh_all_action_options()
        self._notify_bindings_changed()

    def _refresh_all_action_options(self) -> None:
        if self._refreshing_action_options:
            return
        self._refreshing_action_options = True
        self._suppress_var_trace_handlers = True
        try:
            for row in self._row_widgets:
                self._refresh_row_action_options(row)
        finally:
            self._suppress_var_trace_handlers = False
            self._refreshing_action_options = False

    def _refresh_row_action_options(self, row: _RowWidgets) -> None:
        filtered_options = self._filtered_action_options(row)
        row.action_display_to_id = {display: action_id for display, action_id in filtered_options}
        row.action_label_by_id = {action_id: display for display, action_id in filtered_options}
        filtered_values = tuple(display for display, _action_id in filtered_options)
        self._set_combobox_values(row.action_combo, filtered_values)
        current_action_id = row.action_id_var.get().strip()
        if current_action_id and current_action_id not in row.action_label_by_id:
            row.action_id_var.set("")
            if row.action_display_var.get().strip():
                row.action_display_var.set("")
            row.payload_var.set("")
            return
        current_display = row.action_display_var.get().strip()
        desired_display = row.action_label_by_id.get(current_action_id, "")
        if current_display != desired_display:
            row.action_display_var.set(desired_display)

    def _filtered_action_options(self, row: _RowWidgets) -> tuple[tuple[str, str], ...]:
        plugin = row.plugin_var.get().strip()
        if not plugin:
            return ()
        plugin_key = plugin.casefold()
        assigned_single_actions = self._assigned_single_actions_from_other_enabled_rows(row)
        label_counts: dict[str, int] = {}
        values: list[tuple[str, str]] = []
        for option in self._state.action_options:
            option_plugin = option.plugin.strip()
            if not option_plugin or option_plugin.casefold() != plugin_key:
                continue
            option_cardinality = normalize_action_cardinality(
                getattr(option, "cardinality", ACTION_CARDINALITY_SINGLE)
            )
            if option_cardinality == ACTION_CARDINALITY_SINGLE and option.action_id in assigned_single_actions:
                continue
            base_label = option.label.strip() or option.action_id
            label_count = label_counts.get(base_label, 0) + 1
            label_counts[base_label] = label_count
            label = base_label if label_count == 1 else f"{base_label} ({label_count})"
            values.append((label, option.action_id))
        return tuple(values)

    def _assigned_single_actions_from_other_enabled_rows(self, target_row: _RowWidgets) -> set[str]:
        option_by_id = {option.action_id: option for option in self._state.action_options}
        assigned: set[str] = set()
        for row in self._row_widgets:
            if row is target_row:
                continue
            if not _enabled_from_label(str(row.enabled_var.get())):
                continue
            action_id = row.action_id_var.get().strip()
            if not action_id:
                continue
            option = option_by_id.get(action_id)
            option_cardinality = normalize_action_cardinality(
                getattr(option, "cardinality", ACTION_CARDINALITY_SINGLE) if option is not None else ACTION_CARDINALITY_SINGLE
            )
            if option_cardinality != ACTION_CARDINALITY_SINGLE:
                continue
            assigned.add(action_id)
        return assigned

    def _set_combobox_values(self, combo: object, values: tuple[str, ...]) -> None:
        if hasattr(combo, "configure"):
            combo.configure(values=values)
            return
        if hasattr(combo, "__setitem__"):
            combo["values"] = values

    def _refresh_row_positions(self) -> None:
        for index, row in enumerate(self._row_widgets):
            for column, widget in enumerate(row.widgets):
                if hasattr(widget, "grid_configure"):
                    widget.grid_configure(row=index + 1, column=column)

    def _on_canvas_configure(self, event: object) -> None:
        if tk is None:
            return
        self._canvas.itemconfigure(self._canvas_window, width=event.width)
        self._refresh_scroll_region()

    def _refresh_scroll_region(self) -> None:
        if tk is None:
            return
        bbox = self._canvas.bbox("all")
        self._canvas.configure(scrollregion=bbox)
        scrollable = False
        if bbox is not None:
            content_height = int(bbox[3] - bbox[1])
            viewport_height = int(self._canvas.winfo_height() or 0)
            if viewport_height <= 0:
                viewport_height = int(self._canvas.cget("height") or 0)
            scrollable = content_height > max(0, viewport_height)
        self._set_rows_scrollable(scrollable)

    def _set_rows_scrollable(self, scrollable: bool) -> None:
        self._rows_scrollable = bool(scrollable)
        scrollbar = self._rows_scrollbar
        if scrollbar is not None:
            if self._rows_scrollable:
                scrollbar.grid()
            else:
                scrollbar.grid_remove()
        body = self._rows_body
        if body is not None:
            minsize = self._rows_scrollbar_width if self._rows_scrollable else 0
            try:
                body.columnconfigure(1, minsize=minsize)
            except Exception:
                pass

    def _bind_mousewheel_recursive(self, widget: object) -> None:
        if not hasattr(widget, "bind"):
            return
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)
        widget.bind("<Button-5>", self._on_mousewheel)
        if not hasattr(widget, "winfo_children"):
            return
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    def _capture_hotkey(self, event: object, hotkey_var: object, widget: object) -> str | None:
        keysym = str(getattr(event, "keysym", "") or "")
        if _track_modifier_press(keysym, self._active_modifier_tokens, widget):
            return "break"
        state = int(getattr(event, "state", 0))
        char = str(getattr(event, "char", "") or "")
        active_tokens = tuple(self._active_modifier_tokens.get(str(widget), {}).values())
        if self._should_allow_hotkey_text_editing(keysym=keysym, char=char, state=state, active_tokens=active_tokens):
            return None
        captured, resolved_groups, ambiguous_groups = _hotkey_from_parts_with_details(
            state=state,
            keysym=keysym,
            char=char,
            active_modifiers=active_tokens,
            supports_side_specific_modifiers=self._supports_side_specific_modifiers,
            is_windows=_is_windows_platform(),
        )
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(
                "Hotkey capture resolved: keysym=%s char=%r state=0x%X active_modifiers=%s resolved_groups=%s ambiguous_groups=%s captured=%s",
                keysym,
                char,
                state,
                active_tokens,
                resolved_groups,
                ambiguous_groups,
                captured,
            )
        if captured is not None and ambiguous_groups:
            self._logger.warning(
                "Ambiguous Windows modifier state during hotkey capture: groups=%s keysym=%s state=0x%X",
                ",".join(ambiguous_groups),
                keysym,
                state,
            )
        if captured is None:
            if keysym in _MODIFIER_KEYSYMS:
                return "break"
            return None
        hotkey_var.set(captured)
        return "break"

    def _release_modifier(self, event: object, widget: object) -> str | None:
        keysym = str(getattr(event, "keysym", "") or "")
        _track_modifier_release(keysym, self._active_modifier_tokens, widget)
        return None

    def _clear_modifiers(self, widget: object) -> None:
        self._active_modifier_tokens.pop(str(widget), None)

    def _should_allow_hotkey_text_editing(
        self,
        *,
        keysym: str,
        char: str,
        state: int,
        active_tokens: tuple[str, ...],
    ) -> bool:
        if active_tokens:
            return False
        effective_modifier_state = state & _MODIFIER_STATE_MASK
        # Allow typed/pasted editing when only Shift is pressed so users can
        # enter '+' and mixed-case text for manual hotkey edits.
        if effective_modifier_state and effective_modifier_state != _SHIFT_MASK:
            return False
        if keysym in _EDITING_KEYSYMS:
            return True
        if len(char) == 1 and char.isprintable():
            return True
        return False

    def _on_hotkey_commit(self, widget: object) -> str | None:
        self._clear_modifiers(widget)
        self._notify_bindings_changed()
        return None

    def _notify_bindings_changed(self) -> None:
        callback = getattr(self, "_on_bindings_changed", None)
        if callback is None:
            return
        try:
            callback()
        except Exception:
            self._logger.debug("Failed to process settings change callback", exc_info=True)

    def _on_mousewheel(self, event: object) -> str | None:
        if tk is None:
            return None
        if not self._rows_scrollable:
            return "break"

        direction = 0
        event_num = getattr(event, "num", None)
        if event_num == 4:
            direction = -1
        elif event_num == 5:
            direction = 1
        else:
            delta = int(getattr(event, "delta", 0))
            if delta == 0:
                return None
            direction = -1 if delta > 0 else 1

        self._canvas.yview_scroll(direction, "units")
        return "break"

    def _widget_class(self, name: str, fallback: object) -> object:
        if self._notebook_widgets is None:
            return fallback
        return getattr(self._notebook_widgets, name, fallback)


def hotkey_from_event(
    event: object,
    *,
    active_modifiers: tuple[str, ...] = (),
    supports_side_specific_modifiers: bool = True,
) -> str | None:
    """Convert a Tk key event into a canonical hotkey string."""
    state = int(getattr(event, "state", 0))
    keysym = str(getattr(event, "keysym", "") or "")
    char = str(getattr(event, "char", "") or "")
    return hotkey_from_parts(
        state=state,
        keysym=keysym,
        char=char,
        active_modifiers=active_modifiers,
        supports_side_specific_modifiers=supports_side_specific_modifiers,
    )


def hotkey_from_parts(
    *,
    state: int,
    keysym: str,
    char: str,
    active_modifiers: tuple[str, ...] = (),
    supports_side_specific_modifiers: bool = True,
) -> str | None:
    """Convert key event parts into pretty hotkey text."""
    captured, _resolved_groups, _ambiguous_groups = _hotkey_from_parts_with_details(
        state=state,
        keysym=keysym,
        char=char,
        active_modifiers=active_modifiers,
        supports_side_specific_modifiers=supports_side_specific_modifiers,
        is_windows=_is_windows_platform(),
    )
    return captured


def _hotkey_from_parts_with_details(
    *,
    state: int,
    keysym: str,
    char: str,
    active_modifiers: tuple[str, ...] = (),
    supports_side_specific_modifiers: bool = True,
    is_windows: bool,
) -> tuple[str | None, dict[str, str], tuple[str, ...]]:
    """Return a captured hotkey plus modifier-resolution details."""
    if keysym in _MODIFIER_KEYSYMS:
        return None, {}, ()

    key = _normalize_hotkey_key(keysym=keysym, char=char)
    if key is None:
        return None, {}, ()

    grouped, ambiguous_groups = _resolve_modifier_groups(
        state=state,
        active_modifiers=active_modifiers,
        supports_side_specific_modifiers=supports_side_specific_modifiers,
        is_windows=is_windows,
    )

    ordered = tuple(token for token in CANONICAL_MODIFIER_ORDER if token in grouped.values())
    return pretty_hotkey_text(modifiers=ordered, key=key), grouped, ambiguous_groups


def _resolve_modifier_groups(
    *,
    state: int,
    active_modifiers: tuple[str, ...],
    supports_side_specific_modifiers: bool,
    is_windows: bool,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Resolve final modifier tokens and any ambiguous state-only groups."""
    grouped = _group_modifier_tokens(active_modifiers)
    ambiguous_groups: list[str] = []

    for group, mask in _MODIFIER_STATE_FLAGS:
        if not (state & mask):
            continue
        if group in grouped:
            continue
        if supports_side_specific_modifiers and is_windows:
            ambiguous_groups.append(group)
            continue
        grouped[group] = _default_modifier_token(group, supports_side_specific_modifiers)

    if not supports_side_specific_modifiers:
        grouped = {group: group for group in grouped}

    return grouped, tuple(ambiguous_groups)


def _is_windows_platform() -> bool:
    return sys.platform.startswith("win")


def _normalize_hotkey_key(*, keysym: str, char: str) -> str | None:
    normalized_keysym = keysym.strip()
    if not normalized_keysym:
        return None

    shifted_from_char = _SHIFTED_SYMBOL_TO_BASE_KEY.get(char)
    if shifted_from_char is not None:
        return normalize_key_token(shifted_from_char)

    shifted_from_keysym = _SHIFTED_SYMBOL_TO_BASE_KEY.get(normalized_keysym.lower())
    if shifted_from_keysym is not None:
        return normalize_key_token(shifted_from_keysym)

    if len(char) == 1 and char.isalnum():
        return normalize_key_token(char)
    if len(normalized_keysym) == 1 and normalized_keysym.isalnum():
        return normalize_key_token(normalized_keysym)

    upper = normalized_keysym.upper()
    if upper.startswith("F") and upper[1:].isdigit():
        fn_number = int(upper[1:])
        if 1 <= fn_number <= 24:
            return normalize_key_token(upper)

    special = {
        "SPACE": "space",
        "TAB": "tab",
        "RETURN": "enter",
        "KP_ENTER": "enter",
        "ESCAPE": "esc",
    }
    token = special.get(upper)
    if token is None:
        return None
    return normalize_key_token(token)


def _track_modifier_press(keysym: str, store: dict[str, dict[str, str]], widget: object) -> bool:
    token_info = _MODIFIER_KEYSYM_TO_TOKEN.get(keysym)
    if token_info is None:
        return False
    group, token = token_info
    widget_key = str(widget)
    by_group = store.setdefault(widget_key, {})
    by_group[group] = token
    return True


def _track_modifier_release(keysym: str, store: dict[str, dict[str, str]], widget: object) -> bool:
    token_info = _MODIFIER_KEYSYM_TO_TOKEN.get(keysym)
    if token_info is None:
        return False
    group, _token = token_info
    widget_key = str(widget)
    by_group = store.get(widget_key)
    if by_group is None:
        return False
    by_group.pop(group, None)
    if not by_group:
        store.pop(widget_key, None)
    return True


def _group_modifier_tokens(tokens: tuple[str, ...]) -> dict[str, str]:
    grouped: dict[str, str] = {}
    for token in tokens:
        if token == "ctrl" or token.startswith("ctrl_"):
            grouped["ctrl"] = token
        elif token == "alt" or token.startswith("alt_"):
            grouped["alt"] = token
        elif token == "shift" or token.startswith("shift_"):
            grouped["shift"] = token
        elif token == "win" or token.startswith("win_"):
            grouped["win"] = token
    return grouped


def _default_modifier_token(group: str, supports_side_specific_modifiers: bool) -> str:
    if not supports_side_specific_modifiers:
        return group
    defaults = {
        "ctrl": "ctrl_l",
        "alt": "alt_l",
        "shift": "shift_l",
        "win": "win_l",
    }
    return defaults[group]


def build_settings_panel(
    parent: object,
    state: SettingsState,
    *,
    logger: logging.Logger,
    notebook_widgets: object | None = None,
    supports_side_specific_modifiers: bool = True,
    on_bindings_changed: Callable[[], None] | None = None,
) -> Optional[SettingsPanel]:
    if tk is None or ttk is None:
        logger.warning("tkinter is unavailable; settings UI cannot be created")
        return None
    try:
        return SettingsPanel(
            parent,
            state,
            logger=logger,
            notebook_widgets=notebook_widgets,
            supports_side_specific_modifiers=supports_side_specific_modifiers,
            on_bindings_changed=on_bindings_changed,
        )
    except Exception:
        logger.exception("Failed to build settings panel")
        return None
