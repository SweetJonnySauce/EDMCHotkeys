"""EDMC plugin entrypoint for EDMC-Hotkeys."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from typing import Optional

from edmc_hotkeys.bindings import BindingRecord, BindingsDocument, default_document
from edmc_hotkeys.plugin import Binding, HotkeyPlugin
from edmc_hotkeys.registry import Action
from edmc_hotkeys.settings_state import SettingsState
from edmc_hotkeys.settings_ui import SettingsPanel, build_settings_panel
from edmc_hotkeys.storage import BindingsStore


def _build_plugin_logger(plugin_name: str) -> logging.Logger:
    try:
        from config import appcmdname, appname  # type: ignore

        base_logger_name = appcmdname if os.getenv("EDMC_NO_UI") else appname
        return logging.getLogger(f"{base_logger_name}.{plugin_name}")
    except Exception:
        return logging.getLogger(plugin_name)


plugin_name = "EDMC-Hotkeys"
logger = _build_plugin_logger(plugin_name)
_plugin: Optional[HotkeyPlugin] = None
_bindings_store: Optional[BindingsStore] = None
_bindings_document: Optional[BindingsDocument] = None
_settings_panel: Optional[SettingsPanel] = None


def plugin_start3(plugin_dir: str) -> str:
    """EDMC plugin start hook."""
    global _plugin, _bindings_store, _bindings_document
    plugin_path = Path(plugin_dir)
    _plugin = HotkeyPlugin(plugin_dir=plugin_path, logger=logger)

    _bindings_store = BindingsStore(plugin_path / "bindings.json", logger=logger)
    _bindings_document = _bindings_store.load_or_create()
    bindings = _bindings_from_document(_bindings_document)
    logger.info("Loaded %d active bindings for profile '%s'", len(bindings), _bindings_document.active_profile)
    if not _plugin.replace_bindings(bindings):
        logger.warning("Some bindings failed to register during startup")
    _plugin.start()
    return plugin_name


def plugin_stop() -> None:
    """EDMC plugin stop hook."""
    global _plugin, _settings_panel
    if _plugin is not None:
        _plugin.stop()
    _plugin = None
    _settings_panel = None


def register_action(action: Action) -> bool:
    plugin = _require_started()
    if plugin is None:
        return False
    return plugin.register_action(action)


def list_actions() -> list[Action]:
    plugin = _require_started()
    if plugin is None:
        return []
    return plugin.list_actions()


def get_action(action_id: str) -> Optional[Action]:
    plugin = _require_started()
    if plugin is None:
        return None
    return plugin.get_action(action_id)


def invoke_action(action_id: str, payload: Optional[dict] = None, source: str = "hotkey") -> bool:
    plugin = _require_started()
    if plugin is None:
        return False
    return plugin.invoke_action(action_id=action_id, payload=payload, source=source)


def invoke_bound_action(binding: Binding, source: str = "hotkey") -> bool:
    plugin = _require_started()
    if plugin is None:
        return False
    return plugin.invoke_binding(binding=binding, source=source)


def journal_entry(
    cmdr: str,
    is_beta: bool,
    system: str,
    station: str,
    entry: dict,
    state: dict,
) -> Optional[str]:
    del cmdr, is_beta, system, station, entry, state
    _pump_dispatch_queue()
    return None


def dashboard_entry(cmdr: str, is_beta: bool, entry: dict) -> None:
    del cmdr, is_beta, entry
    _pump_dispatch_queue()


def plugin_prefs(parent: object, cmdr: str, is_beta: bool) -> Optional[object]:
    del cmdr, is_beta
    global _settings_panel
    plugin = _require_started()
    if plugin is None:
        return None
    notebook_widgets = _resolve_notebook_widgets(parent)
    container = _create_notebook_container(parent, notebook_widgets)
    ui_parent = container if container is not None else parent
    document = _bindings_document or default_document()
    state = SettingsState.from_document(document=document, actions=plugin.list_actions())
    _settings_panel = build_settings_panel(
        ui_parent,
        state,
        logger=logger,
        notebook_widgets=notebook_widgets,
    )
    if _settings_panel is None:
        return None
    if container is not None and _settings_panel.frame is not container:
        _settings_panel.frame.grid(row=0, column=0, sticky="nsew")
    frame = container if container is not None else _settings_panel.frame
    logger.debug(
        "plugin_prefs returning frame type: %s (module=%s)",
        type(frame).__name__,
        type(frame).__module__,
    )
    return frame


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    del cmdr, is_beta
    global _bindings_document
    plugin = _require_started()
    if plugin is None or _settings_panel is None:
        return
    if _bindings_store is None:
        logger.warning("Bindings store is unavailable; prefs change ignored")
        return

    current_document = _bindings_document or default_document()
    state = SettingsState(
        document=current_document,
        action_options=SettingsState.from_document(
            document=current_document,
            actions=plugin.list_actions(),
        ).action_options,
        rows=_settings_panel.get_rows(),
    )
    issues = state.validate()
    _settings_panel.set_validation_issues(issues)
    has_errors = any(issue.level == "error" for issue in issues)
    if has_errors:
        logger.warning("Bindings settings contain validation errors; changes were not saved")
        return

    new_document = state.to_document()
    _bindings_store.save(new_document)
    _bindings_document = new_document
    if not plugin.replace_bindings(_bindings_from_document(new_document)):
        logger.warning("Some bindings failed to register after settings save")


def _require_started() -> Optional[HotkeyPlugin]:
    if _plugin is None:
        logger.warning("Plugin is not started")
        return None
    return _plugin


def _pump_dispatch_queue() -> int:
    plugin = _require_started()
    if plugin is None:
        return 0
    return plugin.pump_main_thread_dispatch()


def _bindings_from_document(document: BindingsDocument) -> list[Binding]:
    active_profile_bindings = document.profiles.get(document.active_profile, [])
    return [_binding_from_record(binding) for binding in active_profile_bindings]


def _binding_from_record(record: BindingRecord) -> Binding:
    return Binding(
        id=record.id,
        hotkey=record.hotkey,
        action_id=record.action_id,
        payload=record.payload,
        enabled=record.enabled,
    )


def _resolve_notebook_widgets(parent: object) -> object | None:
    parent_module_name = getattr(parent.__class__, "__module__", "")
    if parent_module_name:
        parent_module = sys.modules.get(parent_module_name)
        if parent_module is not None and hasattr(parent_module, "Frame"):
            return parent_module

    preloaded = sys.modules.get("myNotebook")
    if preloaded is not None and hasattr(preloaded, "Frame"):
        return preloaded

    try:
        import myNotebook as nb  # type: ignore

        return nb
    except Exception as exc:
        logger.warning("Unable to import myNotebook; falling back to ttk widgets")
        logger.debug("myNotebook import failure", exc_info=exc)
        return None


def _create_notebook_container(parent: object, notebook_widgets: object | None) -> object | None:
    if notebook_widgets is None:
        return None
    frame_class = getattr(notebook_widgets, "Frame", None)
    if frame_class is None:
        return None
    try:
        container = frame_class(parent)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)
        return container
    except Exception as exc:
        logger.warning("Unable to create myNotebook frame container; using parent directly")
        logger.debug("myNotebook container creation failure", exc_info=exc)
        return None
