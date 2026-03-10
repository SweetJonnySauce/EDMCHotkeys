from __future__ import annotations

import subprocess
from pathlib import Path

from edmc_hotkeys.keyd_prefs_alerts import (
    KeydAvailabilityStatus,
    build_keyd_command_set,
    detect_keyd_availability,
    detect_keyd_export_required,
    detect_keyd_integration,
    launch_terminal_command,
)
from edmc_hotkeys.runtime_config import RuntimeConfig


def _completed(returncode: int, *, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _default_config() -> RuntimeConfig:
    return RuntimeConfig(
        backend_mode="wayland_keyd",
        keyd_generated_path="keyd/runtime/keyd.generated.conf",
        keyd_state_path="keyd/runtime/export_state.json",
        keyd_socket_path="/dev/shm/edmchotkeys/keyd.sock",
        keyd_token_file="/dev/shm/edmchotkeys/sender.token",
        keyd_apply_target_path="/etc/keyd/edmchotkeys.conf",
        keyd_command_template=(
            "/usr/bin/python3 /usr/local/bin/edmchotkeys_send.py --socket {socket_path} --binding-id {binding_id}"
        ),
    )


def test_detect_keyd_availability_systemd_active() -> None:
    def _which(name: str) -> str | None:
        mapping = {"keyd": "/usr/bin/keyd", "systemctl": "/usr/bin/systemctl"}
        return mapping.get(name)

    status = detect_keyd_availability(
        which=_which,
        run=lambda *args, **kwargs: _completed(0),
    )
    assert status == KeydAvailabilityStatus(
        available=True,
        keyd_executable_found=True,
        systemd_available=True,
        keyd_active=True,
        reason="keyd service active via systemctl",
    )


def test_detect_keyd_availability_systemd_inactive_does_not_use_pgrep() -> None:
    called_with: list[list[str]] = []

    def _which(name: str) -> str | None:
        mapping = {
            "keyd": "/usr/bin/keyd",
            "systemctl": "/usr/bin/systemctl",
            "pgrep": "/usr/bin/pgrep",
        }
        return mapping.get(name)

    def _run(args, **_kwargs):
        called_with.append(list(args))
        return _completed(3)

    status = detect_keyd_availability(which=_which, run=_run)
    assert status.available is False
    assert status.systemd_available is True
    assert status.reason == "keyd service not active via systemctl"
    assert called_with == [["/usr/bin/systemctl", "is-active", "--quiet", "keyd"]]


def test_detect_keyd_availability_non_systemd_uses_pgrep() -> None:
    def _which(name: str) -> str | None:
        mapping = {"keyd": "/usr/bin/keyd", "pgrep": "/usr/bin/pgrep"}
        return mapping.get(name)

    status = detect_keyd_availability(
        which=_which,
        run=lambda *args, **kwargs: _completed(0),
    )
    assert status.available is True
    assert status.systemd_available is False
    assert status.reason == "keyd process active via pgrep"


def test_detect_keyd_integration_requires_helper_and_valid_keyd_config(monkeypatch, tmp_path: Path) -> None:
    helper = tmp_path / "edmchotkeys_send.py"
    helper.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    helper.chmod(0o755)
    target = tmp_path / "edmchotkeys.conf"
    target.write_text("[main]\na = noop\n", encoding="utf-8")

    import edmc_hotkeys.keyd_prefs_alerts as module

    monkeypatch.setattr(module, "_KEYD_HELPER_TARGET", str(helper))

    status = detect_keyd_integration(
        apply_target_path=str(target),
        which=lambda _name: "/usr/bin/keyd",
        run=lambda *args, **kwargs: _completed(0, stdout="No errors found."),
    )
    assert status.installed is True


def test_detect_keyd_export_required_uses_reload_required_field(tmp_path: Path) -> None:
    config = _default_config()
    state_path = tmp_path / config.keyd_state_path
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text('{"reload_required": true}', encoding="utf-8")

    status = detect_keyd_export_required(plugin_dir=tmp_path, config=config)
    assert status.export_required is True


def test_build_keyd_command_set_omits_restart() -> None:
    config = _default_config()
    commands = build_keyd_command_set(plugin_dir=Path("/tmp/plugin"), config=config)
    assert "systemctl restart keyd" not in commands.install_then_apply_block
    assert "systemctl restart keyd" not in commands.export_then_apply_block


def test_launch_terminal_command_returns_inline_error_when_no_launcher(tmp_path: Path) -> None:
    result = launch_terminal_command(
        command_block="echo hi",
        plugin_dir=tmp_path,
        action_name="prefs_export",
        which=lambda _name: None,
    )
    assert result.launched is False
    assert "Use Copy Commands" in result.reason


def test_launch_terminal_command_uses_first_available_launcher(tmp_path: Path) -> None:
    popen_args: list[list[str]] = []

    class _Popen:
        def __init__(self, args, **_kwargs):
            popen_args.append(list(args))

    def _which(name: str) -> str | None:
        mapping = {
            "x-terminal-emulator": "/usr/bin/x-terminal-emulator",
            "gnome-terminal": "/usr/bin/gnome-terminal",
        }
        return mapping.get(name)

    result = launch_terminal_command(
        command_block="echo hi",
        plugin_dir=tmp_path,
        action_name="prefs_export",
        which=_which,
        popen=_Popen,
    )
    assert result.launched is True
    assert result.launcher == "x-terminal-emulator"
    assert popen_args
    assert popen_args[0][0] == "x-terminal-emulator"


def test_launch_terminal_command_falls_back_to_next_launcher(tmp_path: Path) -> None:
    popen_args: list[list[str]] = []

    class _Popen:
        def __init__(self, args, **_kwargs):
            popen_args.append(list(args))

    def _which(name: str) -> str | None:
        mapping = {
            "kgx": "/usr/bin/kgx",
            "gnome-terminal": "/usr/bin/gnome-terminal",
        }
        return mapping.get(name)

    result = launch_terminal_command(
        command_block="echo hi",
        plugin_dir=tmp_path,
        action_name="prefs_export",
        which=_which,
        popen=_Popen,
    )
    assert result.launched is True
    assert result.launcher == "kgx"
    assert popen_args
    assert popen_args[0][0] == "kgx"
