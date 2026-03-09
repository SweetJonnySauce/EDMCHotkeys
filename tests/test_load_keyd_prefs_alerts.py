from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import load as plugin_load
from edmc_hotkeys.bindings import BindingRecord, BindingsDocument
from edmc_hotkeys.keyd_prefs_alerts import (
    KeydAvailabilityStatus,
    KeydExportStatus,
    KeydIntegrationStatus,
    KeydCommandSet,
    TerminalLaunchResult,
)
from edmc_hotkeys.runtime_config import RuntimeConfig


class _FakePlugin:
    def __init__(self, *, backend_name: str, plugin_dir: Path) -> None:
        self._backend_name = backend_name
        self.plugin_dir = plugin_dir

    def backend_name(self) -> str:
        return self._backend_name


class _FakeBindableFrame:
    def __init__(self) -> None:
        self.bind_calls: list[tuple[str, object, object]] = []
        self.callbacks: dict[str, object] = {}
        self._edmchotkeys_keyd_refresh_on_map = False

    def bind(self, event: str, callback, add=None) -> str:
        self.bind_calls.append((event, callback, add))
        self.callbacks[event] = callback
        return "bind-id"


def _runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        backend_mode="auto",
        keyd_generated_path="keyd/runtime/keyd.generated.conf",
        keyd_state_path="keyd/runtime/export_state.json",
        keyd_socket_path="/dev/shm/edmchotkeys/keyd.sock",
        keyd_token_file="/dev/shm/edmchotkeys/sender.token",
        keyd_apply_target_path="/etc/keyd/edmchotkeys.conf",
        keyd_command_template=(
            "/usr/bin/python3 /usr/local/bin/edmchotkeys_send.py --socket {socket_path} --binding-id {binding_id}"
        ),
    )


def test_build_keyd_alert_model_returns_integration_missing_for_keyd_backend(monkeypatch, tmp_path: Path) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_availability",
        lambda: KeydAvailabilityStatus(
            available=True,
            keyd_executable_found=True,
            systemd_available=True,
            keyd_active=True,
            reason="ok",
        ),
    )
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_integration",
        lambda **_kwargs: KeydIntegrationStatus(installed=False, reason="missing"),
    )
    monkeypatch.setattr(
        plugin_load,
        "build_keyd_command_set",
        lambda **_kwargs: KeydCommandSet(
            install_helper_command="install helper",
            apply_config_command="apply config",
            export_command="export config",
        ),
    )

    model = plugin_load._build_keyd_alert_model()

    assert model.state == "IntegrationMissing"
    assert model.primary_action is not None
    assert model.show_copy_button is True
    assert "systemctl restart keyd" in model.copy_commands


def test_build_keyd_alert_model_returns_auto_hint_when_auto_mode_wayland_missing_keyd(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_plugin = _FakePlugin(backend_name="inactive", plugin_dir=tmp_path)
    config = _runtime_config()
    config = RuntimeConfig(
        backend_mode="auto",
        keyd_generated_path=config.keyd_generated_path,
        keyd_state_path=config.keyd_state_path,
        keyd_socket_path=config.keyd_socket_path,
        keyd_token_file=config.keyd_token_file,
        keyd_apply_target_path=config.keyd_apply_target_path,
        keyd_command_template=config.keyd_command_template,
    )
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_runtime_config", config)
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(plugin_load, "detect_linux_session", lambda _env: "wayland")
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_availability",
        lambda: KeydAvailabilityStatus(
            available=False,
            keyd_executable_found=False,
            systemd_available=True,
            keyd_active=False,
            reason="missing",
        ),
    )
    monkeypatch.setattr(
        plugin_load,
        "build_keyd_command_set",
        lambda **_kwargs: KeydCommandSet(
            install_helper_command="install helper",
            apply_config_command="apply config",
            export_command="export config",
        ),
    )

    model = plugin_load._build_keyd_alert_model()

    assert model.state == "AutoHint"


def test_build_keyd_alert_model_returns_restart_hint_when_auto_mode_has_non_keyd_backend_but_keyd_is_active(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_plugin = _FakePlugin(backend_name="inactive", plugin_dir=tmp_path)
    config = _runtime_config()
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_runtime_config", config)
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(plugin_load, "detect_linux_session", lambda _env: "wayland")
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_availability",
        lambda: KeydAvailabilityStatus(
            available=True,
            keyd_executable_found=True,
            systemd_available=True,
            keyd_active=True,
            reason="active",
        ),
    )
    monkeypatch.setattr(
        plugin_load,
        "build_keyd_command_set",
        lambda **_kwargs: KeydCommandSet(
            install_helper_command="install helper",
            apply_config_command="apply config",
            export_command="export config",
        ),
    )

    model = plugin_load._build_keyd_alert_model()

    assert model.state == "AutoHint"
    assert model.summary == "EDMC restart needed."
    assert "restart EDMC to switch to the keyd backend" in model.body


def test_build_keyd_alert_model_returns_keyd_missing_when_keyd_backend_unavailable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_availability",
        lambda: KeydAvailabilityStatus(
            available=False,
            keyd_executable_found=False,
            systemd_available=True,
            keyd_active=False,
            reason="missing",
        ),
    )
    monkeypatch.setattr(
        plugin_load,
        "build_keyd_command_set",
        lambda **_kwargs: KeydCommandSet(
            install_helper_command="install helper",
            apply_config_command="apply config",
            export_command="export config",
        ),
    )

    model = plugin_load._build_keyd_alert_model()
    assert model.state == "KeydMissing"


def test_build_keyd_alert_model_returns_x11_keyd_conflict_when_x11_backend_has_active_keyd(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-x11", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(plugin_load, "detect_linux_session", lambda _env: "x11")
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_availability",
        lambda: KeydAvailabilityStatus(
            available=True,
            keyd_executable_found=True,
            systemd_available=True,
            keyd_active=True,
            reason="active",
        ),
    )
    monkeypatch.setattr(
        plugin_load,
        "build_keyd_command_set",
        lambda **_kwargs: KeydCommandSet(
            install_helper_command="install helper",
            apply_config_command="apply config",
            export_command="export config",
        ),
    )

    model = plugin_load._build_keyd_alert_model()
    assert model.state == "X11KeydConflict"
    assert model.primary_action is None
    assert model.show_copy_button is False


def test_build_keyd_alert_model_returns_inactive_when_x11_backend_has_no_active_keyd(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-x11", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(plugin_load, "detect_linux_session", lambda _env: "x11")
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_availability",
        lambda: KeydAvailabilityStatus(
            available=False,
            keyd_executable_found=True,
            systemd_available=True,
            keyd_active=False,
            reason="inactive",
        ),
    )
    monkeypatch.setattr(
        plugin_load,
        "build_keyd_command_set",
        lambda **_kwargs: KeydCommandSet(
            install_helper_command="install helper",
            apply_config_command="apply config",
            export_command="export config",
        ),
    )

    model = plugin_load._build_keyd_alert_model()
    assert model.state == "Inactive"


def test_build_keyd_alert_model_returns_export_required_when_state_requires_reload(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_availability",
        lambda: KeydAvailabilityStatus(
            available=True,
            keyd_executable_found=True,
            systemd_available=False,
            keyd_active=True,
            reason="ok",
        ),
    )
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_integration",
        lambda **_kwargs: KeydIntegrationStatus(installed=True, reason="ok"),
    )
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_export_required",
        lambda **_kwargs: KeydExportStatus(export_required=True, reason="reload"),
    )
    monkeypatch.setattr(
        plugin_load,
        "build_keyd_command_set",
        lambda **_kwargs: KeydCommandSet(
            install_helper_command="install helper",
            apply_config_command="apply config",
            export_command="export config",
        ),
    )

    model = plugin_load._build_keyd_alert_model()
    assert model.state == "ExportRequired"
    assert model.primary_action is not None


def test_build_keyd_alert_model_returns_ready_when_keyd_integration_is_current(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_availability",
        lambda: KeydAvailabilityStatus(
            available=True,
            keyd_executable_found=True,
            systemd_available=True,
            keyd_active=True,
            reason="ok",
        ),
    )
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_integration",
        lambda **_kwargs: KeydIntegrationStatus(installed=True, reason="ok"),
    )
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_export_required",
        lambda **_kwargs: KeydExportStatus(export_required=False, reason="no"),
    )
    monkeypatch.setattr(
        plugin_load,
        "build_keyd_command_set",
        lambda **_kwargs: KeydCommandSet(
            install_helper_command="install helper",
            apply_config_command="apply config",
            export_command="export config",
        ),
    )

    model = plugin_load._build_keyd_alert_model()
    assert model.state == "Ready"


def test_build_keyd_alert_model_returns_export_required_for_unsaved_panel_changes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_availability",
        lambda: KeydAvailabilityStatus(
            available=True,
            keyd_executable_found=True,
            systemd_available=True,
            keyd_active=True,
            reason="ok",
        ),
    )
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_integration",
        lambda **_kwargs: KeydIntegrationStatus(installed=True, reason="ok"),
    )
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_export_required",
        lambda **_kwargs: KeydExportStatus(export_required=False, reason="no"),
    )
    monkeypatch.setattr(
        plugin_load,
        "build_keyd_command_set",
        lambda **_kwargs: KeydCommandSet(
            install_helper_command="install helper",
            apply_config_command="apply config",
            export_command="export config",
        ),
    )
    monkeypatch.setattr(plugin_load, "_panel_has_unsaved_keyd_export_changes", lambda _plugin: True)

    model = plugin_load._build_keyd_alert_model()
    assert model.state == "ExportRequired"
    assert model.primary_action is not None


def test_run_keyd_terminal_action_returns_error_when_launcher_missing(monkeypatch, tmp_path: Path) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(
        plugin_load,
        "launch_terminal_command",
        lambda **_kwargs: TerminalLaunchResult(launched=False, reason="missing terminal"),
    )
    monkeypatch.setattr(plugin_load, "_pending_keyd_action", None)

    outcome = plugin_load._run_keyd_terminal_action(
        action_label="Install Integration",
        action_name="prefs_install",
        command_block="echo hi",
        completion_hint="done",
    )

    assert outcome.error_summary
    assert "Unable to launch a terminal" in outcome.error_summary


def test_run_keyd_terminal_action_sets_pending_action_on_launch(monkeypatch, tmp_path: Path) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    status_path = tmp_path / "status"
    log_path = tmp_path / "log"
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_require_started", lambda: fake_plugin)
    monkeypatch.setattr(plugin_load, "_pending_keyd_action", None)
    monkeypatch.setattr(plugin_load, "_schedule_keyd_action_poll", lambda: None)
    monkeypatch.setattr(
        plugin_load,
        "launch_terminal_command",
        lambda **_kwargs: TerminalLaunchResult(
            launched=True,
            reason="ok",
            launcher="xterm",
            status_path=status_path,
            log_path=log_path,
        ),
    )

    outcome = plugin_load._run_keyd_terminal_action(
        action_label="Export Config",
        action_name="prefs_export",
        command_block="echo hi",
        completion_hint="done",
    )

    assert outcome.success_message
    assert plugin_load._pending_keyd_action is not None
    assert plugin_load._pending_keyd_action.status_path == status_path


def test_run_export_config_action_appends_systemd_restart(monkeypatch) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        plugin_load,
        "_run_keyd_terminal_action",
        lambda **kwargs: captured.update(
            {
                "command_block": kwargs["command_block"],
                "completion_hint": kwargs["completion_hint"],
            }
        )
        or plugin_load.KeydAlertActionOutcome(success_message="ok"),
    )

    command_set = KeydCommandSet(
        install_helper_command="install helper",
        apply_config_command="apply config",
        export_command="export config",
    )
    plugin_load._run_export_config_action(command_set, systemd_available=True)

    assert captured["command_block"].endswith("sudo systemctl restart keyd")
    assert "restarted automatically" in captured["completion_hint"]


def test_run_install_integration_action_appends_systemd_restart(monkeypatch) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        plugin_load,
        "_run_keyd_terminal_action",
        lambda **kwargs: captured.update(
            {
                "command_block": kwargs["command_block"],
                "completion_hint": kwargs["completion_hint"],
            }
        )
        or plugin_load.KeydAlertActionOutcome(success_message="ok"),
    )

    command_set = KeydCommandSet(
        install_helper_command="install helper",
        apply_config_command="apply config",
        export_command="export config",
    )
    plugin_load._run_install_integration_action(command_set, systemd_available=True)

    assert captured["command_block"].endswith("sudo systemctl restart keyd")
    assert "restarted automatically" in captured["completion_hint"]


def test_run_install_integration_action_non_systemd_keeps_manual_restart_hint(monkeypatch) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        plugin_load,
        "_run_keyd_terminal_action",
        lambda **kwargs: captured.update(
            {
                "command_block": kwargs["command_block"],
                "completion_hint": kwargs["completion_hint"],
            }
        )
        or plugin_load.KeydAlertActionOutcome(success_message="ok"),
    )

    command_set = KeydCommandSet(
        install_helper_command="install helper",
        apply_config_command="apply config",
        export_command="export config",
    )
    plugin_load._run_install_integration_action(command_set, systemd_available=False)

    assert captured["command_block"] == command_set.install_then_apply_block
    assert "Restart keyd manually" in captured["completion_hint"]


def test_run_export_config_action_non_systemd_keeps_manual_restart_hint(monkeypatch) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        plugin_load,
        "_run_keyd_terminal_action",
        lambda **kwargs: captured.update(
            {
                "command_block": kwargs["command_block"],
                "completion_hint": kwargs["completion_hint"],
            }
        )
        or plugin_load.KeydAlertActionOutcome(success_message="ok"),
    )

    command_set = KeydCommandSet(
        install_helper_command="install helper",
        apply_config_command="apply config",
        export_command="export config",
    )
    plugin_load._run_export_config_action(command_set, systemd_available=False)

    assert captured["command_block"] == command_set.export_then_apply_block
    assert "Restart keyd manually" in captured["completion_hint"]


def test_poll_pending_keyd_action_reports_success_inline(monkeypatch, tmp_path: Path) -> None:
    status_path = tmp_path / "status"
    log_path = tmp_path / "log"
    status_path.write_text("0\n", encoding="utf-8")
    log_path.write_text("ok\n", encoding="utf-8")

    panel_calls: list[str] = []
    fake_panel = SimpleNamespace(
        show_keyd_alert_success=lambda message: panel_calls.append(message),
        show_keyd_alert_error=lambda summary, details="": panel_calls.append(f"{summary}:{details}"),
        set_keyd_alert=lambda _model: None,
        frame=SimpleNamespace(after=lambda *_args, **_kwargs: None, after_cancel=lambda *_args, **_kwargs: None),
    )
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)
    monkeypatch.setattr(plugin_load, "_require_started", lambda: None)
    monkeypatch.setattr(plugin_load, "_runtime_config", None)
    monkeypatch.setattr(
        plugin_load,
        "_pending_keyd_action",
        plugin_load._PendingKeydAction(
            action_label="Export Config",
            status_path=status_path,
            log_path=log_path,
            started_monotonic=0.0,
            completion_hint="Export done. Restart keyd manually.",
        ),
    )

    plugin_load._poll_pending_keyd_action()

    assert panel_calls == ["Export done. Restart keyd manually."]
    assert plugin_load._pending_keyd_action is None


def test_poll_pending_keyd_action_clears_reload_required_when_requested(monkeypatch, tmp_path: Path) -> None:
    status_path = tmp_path / "status"
    log_path = tmp_path / "log"
    status_path.write_text("0\n", encoding="utf-8")
    log_path.write_text("ok\n", encoding="utf-8")
    runtime_dir = tmp_path / "keyd" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    state_path = runtime_dir / "export_state.json"
    state_path.write_text(
        '{"reload_required": true, "state_schema_version": "1.0.0"}\n',
        encoding="utf-8",
    )

    panel_calls: list[str] = []
    fake_panel = SimpleNamespace(
        show_keyd_alert_success=lambda message: panel_calls.append(message),
        show_keyd_alert_error=lambda summary, details="": panel_calls.append(f"{summary}:{details}"),
        set_keyd_alert=lambda _model: None,
        frame=SimpleNamespace(after=lambda *_args, **_kwargs: None, after_cancel=lambda *_args, **_kwargs: None),
    )
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)
    monkeypatch.setattr(
        plugin_load,
        "_pending_keyd_action",
        plugin_load._PendingKeydAction(
            action_label="Export Config",
            status_path=status_path,
            log_path=log_path,
            started_monotonic=0.0,
            completion_hint="Export done and keyd restarted.",
            clear_reload_required_on_success=True,
        ),
    )

    plugin_load._poll_pending_keyd_action()

    assert panel_calls == ["Export done and keyd restarted."]
    state_payload = state_path.read_text(encoding="utf-8")
    assert '"reload_required": false' in state_payload
    assert plugin_load._pending_keyd_action is None


def test_poll_pending_keyd_action_reports_failure_inline(monkeypatch, tmp_path: Path) -> None:
    status_path = tmp_path / "status"
    log_path = tmp_path / "log"
    status_path.write_text("2\n", encoding="utf-8")
    log_path.write_text("permission denied\n", encoding="utf-8")

    panel_calls: list[str] = []
    fake_panel = SimpleNamespace(
        show_keyd_alert_success=lambda message: panel_calls.append(message),
        show_keyd_alert_error=lambda summary, details="": panel_calls.append(f"{summary}::{details}"),
        set_keyd_alert=lambda _model: None,
        frame=SimpleNamespace(after=lambda *_args, **_kwargs: None, after_cancel=lambda *_args, **_kwargs: None),
    )
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)
    monkeypatch.setattr(plugin_load, "_require_started", lambda: None)
    monkeypatch.setattr(plugin_load, "_runtime_config", None)
    monkeypatch.setattr(
        plugin_load,
        "_pending_keyd_action",
        plugin_load._PendingKeydAction(
            action_label="Export Config",
            status_path=status_path,
            log_path=log_path,
            started_monotonic=0.0,
            completion_hint="unused",
        ),
    )

    plugin_load._poll_pending_keyd_action()

    assert len(panel_calls) == 1
    assert "failed with exit code 2" in panel_calls[0]
    assert "permission denied" in panel_calls[0]


def test_install_prefs_open_refresh_binds_map_and_refreshes(monkeypatch) -> None:
    frame = _FakeBindableFrame()
    refresh_calls: list[str] = []
    monkeypatch.setattr(plugin_load, "_refresh_keyd_alert_panel", lambda: refresh_calls.append("refresh"))

    plugin_load._install_prefs_open_refresh(frame)

    assert frame.bind_calls
    event, callback, add = frame.bind_calls[0]
    assert event == "<Map>"
    assert add == "+"
    callback(None)
    assert refresh_calls == ["refresh"]


def test_install_prefs_open_refresh_is_idempotent(monkeypatch) -> None:
    frame = _FakeBindableFrame()
    monkeypatch.setattr(plugin_load, "_refresh_keyd_alert_panel", lambda: None)

    plugin_load._install_prefs_open_refresh(frame)
    plugin_load._install_prefs_open_refresh(frame)

    assert len(frame.bind_calls) == 1


def test_refresh_keyd_alert_panel_logs_x11_keyd_conflict_once_per_transition(monkeypatch) -> None:
    captured_models: list[object] = []
    fake_panel = SimpleNamespace(set_keyd_alert=lambda model: captured_models.append(model))
    warning_messages: list[str] = []

    state_iter = iter(
        (
            plugin_load.KeydAlertViewModel(state="X11KeydConflict"),
            plugin_load.KeydAlertViewModel(state="X11KeydConflict"),
            plugin_load.KeydAlertViewModel(state="Inactive"),
            plugin_load.KeydAlertViewModel(state="X11KeydConflict"),
        )
    )
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)
    monkeypatch.setattr(plugin_load, "_build_keyd_alert_model", lambda: next(state_iter))
    monkeypatch.setattr(plugin_load, "_last_keyd_alert_state", None)
    monkeypatch.setattr(plugin_load.logger, "warning", lambda message, *args: warning_messages.append(message % args if args else message))

    plugin_load._refresh_keyd_alert_panel()
    plugin_load._refresh_keyd_alert_panel()
    plugin_load._refresh_keyd_alert_panel()
    plugin_load._refresh_keyd_alert_panel()

    assert len(captured_models) == 4
    assert len(warning_messages) == 2
    assert all("conflicts may cause hotkeys to not work" in message for message in warning_messages)


def test_plugin_prefs_passes_bindings_changed_callback_to_settings_panel(monkeypatch, tmp_path: Path) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    captured: dict[str, object] = {}
    fake_panel = SimpleNamespace(frame=SimpleNamespace())

    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_bindings_document", None)
    monkeypatch.setattr(plugin_load, "_settings_panel", None)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())
    monkeypatch.setattr(plugin_load, "_pending_keyd_action", None)
    monkeypatch.setattr(plugin_load, "_install_prefs_apply_guard", lambda: None)
    monkeypatch.setattr(plugin_load, "_ensure_dispatch_pump_running", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(plugin_load, "_resolve_notebook_widgets", lambda _parent: None)
    monkeypatch.setattr(plugin_load, "_create_notebook_container", lambda _parent, _widgets: None)
    monkeypatch.setattr(plugin_load, "_refresh_keyd_alert_panel", lambda: None)
    monkeypatch.setattr(plugin_load, "_install_prefs_open_refresh", lambda _frame: None)
    monkeypatch.setattr(
        plugin_load,
        "build_settings_panel",
        lambda _ui_parent, _state, **kwargs: captured.update(kwargs) or fake_panel,
    )
    monkeypatch.setattr(
        fake_plugin,
        "backend_capabilities",
        lambda: SimpleNamespace(supports_side_specific_modifiers=True),
        raising=False,
    )
    monkeypatch.setattr(fake_plugin, "list_actions", lambda: [], raising=False)

    result = plugin_load.plugin_prefs(parent=object(), cmdr="", is_beta=False)

    assert result is fake_panel.frame
    assert callable(captured.get("on_bindings_changed"))


def test_show_validation_error_dialog_uses_hotkey_label_for_row(monkeypatch) -> None:
    captured_messages: list[str] = []
    fake_panel = SimpleNamespace(
        frame=object(),
        get_rows=lambda: [SimpleNamespace(id="binding_a", hotkey="LCtrl+LShift+X")],
    )
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)

    import tkinter.messagebox as messagebox

    monkeypatch.setattr(
        messagebox,
        "showerror",
        lambda _title, message, parent=None: captured_messages.append(message),
    )

    plugin_load._show_validation_error_dialog(
        [
            plugin_load.ValidationIssue(
                level="error",
                row_id="binding_a",
                field="hotkey",
                message="Hotkey is required",
            )
        ]
    )

    assert captured_messages
    assert "LCtrl+LShift+X.hotkey" in captured_messages[0]
    assert "binding_a.hotkey" not in captured_messages[0]


def test_on_settings_panel_changed_persists_valid_changes(monkeypatch, tmp_path: Path) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    fake_panel = SimpleNamespace(set_validation_issues=lambda _issues: None)
    saved_docs: list[BindingsDocument] = []
    refresh_calls: list[str] = []
    export_calls: list[str] = []
    replace_calls: list[list[object]] = []

    initial_doc = BindingsDocument(version=3, active_profile="Default", profiles={"Default": []})
    updated_doc = BindingsDocument(
        version=3,
        active_profile="Default",
        profiles={
            "Default": [
                BindingRecord(
                    id="binding_a",
                    plugin="PluginA",
                    modifiers=("ctrl_l",),
                    key="x",
                    action_id="action.one",
                    payload=None,
                    enabled=True,
                )
            ]
        },
    )

    fake_state = SimpleNamespace(validate=lambda: [], to_document=lambda: updated_doc)
    fake_store = SimpleNamespace(save=lambda document: saved_docs.append(document))

    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)
    monkeypatch.setattr(plugin_load, "_bindings_store", fake_store)
    monkeypatch.setattr(plugin_load, "_bindings_document", initial_doc)
    monkeypatch.setattr(
        plugin_load,
        "_settings_state_from_panel",
        lambda **_kwargs: fake_state,
    )
    monkeypatch.setattr(
        plugin_load,
        "_auto_disable_unsupported_bindings",
        lambda document, _plugin: (document, []),
    )
    monkeypatch.setattr(
        plugin_load,
        "_bindings_from_document",
        lambda _document: ["binding"],
    )
    monkeypatch.setattr(
        plugin_load,
        "_maybe_export_keyd_bindings",
        lambda *, reason: export_calls.append(reason),
    )
    monkeypatch.setattr(
        plugin_load,
        "_refresh_keyd_alert_panel",
        lambda: refresh_calls.append("refresh"),
    )
    monkeypatch.setattr(
        fake_plugin,
        "replace_bindings",
        lambda bindings: replace_calls.append(list(bindings)) or True,
        raising=False,
    )

    plugin_load._on_settings_panel_changed()

    assert saved_docs == [updated_doc]
    assert plugin_load._bindings_document == updated_doc
    assert replace_calls == [["binding"]]
    assert export_calls == ["prefs_panel_changed"]
    assert refresh_calls == ["refresh"]


def test_on_settings_panel_changed_skips_save_when_validation_has_errors(monkeypatch, tmp_path: Path) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    validation_calls: list[list[object]] = []
    fake_panel = SimpleNamespace(set_validation_issues=lambda issues: validation_calls.append(list(issues)))
    saved_docs: list[BindingsDocument] = []
    refresh_calls: list[str] = []
    export_calls: list[str] = []

    initial_doc = BindingsDocument(version=3, active_profile="Default", profiles={"Default": []})
    fake_issue = SimpleNamespace(level="error")
    fake_state = SimpleNamespace(validate=lambda: [fake_issue], to_document=lambda: initial_doc)
    fake_store = SimpleNamespace(save=lambda document: saved_docs.append(document))

    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)
    monkeypatch.setattr(plugin_load, "_bindings_store", fake_store)
    monkeypatch.setattr(plugin_load, "_bindings_document", initial_doc)
    monkeypatch.setattr(
        plugin_load,
        "_settings_state_from_panel",
        lambda **_kwargs: fake_state,
    )
    monkeypatch.setattr(
        plugin_load,
        "_maybe_export_keyd_bindings",
        lambda *, reason: export_calls.append(reason),
    )
    monkeypatch.setattr(
        plugin_load,
        "_refresh_keyd_alert_panel",
        lambda: refresh_calls.append("refresh"),
    )

    plugin_load._on_settings_panel_changed()

    assert validation_calls == [[fake_issue]]
    assert saved_docs == []
    assert export_calls == []
    assert refresh_calls == ["refresh"]


def test_should_warn_keyd_export_before_closing_true_for_keyd_backend_with_export_required(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())
    monkeypatch.setattr(plugin_load, "_panel_has_unsaved_keyd_export_changes", lambda _plugin: False)
    monkeypatch.setattr(
        plugin_load,
        "detect_keyd_export_required",
        lambda **_kwargs: KeydExportStatus(export_required=True, reason="reload"),
    )

    assert plugin_load._should_warn_keyd_export_before_closing(fake_plugin) is True


def test_should_warn_keyd_export_before_closing_false_for_non_keyd_backend(monkeypatch, tmp_path: Path) -> None:
    fake_plugin = _FakePlugin(backend_name="linux-x11", plugin_dir=tmp_path)
    monkeypatch.setattr(plugin_load, "_runtime_config", _runtime_config())

    assert plugin_load._should_warn_keyd_export_before_closing(fake_plugin) is False


def test_install_prefs_apply_guard_blocks_close_when_keyd_export_pending_and_user_cancels(
    monkeypatch,
    tmp_path: Path,
) -> None:
    apply_calls: list[str] = []

    class _FakePreferencesDialog:
        @staticmethod
        def apply(*_args, **_kwargs):
            apply_calls.append("apply")
            return "applied"

    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    fake_panel = SimpleNamespace(frame=object(), set_validation_issues=lambda _issues: None)
    fake_state = SimpleNamespace(validate=lambda: [])

    monkeypatch.setitem(
        plugin_load.sys.modules,
        "prefs",
        SimpleNamespace(PreferencesDialog=_FakePreferencesDialog),
    )
    monkeypatch.setattr(plugin_load, "_prefs_apply_guard_installed", False)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)
    monkeypatch.setattr(plugin_load, "_bindings_document", BindingsDocument(version=3, active_profile="Default", profiles={"Default": []}))
    monkeypatch.setattr(plugin_load, "_settings_state_from_panel", lambda **_kwargs: fake_state)
    monkeypatch.setattr(plugin_load, "_should_warn_keyd_export_before_closing", lambda _plugin: True)
    monkeypatch.setattr(plugin_load, "_show_keyd_export_pending_warning_dialog", lambda: False)

    plugin_load._install_prefs_apply_guard()
    result = _FakePreferencesDialog.apply(object())

    assert result is None
    assert apply_calls == []


def test_install_prefs_apply_guard_allows_close_when_keyd_export_pending_and_user_confirms(
    monkeypatch,
    tmp_path: Path,
) -> None:
    apply_calls: list[str] = []

    class _FakePreferencesDialog:
        @staticmethod
        def apply(*_args, **_kwargs):
            apply_calls.append("apply")
            return "applied"

    fake_plugin = _FakePlugin(backend_name="linux-wayland-keyd", plugin_dir=tmp_path)
    fake_panel = SimpleNamespace(frame=object(), set_validation_issues=lambda _issues: None)
    fake_state = SimpleNamespace(validate=lambda: [])

    monkeypatch.setitem(
        plugin_load.sys.modules,
        "prefs",
        SimpleNamespace(PreferencesDialog=_FakePreferencesDialog),
    )
    monkeypatch.setattr(plugin_load, "_prefs_apply_guard_installed", False)
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)
    monkeypatch.setattr(plugin_load, "_bindings_document", BindingsDocument(version=3, active_profile="Default", profiles={"Default": []}))
    monkeypatch.setattr(plugin_load, "_settings_state_from_panel", lambda **_kwargs: fake_state)
    monkeypatch.setattr(plugin_load, "_should_warn_keyd_export_before_closing", lambda _plugin: True)
    monkeypatch.setattr(plugin_load, "_show_keyd_export_pending_warning_dialog", lambda: True)

    plugin_load._install_prefs_apply_guard()
    result = _FakePreferencesDialog.apply(object())

    assert result == "applied"
    assert apply_calls == ["apply"]
