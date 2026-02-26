"""Backend selection logic by platform/session."""

from __future__ import annotations

import logging
import os
import sys
from typing import Mapping, Optional

from .base import HotkeyBackend, NullHotkeyBackend
from .gnome_bridge import GnomeWaylandBridgeBackend
from .wayland import WaylandPortalBackend
from .windows import WindowsHotkeyBackend
from .x11 import X11HotkeyBackend


def gnome_bridge_enabled(environ: Mapping[str, str]) -> bool:
    """Return True when prototype GNOME bridge backend is explicitly enabled."""
    value = environ.get("EDMC_HOTKEYS_GNOME_BRIDGE", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    windows_backend: Optional[HotkeyBackend] = None,
    x11_backend: Optional[HotkeyBackend] = None,
    wayland_backend: Optional[HotkeyBackend] = None,
    gnome_bridge_backend: Optional[HotkeyBackend] = None,
) -> HotkeyBackend:
    """Select backend according to platform/session strategy."""
    log = logger or logging.getLogger("EDMC-Hotkeys")
    current_platform = platform_name or sys.platform
    env = os.environ if environ is None else environ

    if current_platform == "win32":
        return windows_backend or WindowsHotkeyBackend(logger=log, platform_name=current_platform)

    if current_platform.startswith("linux"):
        session = detect_linux_session(env)
        if session == "wayland":
            if gnome_bridge_enabled(env):
                return gnome_bridge_backend or GnomeWaylandBridgeBackend(
                    logger=log,
                    platform_name=current_platform,
                    environ=env,
                )
            return wayland_backend or WaylandPortalBackend(logger=log, platform_name=current_platform)
        if session == "x11":
            return x11_backend or X11HotkeyBackend(logger=log, platform_name=current_platform)
        return NullHotkeyBackend(reason="Linux session type is unknown; hotkeys disabled", logger=log)

    return NullHotkeyBackend(
        reason=f"No supported backend for platform '{current_platform}'",
        logger=log,
    )
