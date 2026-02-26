"""Settings UI widgets for editing bindings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .hotkey import CANONICAL_MODIFIER_ORDER, normalize_key_token, pretty_hotkey_text
from .settings_state import BindingRow, SettingsState, ValidationIssue

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - exercised only in EDMC runtime without tkinter
    tk = None
    ttk = None


_SHIFT_MASK = 0x0001
_CONTROL_MASK = 0x0004
_ALT_MASK = 0x0008
_SUPER_MASK = 0x0040
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


@dataclass
class _RowWidgets:
    row_id_var: object
    hotkey_var: object
    plugin_var: object
    action_var: object
    payload_var: object
    payload: dict | None
    enabled_var: object
    frame: object


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
    ) -> None:
        if tk is None or ttk is None:
            raise RuntimeError("tkinter is unavailable")
        self._logger = logger
        self._state = state
        self._notebook_widgets = notebook_widgets
        self._supports_side_specific_modifiers = supports_side_specific_modifiers
        self.frame = self._widget_class("Frame", ttk.Frame)(parent)
        self._row_widgets: list[_RowWidgets] = []
        self._active_modifier_tokens: dict[str, dict[str, str]] = {}

        self._action_values = [option.action_id for option in state.action_options]
        self._plugin_values = sorted({option.plugin for option in state.action_options if option.plugin})

        self._build_layout()
        for row in state.rows:
            self.add_row(row)

    def add_row(self, row: BindingRow) -> None:
        if tk is None or ttk is None:
            return
        row_frame = self._widget_class("Frame", ttk.Frame)(self._rows_inner)
        row_frame.grid(row=len(self._row_widgets), column=0, sticky="ew", pady=1)
        row_frame.columnconfigure(1, weight=1)
        row_frame.columnconfigure(3, weight=1)
        row_frame.columnconfigure(4, weight=1)

        row_id_var = tk.StringVar(value=row.id)
        hotkey_var = tk.StringVar(value=row.hotkey)
        plugin_var = tk.StringVar(value=row.plugin)
        action_var = tk.StringVar(value=row.action_id)
        payload_var = tk.StringVar(value=row.payload_text)
        enabled_var = tk.BooleanVar(value=row.enabled)

        self._widget_class("Entry", ttk.Entry)(row_frame, textvariable=row_id_var, width=16).grid(
            row=0,
            column=0,
            padx=2,
            sticky="ew",
        )
        hotkey_entry = self._widget_class("Entry", ttk.Entry)(row_frame, textvariable=hotkey_var, width=18)
        hotkey_entry.grid(
            row=0,
            column=1,
            padx=2,
            sticky="ew",
        )
        hotkey_entry.bind("<KeyPress>", lambda event, var=hotkey_var, widget=hotkey_entry: self._capture_hotkey(event, var, widget))
        hotkey_entry.bind("<KeyRelease>", lambda event, widget=hotkey_entry: self._release_modifier(event, widget))
        hotkey_entry.bind("<FocusOut>", lambda _event, widget=hotkey_entry: self._clear_modifiers(widget))
        self._widget_class("Combobox", ttk.Combobox)(
            row_frame,
            textvariable=plugin_var,
            values=self._plugin_values,
            state="readonly",
            width=16,
        ).grid(row=0, column=2, padx=2, sticky="ew")
        self._widget_class("Combobox", ttk.Combobox)(
            row_frame,
            textvariable=action_var,
            values=self._action_values,
            state="readonly",
            width=28,
        ).grid(row=0, column=3, padx=2, sticky="ew")
        self._widget_class("Entry", ttk.Entry)(row_frame, textvariable=payload_var, width=24).grid(
            row=0,
            column=4,
            padx=2,
            sticky="ew",
        )
        self._widget_class("Checkbutton", ttk.Checkbutton)(row_frame, variable=enabled_var).grid(
            row=0,
            column=5,
            padx=2,
        )
        self._widget_class("Button", ttk.Button)(
            row_frame,
            text="Remove",
            command=lambda frame=row_frame: self._remove_row(frame),
            width=8,
        ).grid(row=0, column=6, padx=2)
        self._bind_mousewheel_recursive(row_frame)

        self._row_widgets.append(
            _RowWidgets(
                row_id_var=row_id_var,
                hotkey_var=hotkey_var,
                plugin_var=plugin_var,
                action_var=action_var,
                payload_var=payload_var,
                payload=row.payload,
                enabled_var=enabled_var,
                frame=row_frame,
            )
        )
        self._refresh_row_positions()
        self._refresh_scroll_region()

    def get_rows(self) -> list[BindingRow]:
        rows: list[BindingRow] = []
        for row in self._row_widgets:
            rows.append(
                BindingRow(
                    id=row.row_id_var.get().strip(),
                    hotkey=row.hotkey_var.get().strip(),
                    plugin=row.plugin_var.get().strip(),
                    action_id=row.action_var.get().strip(),
                    payload=row.payload,
                    payload_text=row.payload_var.get().strip(),
                    enabled=bool(row.enabled_var.get()),
                )
            )
        return rows

    def set_validation_issues(self, issues: list[ValidationIssue]) -> None:
        if tk is None:
            return
        if not issues:
            self._validation_var.set("No validation issues.")
            return
        lines = [f"[{issue.level}] {issue.row_id}.{issue.field}: {issue.message}" for issue in issues]
        self._validation_var.set("\n".join(lines))

    def _build_layout(self) -> None:
        if tk is None or ttk is None:
            return

        self.frame.columnconfigure(0, weight=1)
        header = self._widget_class("Frame", ttk.Frame)(self.frame)
        header.grid(row=0, column=0, sticky="ew")
        headers = ["Binding ID", "Hotkey", "Plugin", "Action", "Payload", "Enabled", ""]
        for index, label in enumerate(headers):
            self._widget_class("Label", ttk.Label)(header, text=label).grid(row=0, column=index, padx=2, sticky="w")

        body = self._widget_class("Frame", ttk.Frame)(self.frame)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(body, borderwidth=0, highlightthickness=0, height=200)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = self._widget_class("Scrollbar", ttk.Scrollbar)(
            body,
            orient="vertical",
            command=self._canvas.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=scrollbar.set)

        self._rows_inner = self._widget_class("Frame", ttk.Frame)(self._canvas)
        self._rows_inner.columnconfigure(0, weight=1)
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

        self._validation_var = tk.StringVar(value="")
        self._widget_class("Label", ttk.Label)(self.frame, textvariable=self._validation_var, justify="left").grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(6, 0),
        )

        self._bind_mousewheel_recursive(self.frame)

    def _remove_row(self, row_frame: object) -> None:
        remaining: list[_RowWidgets] = []
        for row in self._row_widgets:
            if row.frame is row_frame:
                row.frame.destroy()
                continue
            remaining.append(row)
        self._row_widgets = remaining
        self._refresh_row_positions()
        self._refresh_scroll_region()

    def _refresh_row_positions(self) -> None:
        for index, row in enumerate(self._row_widgets):
            row.frame.grid_configure(row=index)

    def _on_canvas_configure(self, event: object) -> None:
        if tk is None:
            return
        self._canvas.itemconfigure(self._canvas_window, width=event.width)

    def _refresh_scroll_region(self) -> None:
        if tk is None:
            return
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

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
        active_tokens = tuple(self._active_modifier_tokens.get(str(widget), {}).values())
        captured = hotkey_from_event(
            event,
            active_modifiers=active_tokens,
            supports_side_specific_modifiers=self._supports_side_specific_modifiers,
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

    def _on_mousewheel(self, event: object) -> str | None:
        if tk is None:
            return None

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
    if keysym in _MODIFIER_KEYSYMS:
        return None

    key = _normalize_hotkey_key(keysym=keysym, char=char)
    if key is None:
        return None

    grouped = _group_modifier_tokens(active_modifiers)
    if state & _CONTROL_MASK:
        grouped.setdefault("ctrl", _default_modifier_token("ctrl", supports_side_specific_modifiers))
    if state & _ALT_MASK:
        grouped.setdefault("alt", _default_modifier_token("alt", supports_side_specific_modifiers))
    if state & _SHIFT_MASK:
        grouped.setdefault("shift", _default_modifier_token("shift", supports_side_specific_modifiers))
    if state & _SUPER_MASK:
        grouped.setdefault("win", _default_modifier_token("win", supports_side_specific_modifiers))

    if not supports_side_specific_modifiers:
        grouped = {group: group for group in grouped}

    ordered = tuple(token for token in CANONICAL_MODIFIER_ORDER if token in grouped.values())
    return pretty_hotkey_text(modifiers=ordered, key=key)


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
        )
    except Exception:
        logger.exception("Failed to build settings panel")
        return None
