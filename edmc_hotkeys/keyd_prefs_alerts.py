"""Detection and execution helpers for Wayland keyd prefs alerts."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from typing import Callable, Mapping, Optional

from .runtime_config import RuntimeConfig

_KEYD_HELPER_TARGET = "/usr/local/bin/edmchotkeys_send.py"
_DEFAULT_BINDINGS_PATH = "bindings.json"
_TERMINAL_CANDIDATES = (
    "x-terminal-emulator",
    "kgx",
    "gnome-terminal",
    "konsole",
    "xfce4-terminal",
    "xterm",
)


@dataclass(frozen=True)
class KeydAvailabilityStatus:
    available: bool
    keyd_executable_found: bool
    systemd_available: bool
    keyd_active: bool
    reason: str


@dataclass(frozen=True)
class KeydIntegrationStatus:
    installed: bool
    reason: str
    details: str = ""


@dataclass(frozen=True)
class KeydExportStatus:
    export_required: bool
    reason: str


@dataclass(frozen=True)
class KeydCommandSet:
    install_helper_command: str
    apply_config_command: str
    export_command: str

    @property
    def install_then_apply_block(self) -> str:
        return "\n".join((self.install_helper_command, self.apply_config_command))

    @property
    def export_then_apply_block(self) -> str:
        return "\n".join((self.export_command, self.apply_config_command))


@dataclass(frozen=True)
class TerminalLaunchResult:
    launched: bool
    reason: str
    launcher: str = ""
    status_path: Path | None = None
    log_path: Path | None = None


def resolve_runtime_path(plugin_dir: Path, configured_path: str) -> Path:
    candidate = Path(configured_path.strip())
    if candidate.is_absolute():
        return candidate
    return plugin_dir / candidate


def detect_keyd_availability(
    *,
    which: Callable[[str], Optional[str]] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> KeydAvailabilityStatus:
    keyd_executable = which("keyd")
    keyd_found = keyd_executable is not None
    systemctl = which("systemctl")
    if systemctl:
        active = _command_succeeds(run, [systemctl, "is-active", "--quiet", "keyd"])
        if keyd_found and active:
            return KeydAvailabilityStatus(
                available=True,
                keyd_executable_found=True,
                systemd_available=True,
                keyd_active=True,
                reason="keyd service active via systemctl",
            )
        reason = "keyd service not active via systemctl"
        if not keyd_found:
            reason = "keyd executable not found"
        return KeydAvailabilityStatus(
            available=False,
            keyd_executable_found=keyd_found,
            systemd_available=True,
            keyd_active=active,
            reason=reason,
        )

    pgrep = which("pgrep")
    active = False
    if pgrep:
        active = _command_succeeds(run, [pgrep, "-x", "keyd"])
    if keyd_found and active:
        return KeydAvailabilityStatus(
            available=True,
            keyd_executable_found=True,
            systemd_available=False,
            keyd_active=True,
            reason="keyd process active via pgrep",
        )
    reason = "keyd process not active via pgrep"
    if not pgrep:
        reason = "keyd process check unavailable (pgrep missing)"
    if not keyd_found:
        reason = "keyd executable not found"
    return KeydAvailabilityStatus(
        available=False,
        keyd_executable_found=keyd_found,
        systemd_available=False,
        keyd_active=active,
        reason=reason,
    )


def detect_keyd_integration(
    *,
    apply_target_path: str,
    which: Callable[[str], Optional[str]] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> KeydIntegrationStatus:
    helper_path = Path(_KEYD_HELPER_TARGET)
    if not helper_path.exists():
        return KeydIntegrationStatus(installed=False, reason="helper script is missing")
    if not os.access(helper_path, os.X_OK):
        return KeydIntegrationStatus(installed=False, reason="helper script is not executable")

    apply_target = Path(apply_target_path)
    if not apply_target.exists():
        return KeydIntegrationStatus(installed=False, reason="active keyd config is missing")

    keyd_executable = which("keyd")
    if not keyd_executable:
        return KeydIntegrationStatus(installed=False, reason="keyd executable not found for keyd check")
    check = _run_command(
        run,
        [keyd_executable, "check", str(apply_target)],
        timeout=5.0,
    )
    if check.returncode != 0:
        return KeydIntegrationStatus(
            installed=False,
            reason="keyd check failed for active config",
            details=(check.stdout + "\n" + check.stderr).strip(),
        )
    return KeydIntegrationStatus(installed=True, reason="integration installed")


def detect_keyd_export_required(*, plugin_dir: Path, config: RuntimeConfig) -> KeydExportStatus:
    state_path = resolve_runtime_path(plugin_dir, config.keyd_state_path)
    if not state_path.exists():
        return KeydExportStatus(export_required=False, reason="export state file missing")
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return KeydExportStatus(export_required=False, reason="export state unreadable")
    if not isinstance(payload, dict):
        return KeydExportStatus(export_required=False, reason="export state invalid")
    required = bool(payload.get("reload_required", False))
    if required:
        return KeydExportStatus(export_required=True, reason="export state indicates reload_required")
    return KeydExportStatus(export_required=False, reason="export state indicates no reload required")


def build_keyd_command_set(*, plugin_dir: Path, config: RuntimeConfig) -> KeydCommandSet:
    helper_source = plugin_dir / "scripts" / "keyd_send.py"
    generated_path = resolve_runtime_path(plugin_dir, config.keyd_generated_path)
    export_script = plugin_dir / "scripts" / "export_keyd_bindings.py"
    bindings_path = plugin_dir / _DEFAULT_BINDINGS_PATH
    install_command = (
        f"sudo install -m 0755 {shlex.quote(str(helper_source))} {shlex.quote(_KEYD_HELPER_TARGET)}"
    )
    apply_command = (
        f"sudo install -m 0644 {shlex.quote(str(generated_path))} {shlex.quote(config.keyd_apply_target_path)}"
    )
    export_command = (
        f"python3 {shlex.quote(str(export_script))} "
        f"--plugin-dir {shlex.quote(str(plugin_dir))} "
        f"--bindings {shlex.quote(str(bindings_path))}"
    )
    return KeydCommandSet(
        install_helper_command=install_command,
        apply_config_command=apply_command,
        export_command=export_command,
    )


def launch_terminal_command(
    *,
    command_block: str,
    plugin_dir: Path,
    action_name: str,
    which: Callable[[str], Optional[str]] = shutil.which,
    popen: Callable[..., subprocess.Popen] = subprocess.Popen,
    environ: Optional[Mapping[str, str]] = None,
) -> TerminalLaunchResult:
    launcher = _resolve_terminal_launcher(which=which)
    if launcher is None:
        return TerminalLaunchResult(
            launched=False,
            reason="No supported terminal launcher found. Use Copy Commands instead.",
        )
    runtime_dir = plugin_dir / "keyd" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    safe_name = action_name.replace(" ", "_").replace("/", "_")
    status_path = runtime_dir / f"{safe_name}.status"
    log_path = runtime_dir / f"{safe_name}.log"
    _safe_unlink(status_path)
    _safe_unlink(log_path)
    payload = _terminal_shell_payload(command_block=command_block, log_path=log_path, status_path=status_path)
    args = _terminal_args(launcher=launcher, payload=payload)
    if args is None:
        return TerminalLaunchResult(
            launched=False,
            reason=f"Terminal launcher '{launcher}' is unsupported in this build.",
        )
    env = dict(os.environ if environ is None else environ)
    popen(args, env=env)
    return TerminalLaunchResult(
        launched=True,
        reason=f"Launched command in terminal '{launcher}'.",
        launcher=launcher,
        status_path=status_path,
        log_path=log_path,
    )


def read_terminal_action_exit_code(status_path: Path) -> Optional[int]:
    if not status_path.exists():
        return None
    try:
        return int(status_path.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def read_terminal_action_log(log_path: Path, *, max_lines: int = 60) -> str:
    if not log_path.exists():
        return ""
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return ""
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def _resolve_terminal_launcher(
    *,
    which: Callable[[str], Optional[str]],
) -> Optional[str]:
    for launcher in _TERMINAL_CANDIDATES:
        if which(launcher):
            return launcher
    return None


def _terminal_args(*, launcher: str, payload: str) -> list[str] | None:
    if launcher == "kgx":
        return [launcher, "--", "bash", "-lc", payload]
    if launcher == "gnome-terminal":
        return [launcher, "--", "bash", "-lc", payload]
    if launcher == "konsole":
        return [launcher, "-e", "bash", "-lc", payload]
    if launcher == "xterm":
        return [launcher, "-hold", "-e", "bash", "-lc", payload]
    if launcher == "xfce4-terminal":
        return [launcher, "--hold", "--command", f"bash -lc {shlex.quote(payload)}"]
    if launcher == "x-terminal-emulator":
        return [launcher, "-e", "bash", "-lc", payload]
    return None


def _terminal_shell_payload(*, command_block: str, log_path: Path, status_path: Path) -> str:
    quoted_log = shlex.quote(str(log_path))
    quoted_status = shlex.quote(str(status_path))
    return (
        "set -o pipefail\n"
        "{\n"
        f"{command_block}\n"
        f"}} 2>&1 | tee -a {quoted_log}\n"
        "status=${PIPESTATUS[0]}\n"
        f"printf '%s\\n' \"$status\" > {quoted_status}\n"
        "echo\n"
        "if [ \"$status\" -eq 0 ]; then\n"
        "  echo 'EDMCHotkeys: command completed successfully.'\n"
        "else\n"
        "  echo \"EDMCHotkeys: command failed with status $status.\"\n"
        "fi\n"
        "echo 'Close this terminal window when done.'\n"
        "exec bash\n"
    )


def _run_command(
    run: Callable[..., subprocess.CompletedProcess[str]],
    args: list[str],
    *,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    return run(
        args,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _command_succeeds(
    run: Callable[..., subprocess.CompletedProcess[str]],
    args: list[str],
) -> bool:
    try:
        completed = _run_command(run, args, timeout=2.0)
    except Exception:
        return False
    return completed.returncode == 0


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except Exception:
        return
