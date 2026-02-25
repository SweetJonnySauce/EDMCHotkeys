"""Global hotkey backend adapters."""

from .base import BackendAvailability, BackendCapabilities, HotkeyBackend, NullHotkeyBackend
from .selector import detect_linux_session, select_backend
from .wayland import WaylandPortalBackend
from .windows import WindowsHotkeyBackend
from .x11 import X11HotkeyBackend

__all__ = [
    "BackendAvailability",
    "BackendCapabilities",
    "HotkeyBackend",
    "NullHotkeyBackend",
    "WindowsHotkeyBackend",
    "X11HotkeyBackend",
    "WaylandPortalBackend",
    "detect_linux_session",
    "select_backend",
]
