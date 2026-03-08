"""EDMC plugin entrypoint for EDMCHotkeys."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from dataclasses import dataclass
import json
from datetime import datetime, timezone
import sys
import time
from typing import Optional

from edmc_hotkeys.bindings import BindingRecord, BindingsDocument, default_document
from edmc_hotkeys.hotkey import canonical_hotkey_text
from edmc_hotkeys.keyd_prefs_alerts import (
    KeydCommandSet,
    build_keyd_command_set,
    detect_keyd_availability,
    detect_keyd_export_required,
    detect_keyd_integration,
    launch_terminal_command,
    read_terminal_action_exit_code,
    read_terminal_action_log,
)
from edmc_hotkeys.keyd_export import export_keyd_bindings, should_use_systemd
from edmc_hotkeys.plugin import Binding, HotkeyPlugin
from edmc_hotkeys.registry import Action
from edmc_hotkeys.runtime_config import BACKEND_MODE_CONFIG_KEY, RuntimeConfig, load_runtime_config
from edmc_hotkeys.backends.selector import detect_linux_session
from edmc_hotkeys.settings_state import SettingsState, ValidationIssue
from edmc_hotkeys.settings_ui import (
    KEYD_ALERT_STATE_AUTO_HINT,
    KEYD_ALERT_STATE_EXPORT_REQUIRED,
    KEYD_ALERT_STATE_INACTIVE,
    KEYD_ALERT_STATE_INTEGRATION_MISSING,
    KEYD_ALERT_STATE_KEYD_MISSING,
    KEYD_ALERT_STATE_READY,
    KeydAlertActionOutcome,
    KeydAlertViewModel,
    SettingsPanel,
    build_settings_panel,
    keyd_alert_view_for_state,
)
from edmc_hotkeys.storage import BindingsStore


def _build_plugin_logger(plugin_name: str) -> logging.Logger:
    try:
        from config import appcmdname, appname  # type: ignore

        base_logger_name = appcmdname if os.getenv("EDMC_NO_UI") else appname
        return logging.getLogger(f"{base_logger_name}.{plugin_name}")
    except Exception:
        return logging.getLogger(plugin_name)


plugin_name = "EDMCHotkeys"
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
_VALID_BACKEND_MODES = {"auto", "wayland_keyd", "x11"}
_runtime_config: Optional[RuntimeConfig] = None
_KEYD_ACTION_POLL_INTERVAL_MS = 500
_KEYD_ACTION_POLL_TIMEOUT_SECONDS = 900
_keyd_action_poll_owner: Optional[object] = None
_keyd_action_poll_after_id: Optional[object] = None
_pending_keyd_action: Optional["_PendingKeydAction"] = None


@dataclass
class _PendingKeydAction:
    action_label: str
    status_path: Path
    log_path: Path
    started_monotonic: float
    completion_hint: str
    clear_reload_required_on_success: bool = False


def plugin_start3(plugin_dir: str) -> str:
    """EDMC plugin start hook."""
    global _plugin, _bindings_store, _bindings_document, _runtime_config
    plugin_path = Path(plugin_dir)
    _runtime_config, config_sources = _resolve_runtime_config(plugin_path)
    _apply_runtime_keyd_environment(_runtime_config)
    selected_backend_mode = _runtime_config.backend_mode.strip().lower()
    if selected_backend_mode not in _VALID_BACKEND_MODES:
        logger.warning("Invalid backend mode '%s' from runtime config; falling back to auto", selected_backend_mode)
        selected_backend_mode = "auto"
    _plugin = HotkeyPlugin(plugin_dir=plugin_path, logger=logger, backend_mode=selected_backend_mode)
    rendered_sources = " ".join(f"{key}={config_sources[key]}" for key in sorted(config_sources))
    logger.info("Runtime config sources: %s", rendered_sources)
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
    _maybe_export_keyd_bindings(reason="startup")
    _ensure_dispatch_pump_running()
    return plugin_name


def _apply_runtime_keyd_environment(config: RuntimeConfig) -> None:
    """Apply resolved keyd runtime paths for backend startup compatibility."""
    socket_path = config.keyd_socket_path.strip()
    token_file = config.keyd_token_file.strip()
    if socket_path:
        os.environ["EDMC_HOTKEYS_KEYD_SOCKET_PATH"] = socket_path
    if token_file:
        os.environ["EDMC_HOTKEYS_KEYD_TOKEN_FILE"] = token_file


def _resolve_backend_mode(plugin_path: Optional[Path] = None) -> str:
    if plugin_path is None:
        env_mode = os.environ.get(_BACKEND_MODE_ENV, "").strip().lower()
        if env_mode:
            if env_mode in _VALID_BACKEND_MODES:
                return env_mode
            logger.warning("Invalid backend mode in %s='%s'; falling back to auto", _BACKEND_MODE_ENV, env_mode)
            return "auto"
        getter = _edmc_get_str_getter()
        configured = ""
        if getter is not None:
            try:
                configured = str(getter(BACKEND_MODE_CONFIG_KEY) or "")
            except TypeError:
                try:
                    configured = str(getter(BACKEND_MODE_CONFIG_KEY, default="") or "")
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
                BACKEND_MODE_CONFIG_KEY,
                configured_mode,
            )
        return "auto"

    config, _sources = _resolve_runtime_config(plugin_path)
    mode = config.backend_mode.strip().lower()
    if mode in _VALID_BACKEND_MODES:
        return mode
    if mode:
        logger.warning("Invalid backend mode '%s'; falling back to auto", mode)
    return "auto"


def _resolve_runtime_config(plugin_path: Path) -> tuple[RuntimeConfig, dict[str, str]]:
    return load_runtime_config(
        plugin_dir=plugin_path,
        logger=logger,
        edmc_get_str=_edmc_get_str_getter(),
    )


def _edmc_get_str_getter():
    # Prefer EDMC config when available; keep fallback safe for tests/runtime without config module.
    try:
        import config  # type: ignore
    except Exception:
        return None
    getter = getattr(config, "get_str", None)
    if not callable(getter):
        return None
    return getter


def plugin_stop() -> None:
    """EDMC plugin stop hook."""
    global _plugin, _settings_panel, _runtime_config, _pending_keyd_action
    _cancel_keyd_action_poll()
    _stop_dispatch_pump()
    if _plugin is not None:
        _plugin.stop()
    _plugin = None
    _settings_panel = None
    _runtime_config = None
    _pending_keyd_action = None


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
        on_bindings_changed=_on_settings_panel_changed,
    )
    if _settings_panel is None:
        return None
    _refresh_keyd_alert_panel()
    if _pending_keyd_action is not None:
        _cancel_keyd_action_poll()
        _schedule_keyd_action_poll()
    if container is not None and _settings_panel.frame is not container:
        _settings_panel.frame.grid(row=0, column=0, sticky="nsew")
    frame = container if container is not None else _settings_panel.frame
    _install_prefs_open_refresh(frame)
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
    _maybe_export_keyd_bindings(reason="prefs_changed")
    _refresh_keyd_alert_panel()


def _on_settings_panel_changed() -> None:
    global _bindings_document
    plugin = _require_started()
    panel = _settings_panel
    if plugin is None or panel is None:
        return
    if _bindings_store is None:
        logger.warning("Bindings store is unavailable; settings change persistence skipped")
        _refresh_keyd_alert_panel()
        return

    current_document = _bindings_document or default_document()
    try:
        state = _settings_state_from_panel(
            plugin=plugin,
            panel=panel,
            current_document=current_document,
        )
    except Exception:
        logger.debug("Failed to build settings state from panel change", exc_info=True)
        _refresh_keyd_alert_panel()
        return

    issues = state.validate()
    panel.set_validation_issues(issues)
    if any(issue.level == "error" for issue in issues):
        _refresh_keyd_alert_panel()
        return

    new_document = state.to_document()
    normalized_document, disable_reasons = _auto_disable_unsupported_bindings(new_document, plugin)
    if disable_reasons:
        logger.info("Capability policy auto-disabled %d binding(s) for active profile", len(disable_reasons))
    for reason in disable_reasons:
        logger.info(reason)

    if normalized_document == current_document:
        _refresh_keyd_alert_panel()
        return

    _bindings_store.save(normalized_document)
    _bindings_document = normalized_document
    if not plugin.replace_bindings(_bindings_from_document(normalized_document)):
        logger.warning("Some bindings failed to register after panel settings change")
    _maybe_export_keyd_bindings(reason="prefs_panel_changed")
    _refresh_keyd_alert_panel()


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


def _maybe_export_keyd_bindings(*, reason: str) -> None:
    plugin = _require_started()
    if plugin is None:
        return
    if plugin.backend_name() != "linux-wayland-keyd":
        return
    if _runtime_config is None:
        logger.warning("Runtime config unavailable; skipping keyd export")
        return
    if _bindings_document is None:
        logger.warning("Bindings document unavailable; skipping keyd export")
        return
    summary = export_keyd_bindings(
        document=_bindings_document,
        plugin_dir=plugin.plugin_dir,
        config=_runtime_config,
        logger=logger,
    )
    logger.info(
        "keyd export trigger complete: reason=%s profile=%s exported=%d wrote=%s reload_required=%s",
        reason,
        summary.profile,
        summary.exported_bindings,
        summary.wrote_generated_file,
        summary.reload_required,
    )
    if not summary.reload_required:
        return
    if should_use_systemd():
        logger.info("keyd export apply command: %s", summary.systemd_prompt_command)
        return
    logger.info("keyd export apply command: %s", summary.non_systemd_prompt_command)
    logger.info(summary.non_systemd_restart_hint)


def _refresh_keyd_alert_panel() -> None:
    panel = _settings_panel
    if panel is None:
        return
    panel.set_keyd_alert(_build_keyd_alert_model())


def _install_prefs_open_refresh(frame: object) -> None:
    if not hasattr(frame, "bind"):
        return
    try:
        already_installed = bool(getattr(frame, "_edmchotkeys_keyd_refresh_on_map", False))
    except Exception:
        already_installed = False
    if already_installed:
        return

    def _on_map(_event: object) -> None:
        try:
            _refresh_keyd_alert_panel()
        except Exception as exc:
            logger.debug("Failed to refresh keyd alert state on prefs map", exc_info=exc)

    bound = False
    try:
        frame.bind("<Map>", _on_map, add="+")
        bound = True
    except TypeError:
        try:
            frame.bind("<Map>", _on_map)
            bound = True
        except Exception as exc:
            logger.debug("Failed to bind prefs map refresh callback", exc_info=exc)
    except Exception as exc:
        logger.debug("Failed to bind prefs map refresh callback", exc_info=exc)
    if not bound:
        return
    try:
        setattr(frame, "_edmchotkeys_keyd_refresh_on_map", True)
    except Exception:
        return


def _build_keyd_alert_model() -> KeydAlertViewModel:
    plugin = _require_started()
    if plugin is None or _runtime_config is None:
        return keyd_alert_view_for_state(KEYD_ALERT_STATE_INACTIVE)

    selected_backend = plugin.backend_name()
    backend_mode = _runtime_config.backend_mode.strip().lower()
    session = detect_linux_session(os.environ)
    keyd_status = detect_keyd_availability()
    command_set = build_keyd_command_set(plugin_dir=plugin.plugin_dir, config=_runtime_config)

    if selected_backend == "linux-wayland-keyd":
        if not keyd_status.available:
            return keyd_alert_view_for_state(KEYD_ALERT_STATE_KEYD_MISSING)
        integration_status = detect_keyd_integration(
            apply_target_path=_runtime_config.keyd_apply_target_path,
        )
        if not integration_status.installed:
            return keyd_alert_view_for_state(
                KEYD_ALERT_STATE_INTEGRATION_MISSING,
                install_command=command_set.install_helper_command,
                apply_command=command_set.apply_config_command,
                systemd_available=keyd_status.systemd_available,
                on_install=lambda: _run_install_integration_action(
                    command_set,
                    systemd_available=keyd_status.systemd_available,
                ),
            )
        export_status = detect_keyd_export_required(plugin_dir=plugin.plugin_dir, config=_runtime_config)
        if export_status.export_required or _panel_has_unsaved_keyd_export_changes(plugin):
            return keyd_alert_view_for_state(
                KEYD_ALERT_STATE_EXPORT_REQUIRED,
                install_command=command_set.install_helper_command,
                apply_command=command_set.apply_config_command,
                systemd_available=keyd_status.systemd_available,
                on_export=lambda: _run_export_config_action(
                    command_set,
                    systemd_available=keyd_status.systemd_available,
                ),
            )
        return keyd_alert_view_for_state(KEYD_ALERT_STATE_READY)

    if (
        backend_mode == "auto"
        and session == "wayland"
        and selected_backend != "linux-wayland-keyd"
        and keyd_status.available
    ):
        return KeydAlertViewModel(
            state=KEYD_ALERT_STATE_AUTO_HINT,
            summary="EDMC restart needed.",
            body=(
                "EDMCHotkeys auto mode selected a non-keyd backend for this EDMC session. "
                "keyd is active now; restart EDMC to switch to the keyd backend."
            ),
        )

    if _should_show_auto_keyd_hint(
        selected_backend=selected_backend,
        backend_mode=backend_mode,
        session=session,
        keyd_available=keyd_status.available,
    ):
        return keyd_alert_view_for_state(KEYD_ALERT_STATE_AUTO_HINT)
    return keyd_alert_view_for_state(KEYD_ALERT_STATE_INACTIVE)


def _panel_has_unsaved_keyd_export_changes(plugin: HotkeyPlugin) -> bool:
    panel = _settings_panel
    current_document = _bindings_document
    if panel is None or current_document is None:
        return False
    try:
        state = _settings_state_from_panel(
            plugin=plugin,
            panel=panel,
            current_document=current_document,
        )
        issues = state.validate()
        if any(issue.level == "error" for issue in issues):
            return False
        candidate_document = state.to_document()
        normalized_document, _disable_reasons = _auto_disable_unsupported_bindings(candidate_document, plugin)
        return normalized_document != current_document
    except Exception as exc:
        logger.debug("Failed to evaluate unsaved keyd export changes from settings panel", exc_info=exc)
        return False


def _should_show_auto_keyd_hint(
    *,
    selected_backend: str,
    backend_mode: str,
    session: str,
    keyd_available: bool,
) -> bool:
    if backend_mode != "auto":
        return False
    if session != "wayland":
        return False
    if selected_backend == "linux-wayland-keyd":
        return False
    return not keyd_available


def _run_install_integration_action(
    command_set: KeydCommandSet,
    *,
    systemd_available: bool,
) -> KeydAlertActionOutcome:
    command_block = command_set.install_then_apply_block
    completion_hint = "Install Integration completed. Restart keyd manually to load changes."
    if systemd_available:
        command_block = f"{command_block}\nsudo systemctl restart keyd"
        completion_hint = "Install Integration completed and keyd was restarted automatically."
    return _run_keyd_terminal_action(
        action_label="Install Integration",
        action_name="prefs_install_integration",
        command_block=command_block,
        completion_hint=completion_hint,
    )


def _run_export_config_action(
    command_set: KeydCommandSet,
    *,
    systemd_available: bool,
) -> KeydAlertActionOutcome:
    command_block = command_set.export_then_apply_block
    completion_hint = "Export Config completed. Restart keyd manually to load changes."
    if systemd_available:
        command_block = f"{command_block}\nsudo systemctl restart keyd"
        completion_hint = "Export Config completed and keyd was restarted automatically."
    return _run_keyd_terminal_action(
        action_label="Export Config",
        action_name="prefs_export_config",
        command_block=command_block,
        completion_hint=completion_hint,
        clear_reload_required_on_success=systemd_available,
    )


def _run_keyd_terminal_action(
    *,
    action_label: str,
    action_name: str,
    command_block: str,
    completion_hint: str,
    clear_reload_required_on_success: bool = False,
) -> KeydAlertActionOutcome:
    plugin = _require_started()
    if plugin is None:
        return KeydAlertActionOutcome(
            error_summary=f"{action_label} could not start because EDMCHotkeys is not running.",
        )
    if _pending_keyd_action is not None:
        return KeydAlertActionOutcome(
            error_summary=(
                "Another keyd action is still running in a terminal window. "
                "Finish that action before starting a new one."
            ),
        )
    launch = launch_terminal_command(
        command_block=command_block,
        plugin_dir=plugin.plugin_dir,
        action_name=action_name,
    )
    if not launch.launched:
        return KeydAlertActionOutcome(
            error_summary="Unable to launch a terminal for automatic setup.",
            error_details=f"{launch.reason}\nUse Copy Commands and run the command block manually.",
        )
    if launch.status_path is None or launch.log_path is None:
        return KeydAlertActionOutcome(
            error_summary=f"{action_label} launched, but status tracking is unavailable.",
            error_details="Use verify scripts or Copy Commands for manual validation.",
        )
    logger.info(
        "Keyd prefs action launched: action=%s launcher=%s status_path=%s log_path=%s",
        action_label,
        launch.launcher,
        launch.status_path,
        launch.log_path,
    )
    _register_pending_keyd_action(
        action_label=action_label,
        status_path=launch.status_path,
        log_path=launch.log_path,
        completion_hint=completion_hint,
        clear_reload_required_on_success=clear_reload_required_on_success,
    )
    return KeydAlertActionOutcome(
        success_message=(
            f"{action_label} launched in terminal. Complete any sudo prompts there; "
            "this panel will refresh after completion."
        ),
    )


def _register_pending_keyd_action(
    *,
    action_label: str,
    status_path: Path,
    log_path: Path,
    completion_hint: str,
    clear_reload_required_on_success: bool = False,
) -> None:
    global _pending_keyd_action
    _pending_keyd_action = _PendingKeydAction(
        action_label=action_label,
        status_path=status_path,
        log_path=log_path,
        started_monotonic=time.monotonic(),
        completion_hint=completion_hint,
        clear_reload_required_on_success=clear_reload_required_on_success,
    )
    _schedule_keyd_action_poll()


def _clear_keyd_reload_required_state() -> None:
    plugin = _require_started()
    if plugin is None or _runtime_config is None:
        return
    state_path = plugin.plugin_dir / _runtime_config.keyd_state_path
    if not state_path.exists():
        return
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Unable to parse keyd export state for reload clear", exc_info=exc)
        return
    if not isinstance(payload, dict):
        return
    if not bool(payload.get("reload_required", False)):
        return
    payload["reload_required"] = False
    payload["last_reload_applied_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        state_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        logger.debug("Unable to write keyd export state after reload clear", exc_info=exc)


def _schedule_keyd_action_poll() -> None:
    global _keyd_action_poll_after_id, _keyd_action_poll_owner
    if _keyd_action_poll_after_id is not None:
        return
    owner = _resolve_keyd_poll_owner()
    if owner is None:
        return
    _keyd_action_poll_owner = owner
    try:
        _keyd_action_poll_after_id = owner.after(  # type: ignore[attr-defined]
            _KEYD_ACTION_POLL_INTERVAL_MS,
            _poll_pending_keyd_action,
        )
    except Exception as exc:
        _keyd_action_poll_after_id = None
        logger.debug("Failed to schedule keyd action poll", exc_info=exc)


def _poll_pending_keyd_action() -> None:
    global _pending_keyd_action, _keyd_action_poll_after_id
    _keyd_action_poll_after_id = None
    pending = _pending_keyd_action
    if pending is None:
        return
    exit_code = read_terminal_action_exit_code(pending.status_path)
    if exit_code is None:
        elapsed = time.monotonic() - pending.started_monotonic
        if elapsed >= _KEYD_ACTION_POLL_TIMEOUT_SECONDS:
            _pending_keyd_action = None
            panel = _settings_panel
            if panel is not None:
                panel.show_keyd_alert_error(
                    "Timed out waiting for terminal action completion.",
                    "Close the terminal window and retry, or use Copy Commands for manual setup.",
                )
            return
        _schedule_keyd_action_poll()
        return

    output = read_terminal_action_log(pending.log_path)
    if output:
        if exit_code == 0:
            logger.info("Keyd prefs action output (%s):\n%s", pending.action_label, output)
        else:
            logger.warning("Keyd prefs action output (%s):\n%s", pending.action_label, output)

    _pending_keyd_action = None
    if exit_code == 0 and pending.clear_reload_required_on_success:
        _clear_keyd_reload_required_state()
    panel = _settings_panel
    _refresh_keyd_alert_panel()
    if panel is None:
        return
    if exit_code == 0:
        panel.show_keyd_alert_success(pending.completion_hint)
        return
    panel.show_keyd_alert_error(
        f"{pending.action_label} failed with exit code {exit_code}.",
        output or "No output captured from terminal action.",
    )


def _resolve_keyd_poll_owner() -> object | None:
    panel = _settings_panel
    if panel is not None and _supports_after_callbacks(panel.frame):
        return panel.frame
    if _supports_after_callbacks(_dispatch_pump_owner):
        return _dispatch_pump_owner
    return _resolve_default_tk_root()


def _cancel_keyd_action_poll() -> None:
    global _keyd_action_poll_after_id, _keyd_action_poll_owner
    owner = _keyd_action_poll_owner
    after_id = _keyd_action_poll_after_id
    _keyd_action_poll_owner = None
    _keyd_action_poll_after_id = None
    if owner is None or after_id is None or not hasattr(owner, "after_cancel"):
        return
    try:
        owner.after_cancel(after_id)
    except Exception:
        return


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
    lines = [f"{_issue_row_label_for_dialog(issue.row_id)}.{issue.field}: {issue.message}" for issue in errors[:8]]
    message = "Bindings were not saved due to validation errors:\n\n" + "\n".join(lines)
    try:
        from tkinter import messagebox

        parent = _settings_panel.frame if _settings_panel is not None else None
        messagebox.showerror("EDMCHotkeys", message, parent=parent)
    except Exception as exc:
        logger.warning("Unable to show validation error dialog")
        logger.debug("Validation error dialog failure", exc_info=exc)


def _issue_row_label_for_dialog(row_id: str) -> str:
    panel = _settings_panel
    if panel is None or not hasattr(panel, "get_rows"):
        return row_id
    try:
        for row in panel.get_rows():
            current_id = str(getattr(row, "id", "")).strip()
            if current_id != row_id:
                continue
            hotkey = str(getattr(row, "hotkey", "")).strip()
            return hotkey or row_id
    except Exception:
        return row_id
    return row_id


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
                if _should_warn_keyd_export_before_closing(plugin):
                    proceed = _show_keyd_export_pending_warning_dialog()
                    if not proceed:
                        logger.info("Settings apply canceled; keyd export is still pending")
                        return None
            except Exception:
                logger.exception("EDMCHotkeys settings apply guard failed; falling back to EDMC apply")
        return original_apply(dialog_self, *args, **kwargs)

    setattr(_guarded_apply, "_edmc_hotkeys_guard", True)
    preferences_dialog.apply = _guarded_apply
    _prefs_apply_guard_installed = True


def _should_warn_keyd_export_before_closing(plugin: HotkeyPlugin) -> bool:
    if plugin.backend_name() != "linux-wayland-keyd":
        return False
    if _runtime_config is None:
        return False
    if _panel_has_unsaved_keyd_export_changes(plugin):
        return True
    try:
        export_status = detect_keyd_export_required(plugin_dir=plugin.plugin_dir, config=_runtime_config)
    except Exception:
        logger.debug("Failed to detect keyd export status before settings apply", exc_info=True)
        return False
    return bool(export_status.export_required)


def _show_keyd_export_pending_warning_dialog() -> bool:
    message = (
        "You are closing Settings without exporting the keyd config.\n\n"
        "Hotkey changes will not be active until you export/apply the keyd config "
        "and restart keyd.\n\n"
        "Click OK to continue anyway, or Cancel to return to Settings."
    )
    try:
        from tkinter import messagebox

        parent = _settings_panel.frame if _settings_panel is not None else None
        return bool(messagebox.askokcancel("EDMCHotkeys", message, parent=parent))
    except Exception as exc:
        logger.warning("Unable to show keyd export pending warning dialog")
        logger.debug("Keyd export pending warning dialog failure", exc_info=exc)
        return True


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
