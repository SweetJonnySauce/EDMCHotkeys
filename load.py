"""EDMC plugin entrypoint for EDMC-Hotkeys."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from typing import Optional

from edmc_hotkeys.bindings import BindingRecord, BindingsDocument, default_document
from edmc_hotkeys.hotkey import canonical_hotkey_text
from edmc_hotkeys.plugin import Binding, HotkeyPlugin
from edmc_hotkeys.registry import Action
from edmc_hotkeys.settings_state import SettingsState, ValidationIssue
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
_DISPATCH_PUMP_INTERVAL_MS = 50
_dispatch_pump_owner: Optional[object] = None
_dispatch_pump_after_id: Optional[object] = None
_prefs_apply_guard_installed = False
_BACKEND_MODE_ENV = "EDMC_HOTKEYS_BACKEND_MODE"
_BACKEND_MODE_CONFIG_KEY = "edmc_hotkeys_backend_mode"
_VALID_BACKEND_MODES = {"auto", "wayland_portal", "wayland_gnome_bridge", "x11"}


def plugin_start3(plugin_dir: str) -> str:
    """EDMC plugin start hook."""
    global _plugin, _bindings_store, _bindings_document
    plugin_path = Path(plugin_dir)
    selected_backend_mode = _resolve_backend_mode()
    _plugin = HotkeyPlugin(plugin_dir=plugin_path, logger=logger, backend_mode=selected_backend_mode)
    _install_prefs_apply_guard()

    _bindings_store = BindingsStore(plugin_path / "bindings.json", logger=logger)
    loaded_document = _bindings_store.load_or_create()
    _bindings_document, disable_reasons = _auto_disable_unsupported_bindings(loaded_document, _plugin)
    if _bindings_document != loaded_document:
        _bindings_store.save(_bindings_document)
    if disable_reasons:
        logger.info("Capability policy auto-disabled %d binding(s) for active profile", len(disable_reasons))
    for reason in disable_reasons:
        logger.info(reason)

    bindings = _bindings_from_document(_bindings_document)
    logger.info("Loaded %d active bindings for profile '%s'", len(bindings), _bindings_document.active_profile)
    if not _plugin.replace_bindings(bindings):
        logger.warning("Some bindings failed to register during startup")
    _plugin.start()
    _ensure_dispatch_pump_running()
    return plugin_name


def _resolve_backend_mode() -> str:
    env_mode = os.environ.get(_BACKEND_MODE_ENV, "").strip().lower()
    if env_mode:
        if env_mode in _VALID_BACKEND_MODES:
            return env_mode
        logger.warning("Invalid backend mode in %s='%s'; falling back to auto", _BACKEND_MODE_ENV, env_mode)
        return "auto"

    # Prefer EDMC config when available; keep fallback safe for tests/runtime without config module.
    try:
        import config  # type: ignore
    except Exception:
        return "auto"

    getter = getattr(config, "get_str", None)
    if not callable(getter):
        return "auto"

    configured: str = ""
    try:
        configured = str(getter(_BACKEND_MODE_CONFIG_KEY) or "")
    except TypeError:
        # EDMC version differences may expose default parameter in get_str.
        try:
            configured = str(getter(_BACKEND_MODE_CONFIG_KEY, default="") or "")
        except Exception:
            configured = ""
    except Exception:
        configured = ""

    configured_mode = configured.strip().lower()
    if configured_mode in _VALID_BACKEND_MODES:
        return configured_mode
    if configured_mode:
        logger.warning(
            "Invalid backend mode in config key '%s': '%s'; falling back to auto",
            _BACKEND_MODE_CONFIG_KEY,
            configured_mode,
        )
    return "auto"


def plugin_stop() -> None:
    """EDMC plugin stop hook."""
    global _plugin, _settings_panel
    _stop_dispatch_pump()
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


def list_bindings(plugin_name: str) -> list[Binding]:
    plugin = _require_started()
    if plugin is None:
        return []

    normalized_name = plugin_name.strip()
    if not normalized_name:
        logger.warning("Plugin name is required when listing bindings")
        return []
    target = normalized_name.casefold()

    matching = [
        binding
        for binding in plugin.list_bindings()
        if binding.plugin and binding.plugin.casefold() == target
    ]
    return [
        Binding(
            id=binding.id,
            hotkey=binding.pretty_hotkey,
            action_id=binding.action_id,
            payload=binding.payload,
            enabled=binding.enabled,
            plugin=binding.plugin,
        )
        for binding in matching
    ]


def get_action(action_id: str) -> Optional[Action]:
    plugin = _require_started()
    if plugin is None:
        return None
    return plugin.get_action(action_id)


def invoke_action(
    action_id: str,
    payload: Optional[dict] = None,
    source: str = "hotkey",
    hotkey: Optional[str] = None,
) -> bool:
    plugin = _require_started()
    if plugin is None:
        return False
    return plugin.invoke_action(action_id=action_id, payload=payload, source=source, hotkey=hotkey)


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


def plugin_app(parent: object) -> None:
    _ensure_dispatch_pump_running(parent)
    return None


def plugin_prefs(parent: object, cmdr: str, is_beta: bool) -> Optional[object]:
    del cmdr, is_beta
    global _settings_panel
    plugin = _require_started()
    if plugin is None:
        return None
    _install_prefs_apply_guard()
    _ensure_dispatch_pump_running(parent)
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
        supports_side_specific_modifiers=plugin.backend_capabilities().supports_side_specific_modifiers,
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
    state = _settings_state_from_panel(
        plugin=plugin,
        panel=_settings_panel,
        current_document=current_document,
    )
    issues = state.validate()
    _settings_panel.set_validation_issues(issues)
    has_errors = any(issue.level == "error" for issue in issues)
    if has_errors:
        _show_validation_error_dialog(issues)
        logger.warning("Bindings settings contain validation errors; changes were not saved")
        return

    new_document = state.to_document()
    normalized_document, disable_reasons = _auto_disable_unsupported_bindings(new_document, plugin)
    if disable_reasons:
        logger.info("Capability policy auto-disabled %d binding(s) for active profile", len(disable_reasons))
    for reason in disable_reasons:
        logger.info(reason)

    _bindings_store.save(normalized_document)
    _bindings_document = normalized_document
    if not plugin.replace_bindings(_bindings_from_document(normalized_document)):
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
    hotkey = canonical_hotkey_text(modifiers=record.modifiers, key=record.key)
    if hotkey is None:
        hotkey = record.key
    return Binding(
        id=record.id,
        hotkey=hotkey,
        action_id=record.action_id,
        payload=record.payload,
        enabled=record.enabled,
        plugin=record.plugin,
    )


def _auto_disable_unsupported_bindings(
    document: BindingsDocument,
    plugin: HotkeyPlugin,
) -> tuple[BindingsDocument, list[str]]:
    """Apply core capability policy for the active profile.

    This is the single policy gate for capability-driven auto-disable logic.
    Backends should report capabilities, while core decides enable/disable state.
    """
    capabilities = plugin.backend_capabilities()
    if capabilities.supports_side_specific_modifiers:
        return document, []

    active_profile = document.active_profile
    existing = document.profiles.get(active_profile, [])
    updated: list[BindingRecord] = []
    reasons: list[str] = []
    for binding in existing:
        if not binding.enabled or not _binding_requires_side_specific_capabilities(binding):
            updated.append(binding)
            continue
        updated.append(
            BindingRecord(
                id=binding.id,
                plugin=binding.plugin,
                modifiers=binding.modifiers,
                key=binding.key,
                action_id=binding.action_id,
                payload=binding.payload,
                enabled=False,
            )
        )
        pretty_hotkey = _binding_from_record(binding).pretty_hotkey
        reasons.append(
            "Auto-disabled binding '%s' (%s): backend '%s' does not support side-specific modifiers"
            % (binding.id, pretty_hotkey, plugin.backend_name())
        )

    if not reasons:
        return document, []
    profiles = dict(document.profiles)
    profiles[active_profile] = updated
    return (
        BindingsDocument(
            version=document.version,
            active_profile=document.active_profile,
            profiles=profiles,
        ),
        reasons,
    )


def _binding_requires_side_specific_capabilities(record: BindingRecord) -> bool:
    return any(modifier.endswith("_l") or modifier.endswith("_r") for modifier in record.modifiers)


def _show_validation_error_dialog(issues: list[ValidationIssue]) -> None:
    errors = [issue for issue in issues if getattr(issue, "level", "") == "error"]
    if not errors:
        return
    lines = [f"{issue.row_id}.{issue.field}: {issue.message}" for issue in errors[:8]]
    message = "Bindings were not saved due to validation errors:\n\n" + "\n".join(lines)
    try:
        from tkinter import messagebox

        parent = _settings_panel.frame if _settings_panel is not None else None
        messagebox.showerror("EDMC-Hotkeys", message, parent=parent)
    except Exception as exc:
        logger.warning("Unable to show validation error dialog")
        logger.debug("Validation error dialog failure", exc_info=exc)


def _settings_state_from_panel(
    *,
    plugin: HotkeyPlugin,
    panel: object,
    current_document: BindingsDocument,
) -> SettingsState:
    return SettingsState(
        document=current_document,
        action_options=SettingsState.from_document(
            document=current_document,
            actions=plugin.list_actions(),
        ).action_options,
        rows=panel.get_rows(),
    )


def _install_prefs_apply_guard() -> None:
    global _prefs_apply_guard_installed
    if _prefs_apply_guard_installed:
        return
    try:
        import prefs as edmc_prefs  # type: ignore
    except Exception:
        logger.debug("EDMC prefs module not available yet; apply guard not installed")
        return

    preferences_dialog = getattr(edmc_prefs, "PreferencesDialog", None)
    if preferences_dialog is None or not hasattr(preferences_dialog, "apply"):
        logger.debug("EDMC PreferencesDialog.apply is unavailable; apply guard not installed")
        return

    current_apply = preferences_dialog.apply
    if getattr(current_apply, "_edmc_hotkeys_guard", False):
        _prefs_apply_guard_installed = True
        return

    original_apply = current_apply

    def _guarded_apply(dialog_self: object, *args, **kwargs):
        plugin = _require_started()
        panel = _settings_panel
        if plugin is not None and panel is not None:
            try:
                current_document = _bindings_document or default_document()
                state = _settings_state_from_panel(
                    plugin=plugin,
                    panel=panel,
                    current_document=current_document,
                )
                issues = state.validate()
                panel.set_validation_issues(issues)
                if any(issue.level == "error" for issue in issues):
                    _show_validation_error_dialog(issues)
                    logger.warning("Bindings settings contain validation errors; keeping Settings dialog open")
                    return None
            except Exception:
                logger.exception("EDMC-Hotkeys settings apply guard failed; falling back to EDMC apply")
        return original_apply(dialog_self, *args, **kwargs)

    setattr(_guarded_apply, "_edmc_hotkeys_guard", True)
    preferences_dialog.apply = _guarded_apply
    _prefs_apply_guard_installed = True


def _ensure_dispatch_pump_running(owner: object | None = None) -> None:
    global _dispatch_pump_owner
    if _dispatch_pump_after_id is not None:
        return
    resolved_owner = owner if _supports_after_callbacks(owner) else _resolve_default_tk_root()
    if not _supports_after_callbacks(resolved_owner):
        return
    _dispatch_pump_owner = resolved_owner
    _schedule_dispatch_pump()


def _schedule_dispatch_pump() -> None:
    global _dispatch_pump_after_id
    if not _supports_after_callbacks(_dispatch_pump_owner):
        _dispatch_pump_after_id = None
        return
    try:
        _dispatch_pump_after_id = _dispatch_pump_owner.after(  # type: ignore[attr-defined]
            _DISPATCH_PUMP_INTERVAL_MS,
            _dispatch_pump_tick,
        )
    except Exception as exc:
        _dispatch_pump_after_id = None
        logger.debug("Failed to schedule main-thread dispatch pump", exc_info=exc)


def _dispatch_pump_tick() -> None:
    global _dispatch_pump_after_id
    _dispatch_pump_after_id = None
    _pump_dispatch_queue()
    _schedule_dispatch_pump()


def _stop_dispatch_pump() -> None:
    global _dispatch_pump_owner, _dispatch_pump_after_id
    owner = _dispatch_pump_owner
    after_id = _dispatch_pump_after_id
    _dispatch_pump_owner = None
    _dispatch_pump_after_id = None
    if owner is None or after_id is None or not hasattr(owner, "after_cancel"):
        return
    try:
        owner.after_cancel(after_id)
    except Exception as exc:
        logger.debug("Failed to cancel main-thread dispatch pump", exc_info=exc)


def _resolve_default_tk_root() -> object | None:
    try:
        import tkinter as tk

        return getattr(tk, "_default_root", None)
    except Exception:
        return None


def _supports_after_callbacks(widget: object | None) -> bool:
    return widget is not None and hasattr(widget, "after")


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
