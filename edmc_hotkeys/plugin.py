"""Hotkey plugin scaffold for wiring bindings to the action registry."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .backends.base import (
    BackendCapabilities,
    HotkeyBackend,
    as_batch_binding_backend,
    as_runtime_status_backend,
    backend_contract_issues,
)
from .backends.selector import select_backend
from .hotkey import has_side_specific_modifiers, pretty_hotkey_from_text
from .registry import Action, ActionRegistry, DispatchExecutor, QueuedMainThreadDispatchExecutor


@dataclass(frozen=True)
class Binding:
    """Single hotkey binding."""

    id: str
    hotkey: str
    action_id: str
    payload: Optional[dict[str, Any]] = None
    enabled: bool = True
    plugin: str = ""

    @property
    def pretty_hotkey(self) -> str:
        return pretty_hotkey_from_text(self.hotkey) or self.hotkey

    @property
    def requires_side_specific_modifiers(self) -> bool:
        return has_side_specific_modifiers(self.hotkey)


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
        contract_issues = backend_contract_issues(self._hotkey_backend)
        if contract_issues:
            self._logger.warning(
                "Hotkey backend contract issues detected for '%s': %s",
                type(self._hotkey_backend).__name__,
                "; ".join(contract_issues),
            )
        self._backend_started = False
        self._bindings: dict[str, Binding] = {}

    @property
    def plugin_dir(self) -> Path:
        return self._plugin_dir

    def start(self) -> None:
        availability = self._hotkey_backend.availability()
        capabilities = self._hotkey_backend.capabilities()
        self._logger.info(
            "Hotkey backend selected: name=%s available=%s supports_side_specific_modifiers=%s",
            availability.name,
            availability.available,
            capabilities.supports_side_specific_modifiers,
        )
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
                                "Failed to register binding during startup: backend=%s id=%s hotkey=%s",
                                availability.name,
                                binding.id,
                                binding.hotkey,
                            )
                self._log_backend_runtime_status()
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

    def backend_capabilities(self) -> BackendCapabilities:
        return self._hotkey_backend.capabilities()

    def backend_name(self) -> str:
        return self._hotkey_backend.name

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
                "Backend failed to register binding: backend=%s id=%s hotkey=%s",
                self._hotkey_backend.name,
                binding.id,
                binding.hotkey,
            )
        return ok

    def unregister_binding(self, binding_id: str) -> bool:
        """Remove binding and unregister from backend."""
        binding = self._bindings.pop(binding_id, None)
        if binding is None:
            return True
        if not self._backend_started or not binding.enabled:
            return True
        return self._hotkey_backend.unregister_hotkey(binding_id)

    def list_bindings(self) -> list[Binding]:
        return list(self._bindings.values())

    def replace_bindings(self, bindings: list[Binding]) -> bool:
        """Replace all bindings and synchronize backend registrations."""
        all_ok = True
        batch_backend = as_batch_binding_backend(self._hotkey_backend)
        if batch_backend is not None:
            batch_backend.begin_binding_batch()
        try:
            for existing_id in list(self._bindings.keys()):
                if not self.unregister_binding(existing_id):
                    all_ok = False
            for binding in bindings:
                if not self.register_binding(binding):
                    all_ok = False
        finally:
            if batch_backend is not None:
                batch_backend.end_binding_batch()
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
        hotkey: Optional[str] = None,
    ) -> bool:
        """Invoke action through the plugin's internal registry."""
        return self._registry.invoke_action(
            action_id=action_id,
            payload=payload,
            source=source,
            hotkey=hotkey,
        )

    def invoke_binding(self, binding: Binding, source: str = "hotkey") -> bool:
        """Invoke a binding's target action if the binding is enabled."""
        if not binding.enabled:
            self._logger.debug("Skipping disabled binding '%s'", binding.id)
            return False
        return self.invoke_action(
            action_id=binding.action_id,
            payload=binding.payload,
            source=source,
            hotkey=binding.pretty_hotkey,
        )

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
            binding.pretty_hotkey,
            binding.action_id,
            binding.enabled,
            source,
            extra={"qualname": "HotkeyPlugin.on_hotkey"},
        )
        self.invoke_binding(binding, source=source)

    def _log_backend_runtime_status(self) -> None:
        status_backend = as_runtime_status_backend(self._hotkey_backend)
        if status_backend is None:
            return
        try:
            snapshot = status_backend.runtime_status()
        except Exception:
            self._logger.debug("Failed to query backend runtime status", exc_info=True)
            return
        if not isinstance(snapshot, dict) and not hasattr(snapshot, "items"):
            self._logger.debug("Backend runtime status ignored; expected mapping")
            return
        snapshot_dict = dict(snapshot)
        rendered = " ".join(f"{key}={snapshot_dict[key]}" for key in sorted(snapshot_dict))
        self._logger.info("Hotkey backend runtime status: %s", rendered)
