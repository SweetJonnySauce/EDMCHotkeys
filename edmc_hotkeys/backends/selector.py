"""Backend selection logic by platform/session."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Mapping, Optional

from .base import HotkeyBackend, NullHotkeyBackend
from .gnome_bridge import GnomeWaylandBridgeBackend
from .wayland_keyd import WaylandKeydBackend
from .wayland import WaylandPortalBackend
from .windows import WindowsHotkeyBackend
from .x11 import X11HotkeyBackend

_BACKEND_MODE_ENV = "EDMC_HOTKEYS_BACKEND_MODE"
_VALID_BACKEND_MODES = {"auto", "wayland_keyd", "wayland_portal", "wayland_gnome_bridge", "x11"}


def gnome_bridge_enabled(environ: Mapping[str, str]) -> bool:
    """Return True when prototype GNOME bridge backend is explicitly enabled."""
    value = environ.get("EDMC_HOTKEYS_GNOME_BRIDGE", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def backend_mode(environ: Mapping[str, str], *, default: str = "auto") -> str:
    """Return validated backend mode from environment."""
    value = environ.get(_BACKEND_MODE_ENV, "")
    normalized = value.strip().lower()
    if not normalized:
        return default
    if normalized in _VALID_BACKEND_MODES:
        return normalized
    return default


def detect_linux_session(environ: Mapping[str, str]) -> str:
    """Detect Linux session type from environment."""
    session = environ.get("XDG_SESSION_TYPE", "").strip().lower()
    if session == "wayland" or environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if session == "x11" or environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def select_backend(
    *,
    logger: Optional[logging.Logger] = None,
    platform_name: Optional[str] = None,
    environ: Optional[Mapping[str, str]] = None,
    plugin_dir: Optional[Path] = None,
    windows_backend: Optional[HotkeyBackend] = None,
    x11_backend: Optional[HotkeyBackend] = None,
    keyd_backend: Optional[HotkeyBackend] = None,
    wayland_backend: Optional[HotkeyBackend] = None,
    gnome_bridge_backend: Optional[HotkeyBackend] = None,
    backend_mode_override: Optional[str] = None,
    keyd_health_checker: Optional[Callable[[], tuple[bool, str]]] = None,
) -> HotkeyBackend:
    """Select backend according to platform/session strategy."""
    log = logger or logging.getLogger("EDMCHotkeys")
    current_platform = platform_name or sys.platform
    env = os.environ if environ is None else environ
    resolved_plugin_dir = plugin_dir or Path.cwd()
    mode = (backend_mode_override or backend_mode(env)).strip().lower()
    if mode not in _VALID_BACKEND_MODES:
        mode = "auto"

    if current_platform == "win32":
        return windows_backend or WindowsHotkeyBackend(logger=log, platform_name=current_platform)

    if current_platform.startswith("linux"):
        session = detect_linux_session(env)
        if mode != "auto":
            return _select_backend_for_explicit_mode(
                mode=mode,
                session=session,
                logger=log,
                platform_name=current_platform,
                plugin_dir=resolved_plugin_dir,
                environ=env,
                x11_backend=x11_backend,
                keyd_backend=keyd_backend,
                wayland_backend=wayland_backend,
                gnome_bridge_backend=gnome_bridge_backend,
                keyd_health_checker=keyd_health_checker,
            )
        if session == "wayland":
            healthy, reason = (keyd_health_checker or default_keyd_health_check)()
            if healthy:
                log.info("Auto backend selection: selected=wayland_keyd reason=%s", reason)
                return keyd_backend or WaylandKeydBackend(
                    logger=log,
                    platform_name=current_platform,
                    environ=env,
                    plugin_dir=resolved_plugin_dir,
                )
            if gnome_bridge_enabled(env):
                log.info(
                    "Auto backend selection: selected=wayland_gnome_bridge reason=%s",
                    f"keyd unavailable ({reason}); EDMC_HOTKEYS_GNOME_BRIDGE enabled",
                )
                return gnome_bridge_backend or GnomeWaylandBridgeBackend(
                    logger=log,
                    platform_name=current_platform,
                    environ=env,
                )
            log.info(
                "Auto backend selection: selected=wayland_portal reason=%s",
                f"keyd unavailable ({reason}); falling back to portal backend",
            )
            return wayland_backend or WaylandPortalBackend(logger=log, platform_name=current_platform)
        if session == "x11":
            return x11_backend or X11HotkeyBackend(logger=log, platform_name=current_platform)
        return NullHotkeyBackend(reason="Linux session type is unknown; hotkeys disabled", logger=log)

    return NullHotkeyBackend(
        reason=f"No supported backend for platform '{current_platform}'",
        logger=log,
    )


def _select_backend_for_explicit_mode(
    *,
    mode: str,
    session: str,
    logger: logging.Logger,
    platform_name: str,
    plugin_dir: Path,
    environ: Mapping[str, str],
    x11_backend: Optional[HotkeyBackend],
    keyd_backend: Optional[HotkeyBackend],
    wayland_backend: Optional[HotkeyBackend],
    gnome_bridge_backend: Optional[HotkeyBackend],
    keyd_health_checker: Optional[Callable[[], tuple[bool, str]]],
) -> HotkeyBackend:
    if mode == "x11":
        if session != "x11":
            return NullHotkeyBackend(
                reason=f"Backend mode '{mode}' requires an X11 session",
                logger=logger,
            )
        return x11_backend or X11HotkeyBackend(logger=logger, platform_name=platform_name)

    if mode == "wayland_portal":
        if session != "wayland":
            return NullHotkeyBackend(
                reason=f"Backend mode '{mode}' requires a Wayland session",
                logger=logger,
            )
        return wayland_backend or WaylandPortalBackend(logger=logger, platform_name=platform_name)

    if mode == "wayland_keyd":
        if session != "wayland":
            return NullHotkeyBackend(
                reason=f"Backend mode '{mode}' requires a Wayland session",
                logger=logger,
            )
        healthy, reason = (keyd_health_checker or default_keyd_health_check)()
        if not healthy:
            return NullHotkeyBackend(
                reason=f"Backend mode '{mode}' requires keyd to be active ({reason})",
                logger=logger,
            )
        return keyd_backend or WaylandKeydBackend(
            logger=logger,
            platform_name=platform_name,
            environ=environ,
            plugin_dir=plugin_dir,
        )

    if mode == "wayland_gnome_bridge":
        if session != "wayland":
            return NullHotkeyBackend(
                reason=f"Backend mode '{mode}' requires a Wayland session",
                logger=logger,
            )
        return gnome_bridge_backend or GnomeWaylandBridgeBackend(
            logger=logger,
            platform_name=platform_name,
            environ=environ,
        )

    return NullHotkeyBackend(
        reason=f"Unsupported explicit backend mode '{mode}'",
        logger=logger,
    )


def default_keyd_health_check() -> tuple[bool, str]:
    """Return keyd health status for backend selection."""
    systemctl = shutil.which("systemctl")
    if systemctl:
        if _command_succeeds([systemctl, "is-active", "--quiet", "keyd"]):
            return True, "keyd service active via systemctl"
        pgrep = shutil.which("pgrep")
        if pgrep and _command_succeeds([pgrep, "-x", "keyd"]):
            return True, "keyd process detected via pgrep fallback"
        return False, "keyd service not active via systemctl"
    pgrep = shutil.which("pgrep")
    if pgrep and _command_succeeds([pgrep, "-x", "keyd"]):
        return True, "keyd process detected via pgrep"
    return False, "keyd health check unavailable (no systemctl/pgrep)"


def _command_succeeds(args: list[str]) -> bool:
    try:
        completed = subprocess.run(args, check=False, capture_output=True, text=True)
    except Exception:
        return False
    return completed.returncode == 0
