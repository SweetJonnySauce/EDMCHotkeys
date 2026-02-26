"""Linux Wayland backend using XDG Desktop Portal GlobalShortcuts."""

from __future__ import annotations

import asyncio
from functools import lru_cache
import logging
import os
from secrets import token_hex
import sys
import threading
from typing import Any, Optional, Protocol

from .base import BackendAvailability, BackendCapabilities, HotkeyBackend, HotkeyCallback
from .hotkey_parser import parse_hotkey


_GLOBAL_SHORTCUTS_INTROSPECTION_XML = """<node>
  <interface name="org.freedesktop.portal.GlobalShortcuts">
    <method name="CreateSession">
      <arg name="options" type="a{sv}" direction="in"/>
      <arg name="handle" type="o" direction="out"/>
    </method>
    <method name="BindShortcuts">
      <arg name="session_handle" type="o" direction="in"/>
      <arg name="shortcuts" type="a(sa{sv})" direction="in"/>
      <arg name="parent_window" type="s" direction="in"/>
      <arg name="options" type="a{sv}" direction="in"/>
      <arg name="handle" type="o" direction="out"/>
    </method>
    <signal name="Activated">
      <arg name="session_handle" type="o"/>
      <arg name="shortcut_id" type="s"/>
      <arg name="timestamp" type="t"/>
      <arg name="options" type="a{sv}"/>
    </signal>
  </interface>
</node>"""

_REQUEST_INTROSPECTION_XML = """<node>
  <interface name="org.freedesktop.portal.Request">
    <signal name="Response">
      <arg name="response" type="u"/>
      <arg name="results" type="a{sv}"/>
    </signal>
  </interface>
</node>"""

_SESSION_INTROSPECTION_XML = """<node>
  <interface name="org.freedesktop.portal.Session">
    <method name="Close"/>
  </interface>
</node>"""


@lru_cache(maxsize=3)
def _parse_introspection_node(xml_data: str) -> Any:
    from dbus_next import introspection as dbus_introspection

    return dbus_introspection.Node.parse(xml_data)


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


class PortalService(Protocol):
    """Runtime implementation details for a concrete portal client."""

    def availability(self) -> BackendAvailability:
        """Return runtime availability."""

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        """Start runtime state/listeners."""

    def stop(self) -> None:
        """Stop runtime state/listeners."""

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        """Register portal shortcut."""

    def unregister_hotkey(self, binding_id: str) -> bool:
        """Unregister portal shortcut."""


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


class DbusNextPortalService:
    """Concrete portal service using dbus-next when available."""

    _PORTAL_BUS_NAME = "org.freedesktop.portal.Desktop"
    _PORTAL_OBJECT_PATH = "/org/freedesktop/portal/desktop"
    _PORTAL_INTERFACE = "org.freedesktop.portal.GlobalShortcuts"
    _REQUEST_INTERFACE = "org.freedesktop.portal.Request"
    _SESSION_INTERFACE = "org.freedesktop.portal.Session"

    def __init__(
        self,
        *,
        logger: logging.Logger,
        platform_name: str,
        request_timeout_seconds: float = 5.0,
    ) -> None:
        self._logger = logger
        self._platform_name = platform_name
        self._request_timeout_seconds = request_timeout_seconds
        self._callback: Optional[HotkeyCallback] = None
        self._registered: dict[str, str] = {}
        self._running = False
        self._session_handle: Optional[str] = None
        self._start_error: Optional[str] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started_event = threading.Event()
        self._token_counter = 0
        self._portal_iface = None
        self._bus = None

    def availability(self) -> BackendAvailability:
        if not self._platform_name.startswith("linux"):
            return BackendAvailability(
                name="linux-wayland-portal",
                available=False,
                reason=f"Unsupported platform '{self._platform_name}'",
            )
        if not os.environ.get("WAYLAND_DISPLAY"):
            return BackendAvailability(
                name="linux-wayland-portal",
                available=False,
                reason="WAYLAND_DISPLAY is not set",
            )
        try:
            import dbus_next  # noqa: F401
        except Exception:
            return BackendAvailability(
                name="linux-wayland-portal",
                available=False,
                reason="dbus-next is unavailable",
            )
        return BackendAvailability(name="linux-wayland-portal", available=True)

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        availability = self.availability()
        if not availability.available:
            self._start_error = availability.reason
            return False
        if self._running:
            self._callback = on_hotkey
            return True

        self._callback = on_hotkey
        self._start_error = None
        self._started_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="edmc-hotkeys-wayland-portal")
        self._thread.start()
        if not self._started_event.wait(timeout=3.0):
            self._start_error = "Timed out waiting for Wayland portal startup"
            self.stop()
            return False
        return self._running

    def stop(self) -> None:
        loop = self._loop
        if loop is not None and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._shutdown_async(), loop)
            try:
                future.result(timeout=2.0)
            except Exception:
                self._logger.debug("Wayland portal async shutdown encountered an error", exc_info=True)
            loop.call_soon_threadsafe(loop.stop)

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None
        self._loop = None
        self._portal_iface = None
        self._bus = None
        self._session_handle = None
        self._callback = None
        self._registered.clear()
        self._running = False
        self._started_event.clear()

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        if not self._running:
            self._logger.warning("Wayland portal service is not running; cannot register '%s'", binding_id)
            return False
        if parse_hotkey(hotkey) is None:
            self._logger.warning("Could not parse Wayland hotkey '%s'", hotkey)
            return False

        previous = self._registered.get(binding_id)
        self._registered[binding_id] = hotkey
        if not self._sync_bind_shortcuts():
            if previous is None:
                self._registered.pop(binding_id, None)
            else:
                self._registered[binding_id] = previous
            return False
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        existed = binding_id in self._registered
        self._registered.pop(binding_id, None)
        if not existed:
            return False
        if not self._running:
            return True
        return self._sync_bind_shortcuts()

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        loop.create_task(self._initialize_async())
        try:
            loop.run_forever()
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

    async def _initialize_async(self) -> None:
        try:
            from dbus_next.aio import MessageBus
            from dbus_next.constants import BusType

            self._bus = await MessageBus(bus_type=BusType.SESSION).connect()
            self._portal_iface = self._portal_interface()
            if hasattr(self._portal_iface, "on_activated"):
                self._portal_iface.on_activated(self._on_activated_signal)
            await self._create_session_async()
            self._running = True
        except Exception as exc:
            self._start_error = f"Wayland portal startup failed: {exc}"
            self._running = False
            self._logger.warning(self._start_error)
        finally:
            self._started_event.set()

    async def _shutdown_async(self) -> None:
        try:
            await self._close_session_async()
        except Exception:
            self._logger.debug("Wayland portal session close failed", exc_info=True)
        if self._bus is not None:
            try:
                self._bus.disconnect()
            except Exception:
                self._logger.debug("Wayland portal bus disconnect failed", exc_info=True)
        self._running = False

    async def _create_session_async(self) -> None:
        if self._portal_iface is None:
            raise RuntimeError("Wayland portal interface is unavailable")
        from dbus_next import Variant

        options = {
            "handle_token": Variant("s", self._next_token("create")),
            "session_handle_token": Variant("s", self._next_token("session")),
        }
        request_path = await self._portal_iface.call_create_session(options)
        response, results = await self._wait_for_request_response_async(str(request_path))
        if response != 0:
            raise RuntimeError(f"CreateSession failed with response={response}")
        session_handle_variant = results.get("session_handle")
        if session_handle_variant is None:
            raise RuntimeError("CreateSession response did not include session_handle")
        self._session_handle = str(getattr(session_handle_variant, "value", session_handle_variant))

    async def _close_session_async(self) -> None:
        if self._session_handle is None or self._bus is None:
            return
        try:
            session_iface = self._session_interface(self._session_handle)
            if hasattr(session_iface, "call_close"):
                await session_iface.call_close()
        finally:
            self._session_handle = None

    async def _bind_shortcuts_async(self) -> bool:
        if self._portal_iface is None or self._session_handle is None:
            return False
        from dbus_next import Variant

        shortcuts: list[tuple[str, dict[str, Variant]]] = []
        for binding_id, hotkey in self._registered.items():
            shortcuts.append(
                (
                    binding_id,
                    {
                        "description": Variant("s", f"EDMC-Hotkeys {binding_id}"),
                        "preferred_trigger": Variant("s", hotkey),
                    },
                )
            )

        options = {"handle_token": Variant("s", self._next_token("bind"))}
        request_path = await self._portal_iface.call_bind_shortcuts(
            self._session_handle,
            shortcuts,
            "",
            options,
        )
        response, _results = await self._wait_for_request_response_async(str(request_path))
        return response == 0

    async def _wait_for_request_response_async(self, request_path: str) -> tuple[int, dict]:
        if self._bus is None:
            raise RuntimeError("Wayland portal bus is unavailable")
        request_iface = self._request_interface(request_path)
        loop = asyncio.get_running_loop()
        result_future: asyncio.Future[tuple[int, dict]] = loop.create_future()

        def _on_response(response: int, results: dict) -> None:
            if result_future.done():
                return
            result_future.set_result((int(response), results))

        request_iface.on_response(_on_response)
        return await asyncio.wait_for(result_future, timeout=self._request_timeout_seconds)

    def _sync_bind_shortcuts(self) -> bool:
        loop = self._loop
        if loop is None or not loop.is_running():
            return False
        future = asyncio.run_coroutine_threadsafe(self._bind_shortcuts_async(), loop)
        try:
            return bool(future.result(timeout=self._request_timeout_seconds + 1.0))
        except Exception as exc:
            self._logger.warning("Wayland portal bind operation failed: %s", exc)
            return False

    def _next_token(self, prefix: str) -> str:
        self._token_counter += 1
        return f"edmc_hotkeys_{prefix}_{self._token_counter}_{token_hex(4)}"

    def _on_activated_signal(
        self,
        session_handle: str,
        shortcut_id: str,
        timestamp: int,
        options: dict,
    ) -> None:
        if self._callback is None:
            return
        binding_id = self._resolve_activated_binding_id(
            session_handle=session_handle,
            shortcut_id=shortcut_id,
            timestamp=timestamp,
            options=options,
        )
        if not binding_id:
            self._logger.debug(
                "Ignoring Wayland portal activation with unresolved binding id: shortcut_id=%r session_handle=%r",
                shortcut_id,
                session_handle,
            )
            return
        try:
            self._callback(binding_id)
        except Exception:
            self._logger.exception("Wayland portal callback failed for '%s'", binding_id)

    def _resolve_activated_binding_id(
        self,
        *,
        session_handle: object,
        shortcut_id: object,
        timestamp: object,
        options: object,
    ) -> str:
        del timestamp

        if isinstance(shortcut_id, str) and shortcut_id in self._registered:
            return shortcut_id
        if isinstance(session_handle, str) and session_handle in self._registered:
            return session_handle
        if isinstance(options, dict):
            for value in options.values():
                candidate = getattr(value, "value", value)
                if isinstance(candidate, str) and candidate in self._registered:
                    return candidate
        return ""

    def _portal_interface(self) -> Any:
        return self._static_interface(
            object_path=self._PORTAL_OBJECT_PATH,
            interface_name=self._PORTAL_INTERFACE,
            xml_data=_GLOBAL_SHORTCUTS_INTROSPECTION_XML,
        )

    def _request_interface(self, request_path: str) -> Any:
        return self._static_interface(
            object_path=request_path,
            interface_name=self._REQUEST_INTERFACE,
            xml_data=_REQUEST_INTROSPECTION_XML,
        )

    def _session_interface(self, session_path: str) -> Any:
        return self._static_interface(
            object_path=session_path,
            interface_name=self._SESSION_INTERFACE,
            xml_data=_SESSION_INTROSPECTION_XML,
        )

    def _static_interface(self, *, object_path: str, interface_name: str, xml_data: str) -> Any:
        if self._bus is None:
            raise RuntimeError("Wayland portal bus is unavailable")
        try:
            introspection_node = _parse_introspection_node(xml_data)
        except Exception as exc:
            raise RuntimeError(
                f"Static introspection parse failed for interface '{interface_name}': {exc}"
            ) from exc
        try:
            proxy_object = self._bus.get_proxy_object(
                self._PORTAL_BUS_NAME,
                object_path,
                introspection_node,
            )
            return proxy_object.get_interface(interface_name)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to build proxy interface '{interface_name}' at '{object_path}': {exc}"
            ) from exc


class PortalGlobalShortcutsClient:
    """Concrete PortalClient using a runtime portal service implementation."""

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        platform_name: Optional[str] = None,
        service: Optional[PortalService] = None,
    ) -> None:
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")
        self._platform_name = platform_name or sys.platform
        self._service = service or DbusNextPortalService(
            logger=self._logger,
            platform_name=self._platform_name,
        )

    def availability(self) -> BackendAvailability:
        return self._service.availability()

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        return self._service.start(on_hotkey)

    def stop(self) -> None:
        self._service.stop()

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        return self._service.register_hotkey(binding_id, hotkey)

    def unregister_hotkey(self, binding_id: str) -> bool:
        return self._service.unregister_hotkey(binding_id)


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
        self._portal_client = portal_client or PortalGlobalShortcutsClient(
            logger=self._logger,
            platform_name=self._platform_name,
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
        availability = self.availability()
        if not availability.available:
            self._logger.warning(
                "Hotkey backend '%s' unavailable: %s",
                self.name,
                availability.reason,
            )
            return False
        started = self._portal_client.start(on_hotkey)
        if started:
            self._logger.info("Hotkey backend '%s' started", self.name)
        else:
            self._logger.warning("Hotkey backend '%s' failed to start", self.name)
        return started

    def stop(self) -> None:
        self._portal_client.stop()
        self._logger.info("Hotkey backend '%s' stopped", self.name)

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        availability = self.availability()
        if not availability.available:
            self._logger.warning(
                "Cannot register Wayland hotkey: backend '%s' unavailable: %s",
                self.name,
                availability.reason,
            )
            return False
        registered = self._portal_client.register_hotkey(binding_id, hotkey)
        if not registered:
            self._logger.warning(
                "Backend '%s' failed to register hotkey: id=%s hotkey=%s",
                self.name,
                binding_id,
                hotkey,
            )
        return registered

    def unregister_hotkey(self, binding_id: str) -> bool:
        unregistered = self._portal_client.unregister_hotkey(binding_id)
        if not unregistered:
            self._logger.warning(
                "Backend '%s' failed to unregister hotkey: id=%s",
                self.name,
                binding_id,
            )
        return unregistered
