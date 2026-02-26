"""Backend abstractions for global hotkey adapters."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional, Protocol


HotkeyCallback = Callable[[str], None]

_REQUIRED_BACKEND_METHODS = (
    "availability",
    "capabilities",
    "start",
    "stop",
    "register_hotkey",
    "unregister_hotkey",
)


@dataclass(frozen=True)
class BackendAvailability:
    """Availability status for a backend adapter."""

    name: str
    available: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class BackendCapabilities:
    """Capability flags for backend-specific behavior."""

    supports_side_specific_modifiers: bool = False


class HotkeyBackend(Protocol):
    """Interface implemented by all backend adapters."""

    @property
    def name(self) -> str:
        """Human-readable backend name."""

    def availability(self) -> BackendAvailability:
        """Report if backend is available on this system."""

    def capabilities(self) -> BackendCapabilities:
        """Return backend capability flags."""

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        """Start backend listener state."""

    def stop(self) -> None:
        """Stop backend listener state and release resources."""

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        """Register a hotkey for a binding id."""

    def unregister_hotkey(self, binding_id: str) -> bool:
        """Unregister a hotkey for a binding id."""


def backend_contract_issues(backend: object) -> list[str]:
    """Return backend contract violations for diagnostics/tests."""
    issues: list[str] = []
    name_attr = getattr(backend, "name", None)
    if not isinstance(name_attr, str) or not name_attr:
        issues.append("Backend must expose a non-empty 'name' string")

    for method_name in _REQUIRED_BACKEND_METHODS:
        method = getattr(backend, method_name, None)
        if not callable(method):
            issues.append(f"Backend must implement callable '{method_name}'")
    return issues


class NullHotkeyBackend:
    """Disabled backend used when no platform backend is available."""

    def __init__(self, *, reason: str, logger: Optional[logging.Logger] = None) -> None:
        self._reason = reason
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")

    @property
    def name(self) -> str:
        return "disabled"

    def availability(self) -> BackendAvailability:
        return BackendAvailability(name=self.name, available=False, reason=self._reason)

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_side_specific_modifiers=False)

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        del on_hotkey
        return False

    def stop(self) -> None:
        return None

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        del binding_id, hotkey
        self._logger.debug("Ignoring hotkey register call because backend is disabled")
        return False

    def unregister_hotkey(self, binding_id: str) -> bool:
        del binding_id
        return False
