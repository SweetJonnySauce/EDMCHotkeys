"""Hotkey plugin scaffold for wiring bindings to the action registry."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .backends.base import HotkeyBackend
from .backends.selector import select_backend
from .registry import Action, ActionRegistry, DispatchExecutor, QueuedMainThreadDispatchExecutor


@dataclass(frozen=True)
class Binding:
    """Single hotkey binding."""

    id: str
    hotkey: str
    action_id: str
    payload: Optional[dict[str, Any]] = None
    enabled: bool = True


class HotkeyPlugin:
    """Core plugin scaffold for dispatching bound actions."""

    def __init__(
        self,
        *,
        plugin_dir: Path,
        logger: logging.Logger,
        dispatch_executor: Optional[DispatchExecutor] = None,
        hotkey_backend: Optional[HotkeyBackend] = None,
    ) -> None:
        self._plugin_dir = plugin_dir
        self._logger = logger
        default_executor = QueuedMainThreadDispatchExecutor(
            main_thread_id=threading.get_ident(),
            logger=logger,
        )
        self._dispatch_executor = dispatch_executor or default_executor
        self._registry = ActionRegistry(
            logger=logger,
            dispatch_executor=self._dispatch_executor,
        )
        self._hotkey_backend = hotkey_backend or select_backend(logger=logger)
        self._backend_started = False
        self._bindings: dict[str, Binding] = {}

    @property
    def plugin_dir(self) -> Path:
        return self._plugin_dir

    def start(self) -> None:
        availability = self._hotkey_backend.availability()
        if availability.available:
            started = self._hotkey_backend.start(self._on_backend_hotkey)
            self._backend_started = started
            if started:
                self._logger.info("Hotkey backend '%s' started", availability.name)
                for binding in self._bindings.values():
                    if binding.enabled:
                        ok = self._hotkey_backend.register_hotkey(binding.id, binding.hotkey)
                        if not ok:
                            self._logger.warning(
                                "Failed to register binding during startup: id=%s hotkey=%s",
                                binding.id,
                                binding.hotkey,
                            )
            else:
                self._logger.warning("Hotkey backend '%s' failed to start", availability.name)
        else:
            self._logger.warning(
                "Hotkey backend '%s' unavailable: %s",
                availability.name,
                availability.reason,
            )
        self._logger.info("Hotkey plugin scaffold initialized")

    def stop(self) -> None:
        self._hotkey_backend.stop()
        self._backend_started = False
        self._bindings.clear()
        self._registry.clear()
        self._logger.info("Hotkey plugin scaffold stopped")

    def register_action(self, action: Action) -> bool:
        return self._registry.register_action(action)

    def list_actions(self) -> list[Action]:
        return self._registry.list_actions()

    def get_action(self, action_id: str) -> Optional[Action]:
        return self._registry.get_action(action_id)

    def register_binding(self, binding: Binding) -> bool:
        """Register binding with backend if enabled."""
        self._bindings[binding.id] = binding
        if not binding.enabled:
            return True
        if not self._backend_started:
            return True
        ok = self._hotkey_backend.register_hotkey(binding.id, binding.hotkey)
        if not ok:
            self._logger.warning(
                "Backend failed to register binding: id=%s hotkey=%s",
                binding.id,
                binding.hotkey,
            )
        return ok

    def unregister_binding(self, binding_id: str) -> bool:
        """Remove binding and unregister from backend."""
        self._bindings.pop(binding_id, None)
        return self._hotkey_backend.unregister_hotkey(binding_id)

    def list_bindings(self) -> list[Binding]:
        return list(self._bindings.values())

    def replace_bindings(self, bindings: list[Binding]) -> bool:
        """Replace all bindings and synchronize backend registrations."""
        all_ok = True
        for existing_id in list(self._bindings.keys()):
            if not self.unregister_binding(existing_id):
                all_ok = False
        for binding in bindings:
            if not self.register_binding(binding):
                all_ok = False
        return all_ok

    def pump_main_thread_dispatch(self, max_items: Optional[int] = None) -> int:
        """Process queued main-thread actions if the executor supports queue pumping."""
        if isinstance(self._dispatch_executor, QueuedMainThreadDispatchExecutor):
            return self._dispatch_executor.pump(max_items=max_items)
        return 0

    def invoke_action(
        self,
        action_id: str,
        payload: Optional[dict[str, Any]] = None,
        source: str = "hotkey",
    ) -> bool:
        """Invoke action through the plugin's internal registry."""
        return self._registry.invoke_action(action_id=action_id, payload=payload, source=source)

    def invoke_binding(self, binding: Binding, source: str = "hotkey") -> bool:
        """Invoke a binding's target action if the binding is enabled."""
        if not binding.enabled:
            self._logger.debug("Skipping disabled binding '%s'", binding.id)
            return False
        return self.invoke_action(action_id=binding.action_id, payload=binding.payload, source=source)

    def _on_backend_hotkey(self, binding_id: str) -> None:
        binding = self._bindings.get(binding_id)
        if binding is None:
            self._logger.warning(
                "Received hotkey for unknown binding '%s'",
                binding_id,
                extra={"qualname": "HotkeyPlugin.on_hotkey"},
            )
            return
        source = f"backend:{self._hotkey_backend.name}"
        self._logger.debug(
            "Hotkey pressed: binding_id=%s hotkey=%s action_id=%s enabled=%s source=%s",
            binding.id,
            binding.hotkey,
            binding.action_id,
            binding.enabled,
            source,
            extra={"qualname": "HotkeyPlugin.on_hotkey"},
        )
        self.invoke_binding(binding, source=source)
