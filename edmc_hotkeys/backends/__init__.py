"""Global hotkey backend adapters."""

from .base import (
    BatchBindingUpdateBackend,
    BackendAvailability,
    BackendCapabilities,
    HotkeyBackend,
    NullHotkeyBackend,
    RuntimeStatusBackend,
    as_batch_binding_backend,
    as_runtime_status_backend,
    backend_contract_issues,
)
from .gnome_bridge import GnomeWaylandBridgeBackend
from .wayland_keyd import WaylandKeydBackend
from .selector import detect_linux_session, gnome_bridge_enabled, select_backend
from .wayland import WaylandPortalBackend
from .windows import WindowsHotkeyBackend
from .x11 import X11HotkeyBackend

__all__ = [
    "BackendAvailability",
    "BackendCapabilities",
    "HotkeyBackend",
    "BatchBindingUpdateBackend",
    "RuntimeStatusBackend",
    "NullHotkeyBackend",
    "as_batch_binding_backend",
    "as_runtime_status_backend",
    "backend_contract_issues",
    "WindowsHotkeyBackend",
    "X11HotkeyBackend",
    "WaylandPortalBackend",
    "WaylandKeydBackend",
    "GnomeWaylandBridgeBackend",
    "detect_linux_session",
    "gnome_bridge_enabled",
    "select_backend",
]
