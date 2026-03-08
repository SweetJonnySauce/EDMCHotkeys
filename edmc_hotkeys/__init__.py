"""EDMC Hotkeys plugin package."""

from .plugin import Binding, HotkeyPlugin
from .backends import (
    BackendAvailability,
    BackendCapabilities,
    HotkeyBackend,
    NullHotkeyBackend,
    backend_contract_issues,
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
    "BackendCapabilities",
    "BindingRecord",
    "BindingRow",
    "BindingsDocument",
    "BindingsStore",
    "Binding",
    "HotkeyBackend",
    "HotkeyPlugin",
    "InlineDispatchExecutor",
    "NullHotkeyBackend",
    "backend_contract_issues",
    "QueuedMainThreadDispatchExecutor",
    "ThreadedWorkerDispatchExecutor",
    "SettingsState",
    "ValidationIssue",
    "WindowsHotkeyBackend",
    "X11HotkeyBackend",
    "default_document",
    "detect_linux_session",
    "select_backend",
]
