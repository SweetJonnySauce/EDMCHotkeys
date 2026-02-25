"""Linux Wayland backend using XDG Desktop Portal GlobalShortcuts."""

from __future__ import annotations

import logging
import sys
from typing import Optional, Protocol

from .base import BackendAvailability, BackendCapabilities, HotkeyBackend, HotkeyCallback


class PortalClient(Protocol):
    """Protocol for Wayland GlobalShortcuts portal clients."""

    def availability(self) -> BackendAvailability:
        """Return portal availability."""

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        """Start portal listener."""

    def stop(self) -> None:
        """Stop portal listener."""

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        """Register a hotkey with portal."""

    def unregister_hotkey(self, binding_id: str) -> bool:
        """Unregister a hotkey with portal."""


class NullPortalClient:
    """Default portal client used when no implementation is installed."""

    def __init__(self, *, reason: str, logger: Optional[logging.Logger] = None) -> None:
        self._reason = reason
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")

    def availability(self) -> BackendAvailability:
        return BackendAvailability(name="linux-wayland-portal", available=False, reason=self._reason)

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        del on_hotkey
        return False

    def stop(self) -> None:
        return None

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        del binding_id, hotkey
        self._logger.warning("Wayland portal client is unavailable")
        return False

    def unregister_hotkey(self, binding_id: str) -> bool:
        del binding_id
        return False


class WaylandPortalBackend(HotkeyBackend):
    """Wayland backend wrapper using XDG Desktop Portal GlobalShortcuts."""

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        platform_name: Optional[str] = None,
        portal_client: Optional[PortalClient] = None,
    ) -> None:
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")
        self._platform_name = platform_name or sys.platform
        self._portal_client = portal_client or NullPortalClient(
            reason="No XDG Desktop Portal GlobalShortcuts client is configured",
            logger=self._logger,
        )

    @property
    def name(self) -> str:
        return "linux-wayland-portal"

    def availability(self) -> BackendAvailability:
        if not self._platform_name.startswith("linux"):
            return BackendAvailability(
                name=self.name,
                available=False,
                reason=f"Unsupported platform '{self._platform_name}'",
            )
        availability = self._portal_client.availability()
        if availability.available:
            return BackendAvailability(name=self.name, available=True)
        return BackendAvailability(name=self.name, available=False, reason=availability.reason)

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_side_specific_modifiers=False)

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        if not self.availability().available:
            return False
        return self._portal_client.start(on_hotkey)

    def stop(self) -> None:
        self._portal_client.stop()

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        if not self.availability().available:
            return False
        return self._portal_client.register_hotkey(binding_id, hotkey)

    def unregister_hotkey(self, binding_id: str) -> bool:
        return self._portal_client.unregister_hotkey(binding_id)
