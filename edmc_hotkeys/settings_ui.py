"""Settings UI widgets for editing bindings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .settings_state import BindingRow, SettingsState, ValidationIssue

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - exercised only in EDMC runtime without tkinter
    tk = None
    ttk = None


@dataclass
class _RowWidgets:
    row_id_var: object
    hotkey_var: object
    plugin_var: object
    action_var: object
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
    ) -> None:
        if tk is None or ttk is None:
            raise RuntimeError("tkinter is unavailable")
        self._logger = logger
        self._state = state
        self._notebook_widgets = notebook_widgets
        self.frame = self._widget_class("Frame", ttk.Frame)(parent)
        self._row_widgets: list[_RowWidgets] = []

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

        row_id_var = tk.StringVar(value=row.id)
        hotkey_var = tk.StringVar(value=row.hotkey)
        plugin_var = tk.StringVar(value=row.plugin)
        action_var = tk.StringVar(value=row.action_id)
        enabled_var = tk.BooleanVar(value=row.enabled)

        self._widget_class("Entry", ttk.Entry)(row_frame, textvariable=row_id_var, width=16).grid(
            row=0,
            column=0,
            padx=2,
            sticky="ew",
        )
        self._widget_class("Entry", ttk.Entry)(row_frame, textvariable=hotkey_var, width=18).grid(
            row=0,
            column=1,
            padx=2,
            sticky="ew",
        )
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
        self._widget_class("Checkbutton", ttk.Checkbutton)(row_frame, variable=enabled_var).grid(
            row=0,
            column=4,
            padx=2,
        )
        self._widget_class("Button", ttk.Button)(
            row_frame,
            text="Remove",
            command=lambda frame=row_frame: self._remove_row(frame),
            width=8,
        ).grid(row=0, column=5, padx=2)

        self._row_widgets.append(
            _RowWidgets(
                row_id_var=row_id_var,
                hotkey_var=hotkey_var,
                plugin_var=plugin_var,
                action_var=action_var,
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
                    payload=None,
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
        headers = ["Binding ID", "Hotkey", "Plugin", "Action", "Enabled", ""]
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

    def _widget_class(self, name: str, fallback: object) -> object:
        if self._notebook_widgets is None:
            return fallback
        return getattr(self._notebook_widgets, name, fallback)


def build_settings_panel(
    parent: object,
    state: SettingsState,
    *,
    logger: logging.Logger,
    notebook_widgets: object | None = None,
) -> Optional[SettingsPanel]:
    if tk is None or ttk is None:
        logger.warning("tkinter is unavailable; settings UI cannot be created")
        return None
    try:
        return SettingsPanel(parent, state, logger=logger, notebook_widgets=notebook_widgets)
    except Exception:
        logger.exception("Failed to build settings panel")
        return None
