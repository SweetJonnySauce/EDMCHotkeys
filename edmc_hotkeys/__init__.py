"""EDMC Hotkeys plugin package."""

from .plugin import Binding, HotkeyPlugin
from .backends import (
    BackendAvailability,
    HotkeyBackend,
    NullHotkeyBackend,
    WaylandPortalBackend,
    WindowsHotkeyBackend,
    X11HotkeyBackend,
    detect_linux_session,
    select_backend,
)
from .bindings import BindingRecord, BindingsDocument, default_document
from .registry import (
    Action,
    ActionRegistry,
    InlineDispatchExecutor,
    QueuedMainThreadDispatchExecutor,
    ThreadedWorkerDispatchExecutor,
)
from .settings_state import ActionOption, BindingRow, SettingsState, ValidationIssue
from .storage import BindingsStore

__all__ = [
    "Action",
    "ActionOption",
    "ActionRegistry",
    "BackendAvailability",
    "BindingRecord",
    "BindingRow",
    "BindingsDocument",
    "BindingsStore",
    "Binding",
    "HotkeyBackend",
    "HotkeyPlugin",
    "InlineDispatchExecutor",
    "NullHotkeyBackend",
    "QueuedMainThreadDispatchExecutor",
    "ThreadedWorkerDispatchExecutor",
    "SettingsState",
    "ValidationIssue",
    "WaylandPortalBackend",
    "WindowsHotkeyBackend",
    "X11HotkeyBackend",
    "default_document",
    "detect_linux_session",
    "select_backend",
]
