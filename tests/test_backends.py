from __future__ import annotations

import json
import logging
import socket
import time

from edmc_hotkeys.backends.base import BackendAvailability, NullHotkeyBackend
from edmc_hotkeys.backends.gnome_bridge import GnomeWaylandBridgeBackend
from edmc_hotkeys.backends.gnome_sender_sync import SyncResult
from edmc_hotkeys.backends.selector import backend_mode, detect_linux_session, gnome_bridge_enabled, select_backend
from edmc_hotkeys.backends.wayland import (
    DbusNextPortalService,
    PortalGlobalShortcutsClient,
    WaylandPortalBackend,
)
from edmc_hotkeys.backends.windows import WindowsHotkeyBackend
from edmc_hotkeys.backends.x11 import (
    X11HotkeyBackend,
    _X11Registration,
    _event_modifiers_from_pressed,
    _registration_grab_modifiers,
    _registration_matches_event,
    _to_x11_key,
)


class _FakeBackend:
    def __init__(self, name: str = "fake") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def availability(self) -> BackendAvailability:
        return BackendAvailability(name=self._name, available=True)

    def start(self, on_hotkey):
        del on_hotkey
        return True

    def stop(self) -> None:
        return None

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        del binding_id, hotkey
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        del binding_id
        return True


class _FakeFallback:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.registered: list[tuple[str, str]] = []
        self.unregistered: list[str] = []

    def availability(self) -> BackendAvailability:
        return BackendAvailability(name="fallback", available=True)

    def start(self, on_hotkey):
        del on_hotkey
        self.started = True
        return True

    def stop(self) -> None:
        self.stopped = True

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        self.registered.append((binding_id, hotkey))
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        self.unregistered.append(binding_id)
        return True


class _FakeUser32:
    def __init__(self) -> None:
        self.register_calls: list[tuple[int, int, int]] = []
        self.unregister_calls: list[int] = []
        self.post_messages: list[tuple[int, int]] = []

    def RegisterHotKey(self, _hwnd, hotkey_id: int, modifiers: int, virtual_key: int) -> int:
        self.register_calls.append((hotkey_id, modifiers, virtual_key))
        return 1

    def UnregisterHotKey(self, _hwnd, hotkey_id: int) -> int:
        self.unregister_calls.append(hotkey_id)
        return 1

    def PostThreadMessageW(self, thread_id: int, message: int, _wparam: int, _lparam: int) -> int:
        self.post_messages.append((thread_id, message))
        return 1


class _FakeKernel32:
    def GetCurrentThreadId(self) -> int:
        return 1234


class _FakeX11Mask:
    ShiftMask = 0x01
    ControlMask = 0x04
    Mod1Mask = 0x08
    Mod4Mask = 0x40


class _FakeX11Keysym:
    @staticmethod
    def string_to_keysym(token: str) -> int:
        return {"a": 97}.get(token, 0)


class _FakeX11DisplayForMask:
    @staticmethod
    def keysym_to_keycode(keysym: int) -> int:
        return 38 if keysym == 97 else 0


class _FakePortalClient:
    def __init__(self, available: bool = True, *, start_ok: bool = True, register_ok: bool = True) -> None:
        self.available = available
        self.start_ok = start_ok
        self.register_ok = register_ok
        self.started = False
        self.registered: list[tuple[str, str]] = []
        self.unregistered: list[str] = []

    def availability(self) -> BackendAvailability:
        return BackendAvailability(
            name="linux-wayland-portal",
            available=self.available,
            reason=None if self.available else "portal unavailable",
        )

    def start(self, on_hotkey):
        del on_hotkey
        self.started = True
        return self.available and self.start_ok

    def stop(self) -> None:
        self.started = False

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        if not self.available or not self.register_ok:
            return False
        self.registered.append((binding_id, hotkey))
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        self.unregistered.append(binding_id)
        return True


class _FakeX11Client:
    def __init__(self) -> None:
        self.started = False
        self.registered: list[tuple[str, str]] = []
        self.unregistered: list[str] = []

    def start(self, on_hotkey):
        del on_hotkey
        self.started = True
        return True

    def stop(self) -> None:
        self.started = False

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        self.registered.append((binding_id, hotkey))
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        self.unregistered.append(binding_id)
        return True


class _FakePortalService:
    def __init__(self, *, available: bool = True, start_ok: bool = True, register_ok: bool = True) -> None:
        self._available = available
        self._start_ok = start_ok
        self._register_ok = register_ok
        self.started = False
        self.stopped = False
        self.registered: list[tuple[str, str]] = []
        self.unregistered: list[str] = []

    def availability(self) -> BackendAvailability:
        return BackendAvailability(
            name="linux-wayland-portal",
            available=self._available,
            reason=None if self._available else "portal unavailable",
        )

    def start(self, on_hotkey):
        del on_hotkey
        self.started = True
        return self._available and self._start_ok

    def stop(self) -> None:
        self.stopped = True

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        if not self._available or not self._register_ok:
            return False
        self.registered.append((binding_id, hotkey))
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        self.unregistered.append(binding_id)
        return True


class _FakeVariant:
    def __init__(self, value) -> None:
        self.value = value


class _FakeProxyObject:
    def __init__(self, interface: object) -> None:
        self._interface = interface

    def get_interface(self, _name: str) -> object:
        return self._interface


class _FakeBus:
    def __init__(self, interface: object) -> None:
        self.calls: list[tuple[str, str, object]] = []
        self._interface = interface

    def get_proxy_object(self, bus_name: str, object_path: str, introspection: object) -> _FakeProxyObject:
        self.calls.append((bus_name, object_path, introspection))
        return _FakeProxyObject(self._interface)


class _FakeBridgeSocket:
    def __init__(self) -> None:
        self.bound_path = ""
        self.closed = False

    def settimeout(self, _seconds: float) -> None:
        return None

    def bind(self, path: str) -> None:
        self.bound_path = path

    def recvfrom(self, _size: int) -> tuple[bytes, str]:
        raise socket.timeout()

    def close(self) -> None:
        self.closed = True


class _FakeSenderSync:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.sync_calls: list[dict[str, str]] = []
        self.clear_calls = 0

    def sync_bindings(self, bindings):
        self.sync_calls.append(dict(bindings))
        if self.fail:
            return SyncResult(ok=False, synced_bindings=0, error="sync failed")
        return SyncResult(ok=True, synced_bindings=len(bindings), error=None)

    def clear_managed_bindings(self):
        self.clear_calls += 1
        if self.fail:
            return SyncResult(ok=False, synced_bindings=0, error="clear failed")
        return SyncResult(ok=True, synced_bindings=0, error=None)


def _v1_payload(
    *,
    binding_id: str,
    token: str,
    nonce: str,
    timestamp_ms: int | None = None,
    sender_id: str = "test-sender",
) -> bytes:
    return json.dumps(
        {
            "version": "1",
            "type": "activate",
            "binding_id": binding_id,
            "timestamp_ms": int(time.time() * 1000) if timestamp_ms is None else timestamp_ms,
            "nonce": nonce,
            "token": token,
            "sender_id": sender_id,
        }
    ).encode("utf-8")


def test_detect_linux_session_wayland_from_session_type() -> None:
    assert detect_linux_session({"XDG_SESSION_TYPE": "wayland"}) == "wayland"


def test_detect_linux_session_wayland_from_wayland_display() -> None:
    assert detect_linux_session({"WAYLAND_DISPLAY": "wayland-0"}) == "wayland"


def test_detect_linux_session_x11_from_display() -> None:
    assert detect_linux_session({"DISPLAY": ":0"}) == "x11"


def test_select_backend_windows_strategy() -> None:
    backend = select_backend(logger=logging.getLogger("test.backends"), platform_name="win32")
    assert isinstance(backend, WindowsHotkeyBackend)


def test_select_backend_wayland_strategy() -> None:
    wayland_backend = _FakeBackend("wayland")
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"XDG_SESSION_TYPE": "wayland"},
        wayland_backend=wayland_backend,
    )
    assert selected is wayland_backend


def test_select_backend_wayland_bridge_strategy_when_flag_enabled() -> None:
    bridge_backend = _FakeBackend("wayland-bridge")
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"XDG_SESSION_TYPE": "wayland", "EDMC_HOTKEYS_GNOME_BRIDGE": "1"},
        gnome_bridge_backend=bridge_backend,
    )
    assert selected is bridge_backend


def test_gnome_bridge_enabled_true_and_false_values() -> None:
    assert gnome_bridge_enabled({"EDMC_HOTKEYS_GNOME_BRIDGE": "1"})
    assert gnome_bridge_enabled({"EDMC_HOTKEYS_GNOME_BRIDGE": "true"})
    assert not gnome_bridge_enabled({})
    assert not gnome_bridge_enabled({"EDMC_HOTKEYS_GNOME_BRIDGE": "0"})


def test_backend_mode_defaults_to_auto() -> None:
    assert backend_mode({}) == "auto"


def test_backend_mode_invalid_falls_back_to_auto() -> None:
    assert backend_mode({"EDMC_HOTKEYS_BACKEND_MODE": "invalid"}) == "auto"


def test_select_backend_respects_explicit_wayland_bridge_mode() -> None:
    bridge_backend = _FakeBackend("wayland-bridge")
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"XDG_SESSION_TYPE": "wayland"},
        gnome_bridge_backend=bridge_backend,
        backend_mode_override="wayland_gnome_bridge",
    )
    assert selected is bridge_backend


def test_select_backend_rejects_explicit_x11_mode_on_wayland() -> None:
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"XDG_SESSION_TYPE": "wayland"},
        backend_mode_override="x11",
    )
    assert isinstance(selected, NullHotkeyBackend)
    assert "requires an X11 session" in (selected.availability().reason or "")


def test_select_backend_x11_strategy() -> None:
    x11_backend = _FakeBackend("x11")
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"DISPLAY": ":0"},
        x11_backend=x11_backend,
    )
    assert selected is x11_backend


def test_select_backend_unknown_linux_session_returns_null() -> None:
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={},
    )
    assert isinstance(selected, NullHotkeyBackend)
    assert selected.availability().available is False


def test_windows_backend_registers_modifier_hotkey_with_registerhotkey() -> None:
    fake_user32 = _FakeUser32()
    fake_fallback = _FakeFallback()
    backend = WindowsHotkeyBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="win32",
        user32=fake_user32,
        kernel32=_FakeKernel32(),
        fallback=fake_fallback,
    )
    assert backend.start(lambda _binding_id: None) is True
    assert backend.register_hotkey("binding-1", "F5") is True
    assert fake_user32.register_calls
    _, modifiers, virtual_key = fake_user32.register_calls[0]
    assert modifiers == 0
    assert virtual_key == 0x74
    assert backend.unregister_hotkey("binding-1") is True


def test_windows_backend_registers_generic_modifier_hotkey_with_registerhotkey() -> None:
    fake_user32 = _FakeUser32()
    fake_fallback = _FakeFallback()
    backend = WindowsHotkeyBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="win32",
        user32=fake_user32,
        kernel32=_FakeKernel32(),
        fallback=fake_fallback,
    )
    assert backend.start(lambda _binding_id: None) is True
    assert backend.register_hotkey("binding-generic", "Ctrl+Shift+O") is True
    assert fake_fallback.registered == []
    assert fake_user32.register_calls
    _, modifiers, virtual_key = fake_user32.register_calls[0]
    assert modifiers == 0x0002 | 0x0004
    assert virtual_key == ord("O")
    assert backend.unregister_hotkey("binding-generic") is True


def test_windows_backend_routes_no_modifier_hotkey_to_fallback() -> None:
    fake_user32 = _FakeUser32()
    fake_fallback = _FakeFallback()
    backend = WindowsHotkeyBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="win32",
        user32=fake_user32,
        kernel32=_FakeKernel32(),
        fallback=fake_fallback,
    )
    assert backend.start(lambda _binding_id: None) is True
    assert backend.register_hotkey("binding-2", "LCtrl+LShift+O") is True
    assert fake_fallback.registered == [("binding-2", "LCtrl+LShift+O")]
    assert fake_user32.register_calls == []
    assert backend.unregister_hotkey("binding-2") is True
    assert fake_fallback.unregistered == ["binding-2"]


def test_x11_key_conversion_supports_generic_modifiers() -> None:
    result = _to_x11_key(
        _FakeX11Mask,
        _FakeX11Keysym,
        _FakeX11DisplayForMask(),
        ("ctrl", "shift"),
        "a",
    )

    assert result == (38, 0x04 | 0x01)


def test_x11_backend_uses_client_when_available() -> None:
    client = _FakeX11Client()
    backend = X11HotkeyBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        client=client,
    )
    assert backend.availability().available is True
    assert backend.start(lambda _binding_id: None) is True
    assert backend.register_hotkey("binding-x11", "LCtrl+LShift+O") is True
    assert client.registered == [("binding-x11", "LCtrl+LShift+O")]
    assert backend.unregister_hotkey("binding-x11") is True
    assert client.unregistered == ["binding-x11"]


def test_wayland_backend_uses_portal_client_when_available() -> None:
    portal_client = _FakePortalClient(available=True)
    backend = WaylandPortalBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        portal_client=portal_client,
    )
    assert backend.availability().available is True
    assert backend.start(lambda _binding_id: None) is True
    assert backend.register_hotkey("binding-wl", "LCtrl+LAlt+M") is True
    assert portal_client.registered == [("binding-wl", "LCtrl+LAlt+M")]
    assert backend.unregister_hotkey("binding-wl") is True
    assert portal_client.unregistered == ["binding-wl"]


def test_wayland_concrete_portal_client_delegates_to_service() -> None:
    service = _FakePortalService(available=True, start_ok=True, register_ok=True)
    client = PortalGlobalShortcutsClient(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        service=service,
    )

    assert client.availability().available is True
    assert client.start(lambda _binding_id: None) is True
    assert client.register_hotkey("binding-wl", "LCtrl+LAlt+M") is True
    assert client.unregister_hotkey("binding-wl") is True
    client.stop()

    assert service.started is True
    assert service.stopped is True
    assert service.registered == [("binding-wl", "LCtrl+LAlt+M")]
    assert service.unregistered == ["binding-wl"]


def test_wayland_backend_logs_unavailable_reason(caplog) -> None:
    portal_client = _FakePortalClient(available=False)
    backend = WaylandPortalBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        portal_client=portal_client,
    )

    with caplog.at_level(logging.WARNING):
        started = backend.start(lambda _binding_id: None)

    assert started is False
    assert "unavailable" in caplog.text
    assert "portal unavailable" in caplog.text


def test_wayland_dbus_service_activated_signal_uses_shortcut_id() -> None:
    service = DbusNextPortalService(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
    )
    callbacks: list[str] = []
    service._callback = callbacks.append
    service._registered = {"binding-1": "f1"}

    service._on_activated_signal("/session/1", "binding-1", 123, {})

    assert callbacks == ["binding-1"]


def test_wayland_dbus_service_activated_signal_falls_back_to_options_values() -> None:
    service = DbusNextPortalService(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
    )
    callbacks: list[str] = []
    service._callback = callbacks.append
    service._registered = {"binding-2": "f2"}

    service._on_activated_signal(
        "/session/1",
        "",
        123,
        {"shortcut_id": _FakeVariant("binding-2")},
    )

    assert callbacks == ["binding-2"]


def test_wayland_dbus_service_activated_signal_ignores_unknown_binding() -> None:
    service = DbusNextPortalService(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
    )
    callbacks: list[str] = []
    service._callback = callbacks.append
    service._registered = {"binding-1": "f1"}

    service._on_activated_signal("/session/1", "missing", 123, {})

    assert callbacks == []


def test_wayland_dbus_service_request_interface_uses_static_proxy_path() -> None:
    service = DbusNextPortalService(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
    )
    sentinel_interface = object()
    fake_bus = _FakeBus(sentinel_interface)
    service._bus = fake_bus

    resolved = service._request_interface("/org/freedesktop/portal/desktop/request/1_2/abc")

    assert resolved is sentinel_interface
    assert fake_bus.calls


def test_wayland_dbus_service_portal_interface_uses_static_proxy_path() -> None:
    service = DbusNextPortalService(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
    )
    sentinel_interface = object()
    fake_bus = _FakeBus(sentinel_interface)
    service._bus = fake_bus

    resolved = service._portal_interface()

    assert resolved is sentinel_interface
    assert fake_bus.calls


def test_wayland_dbus_service_session_interface_uses_static_proxy_path() -> None:
    service = DbusNextPortalService(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
    )
    sentinel_interface = object()
    fake_bus = _FakeBus(sentinel_interface)
    service._bus = fake_bus

    resolved = service._session_interface("/org/freedesktop/portal/desktop/session/1_2/abc")

    assert resolved is sentinel_interface
    assert fake_bus.calls


def test_wayland_backend_logs_start_failure(caplog) -> None:
    portal_client = _FakePortalClient(available=True, start_ok=False)
    backend = WaylandPortalBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        portal_client=portal_client,
    )

    with caplog.at_level(logging.WARNING):
        started = backend.start(lambda _binding_id: None)

    assert started is False
    assert "failed to start" in caplog.text
    assert "linux-wayland-portal" in caplog.text


def test_wayland_backend_logs_registration_failure(caplog) -> None:
    portal_client = _FakePortalClient(available=True, register_ok=False)
    backend = WaylandPortalBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        portal_client=portal_client,
    )
    assert backend.start(lambda _binding_id: None) is True

    with caplog.at_level(logging.WARNING):
        registered = backend.register_hotkey("binding-wl", "LCtrl+LAlt+M")

    assert registered is False
    assert "failed to register hotkey" in caplog.text
    assert "binding-wl" in caplog.text


def test_gnome_bridge_backend_unavailable_without_feature_flag(tmp_path) -> None:
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"WAYLAND_DISPLAY": "wayland-0"},
        socket_path=str(tmp_path / "bridge.sock"),
    )

    availability = backend.availability()

    assert availability.available is False
    assert "EDMC_HOTKEYS_GNOME_BRIDGE" in (availability.reason or "")


def test_gnome_bridge_backend_dispatches_registered_binding_with_v1_payload(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    token = "test-token"
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN": token,
        },
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )
    callbacks: list[str] = []

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-1", "Ctrl+Alt+H") is True

    backend._process_payload(
        _v1_payload(binding_id="binding-1", token=token, nonce="nonce-1")
    )

    backend.stop()
    assert callbacks == ["binding-1"]


def test_gnome_bridge_backend_rejects_legacy_json_payload_in_hardened_mode(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"WAYLAND_DISPLAY": "wayland-0", "EDMC_HOTKEYS_GNOME_BRIDGE": "1"},
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )
    callbacks: list[str] = []

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-json", "Ctrl+Alt+J") is True

    backend._process_payload(b'{"binding_id":"binding-json"}')
    status = backend.runtime_status()

    backend.stop()
    assert callbacks == []
    assert status["malformed_reject"] == 1


def test_gnome_bridge_backend_accepts_legacy_payload_when_compat_mode_enabled(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_ALLOW_LEGACY": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_HARDENED": "0",
        },
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )
    callbacks: list[str] = []

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-legacy", "Ctrl+Alt+J") is True

    backend._process_payload(b'{"binding_id":"binding-legacy"}')

    backend.stop()
    assert callbacks == ["binding-legacy"]


def test_gnome_bridge_backend_autosync_status_and_runtime_snapshot(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    fake_sync = _FakeSenderSync()
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"WAYLAND_DISPLAY": "wayland-0", "EDMC_HOTKEYS_GNOME_BRIDGE": "1"},
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
        sender_sync=fake_sync,
    )

    assert backend.start(lambda _binding_id: None) is True
    assert backend.register_hotkey("binding-sync", "Ctrl+M") is True
    status = backend.runtime_status()
    backend.stop()

    assert fake_sync.sync_calls
    assert any("binding-sync" in call for call in fake_sync.sync_calls)
    assert fake_sync.clear_calls == 1
    assert status["sender_status"] == "ready"
    assert status["sender_synced_bindings"] >= 1


def test_gnome_bridge_backend_batches_sender_sync_updates(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    fake_sync = _FakeSenderSync()
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"WAYLAND_DISPLAY": "wayland-0", "EDMC_HOTKEYS_GNOME_BRIDGE": "1"},
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
        sender_sync=fake_sync,
    )

    assert backend.start(lambda _binding_id: None) is True
    baseline_calls = len(fake_sync.sync_calls)
    backend.begin_binding_batch()
    assert backend.register_hotkey("b1", "Ctrl+O") is True
    assert backend.register_hotkey("b2", "Ctrl+M") is True
    assert backend.unregister_hotkey("b1") is True
    assert len(fake_sync.sync_calls) == baseline_calls
    backend.end_binding_batch()
    backend.stop()

    assert len(fake_sync.sync_calls) == baseline_calls + 1
    assert fake_sync.sync_calls[-1] == {"b2": "Ctrl+M"}


def test_gnome_bridge_backend_warns_when_no_sender_events_seen(caplog, tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    fake_sync = _FakeSenderSync()
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_NO_EVENTS_WARN_SECONDS": "0.01",
        },
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
        sender_sync=fake_sync,
    )

    assert backend.start(lambda _binding_id: None) is True
    assert backend.register_hotkey("binding-warn", "Ctrl+M") is True
    backend._started_at_mono -= 1.0

    with caplog.at_level(logging.WARNING):
        backend._maybe_warn_receiver_only()
    backend.stop()

    assert "receiver active but no companion events observed yet" in caplog.text


def test_gnome_bridge_backend_rejects_invalid_token(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN": "good-token",
        },
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )
    callbacks: list[str] = []

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-auth", "Ctrl+M") is True

    backend._process_payload(
        _v1_payload(binding_id="binding-auth", token="bad-token", nonce="nonce-auth")
    )
    status = backend.runtime_status()
    backend.stop()

    assert callbacks == []
    assert status["auth_reject"] == 1


def test_gnome_bridge_backend_rejects_missing_token(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN": "required-token",
        },
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )
    callbacks: list[str] = []

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-auth-missing", "Ctrl+M") is True

    backend._process_payload(
        _v1_payload(binding_id="binding-auth-missing", token="", nonce="nonce-auth-missing")
    )
    status = backend.runtime_status()
    backend.stop()

    assert callbacks == []
    assert status["auth_reject"] == 1


def test_gnome_bridge_backend_rejects_replayed_nonce(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    token = "test-token"
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN": token,
        },
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )
    callbacks: list[str] = []

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-replay", "Ctrl+M") is True
    now_ms = int(time.time() * 1000)
    first = _v1_payload(binding_id="binding-replay", token=token, nonce="same-nonce", timestamp_ms=now_ms)
    second = _v1_payload(binding_id="binding-replay", token=token, nonce="same-nonce", timestamp_ms=now_ms)

    backend._process_payload(first)
    backend._process_payload(second)
    status = backend.runtime_status()
    backend.stop()

    assert callbacks == ["binding-replay"]
    assert status["replay_reject"] == 1


def test_gnome_bridge_backend_rejects_stale_timestamp(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    token = "test-token"
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN": token,
        },
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )
    callbacks: list[str] = []

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-stale", "Ctrl+M") is True
    stale_ts = int(time.time() * 1000) - 60_000
    backend._process_payload(
        _v1_payload(binding_id="binding-stale", token=token, nonce="nonce-stale", timestamp_ms=stale_ts)
    )
    status = backend.runtime_status()
    backend.stop()

    assert callbacks == []
    assert status["replay_reject"] == 1


def test_gnome_bridge_backend_rate_limits_per_sender(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    token = "test-token"
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN": token,
            "EDMC_HOTKEYS_GNOME_BRIDGE_RATE_LIMIT_WINDOW_SECONDS": "60",
            "EDMC_HOTKEYS_GNOME_BRIDGE_RATE_LIMIT_PER_SENDER": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_RATE_LIMIT_GLOBAL": "10",
        },
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )
    callbacks: list[str] = []

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-rate", "Ctrl+M") is True

    backend._process_payload(
        _v1_payload(binding_id="binding-rate", token=token, nonce="rate-1", sender_id="sender-a")
    )
    backend._process_payload(
        _v1_payload(binding_id="binding-rate", token=token, nonce="rate-2", sender_id="sender-a")
    )
    status = backend.runtime_status()
    backend.stop()

    assert callbacks == ["binding-rate"]
    assert status["rate_limit_drop"] == 1


def test_gnome_bridge_backend_rate_limits_globally_across_senders(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    token = "test-token"
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN": token,
            "EDMC_HOTKEYS_GNOME_BRIDGE_RATE_LIMIT_WINDOW_SECONDS": "60",
            "EDMC_HOTKEYS_GNOME_BRIDGE_RATE_LIMIT_PER_SENDER": "10",
            "EDMC_HOTKEYS_GNOME_BRIDGE_RATE_LIMIT_GLOBAL": "1",
        },
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )
    callbacks: list[str] = []

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-rate-global", "Ctrl+M") is True

    backend._process_payload(
        _v1_payload(
            binding_id="binding-rate-global",
            token=token,
            nonce="global-1",
            sender_id="sender-a",
        )
    )
    backend._process_payload(
        _v1_payload(
            binding_id="binding-rate-global",
            token=token,
            nonce="global-2",
            sender_id="sender-b",
        )
    )
    status = backend.runtime_status()
    backend.stop()

    assert callbacks == ["binding-rate-global"]
    assert status["rate_limit_drop"] == 1


def test_gnome_bridge_backend_queue_drop_counter_tracks_saturation(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_QUEUE_MAX": "16",
        },
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )

    for _idx in range(17):
        backend._enqueue_payload(b"payload")
    status = backend.runtime_status()

    assert status["queue_drop"] == 1


def test_gnome_bridge_backend_invalid_json_counts_as_malformed(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    fake_socket = _FakeBridgeSocket()
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"WAYLAND_DISPLAY": "wayland-0", "EDMC_HOTKEYS_GNOME_BRIDGE": "1"},
        socket_path=socket_path,
        socket_factory=lambda: fake_socket,
    )

    assert backend.start(lambda _binding_id: None) is True
    backend._process_payload(b"{invalid-json")
    status = backend.runtime_status()
    backend.stop()

    assert status["malformed_reject"] == 1


def test_gnome_bridge_backend_restart_resets_runtime_and_dispatches(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    token = "test-token"
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={
            "WAYLAND_DISPLAY": "wayland-0",
            "EDMC_HOTKEYS_GNOME_BRIDGE": "1",
            "EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN": token,
        },
        socket_path=socket_path,
        socket_factory=lambda: _FakeBridgeSocket(),
    )
    callbacks: list[str] = []

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-restart", "Ctrl+M") is True
    backend._process_payload(
        _v1_payload(binding_id="binding-restart", token=token, nonce="restart-1")
    )
    backend.stop()

    assert backend.start(callbacks.append) is True
    assert backend.register_hotkey("binding-restart", "Ctrl+M") is True
    backend._process_payload(
        _v1_payload(binding_id="binding-restart", token=token, nonce="restart-2")
    )
    status = backend.runtime_status()
    backend.stop()

    assert callbacks == ["binding-restart", "binding-restart"]
    assert status["events_seen"] == 1


def test_gnome_bridge_backend_requires_xdg_runtime_dir_for_default_socket() -> None:
    backend = GnomeWaylandBridgeBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"WAYLAND_DISPLAY": "wayland-0", "EDMC_HOTKEYS_GNOME_BRIDGE": "1"},
    )

    availability = backend.availability()
    assert availability.available is False
    assert "XDG_RUNTIME_DIR is required" in (availability.reason or "")


def test_x11_side_specific_registration_match_is_order_insensitive() -> None:
    registration = _X11Registration(
        keycode=67,
        modifiers_mask=0x41,  # ShiftMask|Mod4Mask
        required_modifiers=("shift_l", "win_l"),
        grab_modifiers=(0x41, 0x01, 0x40),
    )
    side_keycodes = {
        "shift_l": {50},
        "shift_r": {62},
        "win_l": {133},
        "win_r": {134},
        "ctrl_l": {37},
        "ctrl_r": {105},
        "alt_l": {64},
        "alt_r": {108},
    }

    # Simulate both left-side modifiers currently down.
    pressed = {50, 133}

    # Allow event-state variance; correct side keys should still match.
    assert _registration_matches_event(
        registration=registration,
        event_modifiers=0x40,
        pressed_keycodes=pressed,
        side_keycodes=side_keycodes,
    )
    assert _registration_matches_event(
        registration=registration,
        event_modifiers=0x01,
        pressed_keycodes=pressed,
        side_keycodes=side_keycodes,
    )


def test_x11_side_specific_registration_rejects_wrong_side_modifier() -> None:
    registration = _X11Registration(
        keycode=67,
        modifiers_mask=0x41,
        required_modifiers=("shift_l", "win_l"),
        grab_modifiers=(0x41, 0x01, 0x40),
    )
    side_keycodes = {
        "shift_l": {50},
        "shift_r": {62},
        "win_l": {133},
        "win_r": {134},
        "ctrl_l": {37},
        "ctrl_r": {105},
        "alt_l": {64},
        "alt_r": {108},
    }

    # Right shift + left win should not satisfy left-shift requirement.
    pressed = {62, 133}
    assert not _registration_matches_event(
        registration=registration,
        event_modifiers=0x41,
        pressed_keycodes=pressed,
        side_keycodes=side_keycodes,
    )


def test_x11_right_side_registration_matches_when_right_modifiers_pressed() -> None:
    registration = _X11Registration(
        keycode=68,
        modifiers_mask=0x41,
        required_modifiers=("shift_r", "win_r"),
        grab_modifiers=(0x41, 0x01, 0x40),
    )
    side_keycodes = {
        "shift_l": {50},
        "shift_r": {62},
        "win_l": {133},
        "win_r": {134},
        "ctrl_l": {37},
        "ctrl_r": {105},
        "alt_l": {64},
        "alt_r": {108},
    }

    pressed = {62, 134}
    assert _registration_matches_event(
        registration=registration,
        event_modifiers=0x41,
        pressed_keycodes=pressed,
        side_keycodes=side_keycodes,
    )


def test_x11_right_side_registration_rejects_left_modifier() -> None:
    registration = _X11Registration(
        keycode=68,
        modifiers_mask=0x41,
        required_modifiers=("shift_r", "win_r"),
        grab_modifiers=(0x41, 0x01, 0x40),
    )
    side_keycodes = {
        "shift_l": {50},
        "shift_r": {62},
        "win_l": {133},
        "win_r": {134},
        "ctrl_l": {37},
        "ctrl_r": {105},
        "alt_l": {64},
        "alt_r": {108},
    }

    pressed = {50, 134}
    assert not _registration_matches_event(
        registration=registration,
        event_modifiers=0x41,
        pressed_keycodes=pressed,
        side_keycodes=side_keycodes,
    )


def test_x11_side_specific_registration_allows_state_fallback_when_keymap_misses_required_side() -> None:
    registration = _X11Registration(
        keycode=67,
        modifiers_mask=0x41,
        required_modifiers=("shift_l", "win_l"),
        grab_modifiers=(0x41, 0x01, 0x40),
    )
    side_keycodes = {
        "shift_l": {50},
        "shift_r": {62},
        "win_l": {133},
        "win_r": {134},
        "ctrl_l": {37},
        "ctrl_r": {105},
        "alt_l": {64},
        "alt_r": {108},
    }

    # Simulate query_keymap missing Shift_L while event.state still carries Shift+Win.
    pressed = {133}
    assert _registration_matches_event(
        registration=registration,
        event_modifiers=0x41,
        pressed_keycodes=pressed,
        side_keycodes=side_keycodes,
    )


def test_x11_non_side_specific_registration_keeps_strict_mask_match() -> None:
    registration = _X11Registration(
        keycode=67,
        modifiers_mask=0x00,
        required_modifiers=(),
        grab_modifiers=(0x00,),
    )
    assert _registration_matches_event(
        registration=registration,
        event_modifiers=0x00,
        pressed_keycodes=set(),
        side_keycodes={},
    )
    assert not _registration_matches_event(
        registration=registration,
        event_modifiers=0x01,
        pressed_keycodes=set(),
        side_keycodes={},
    )


def test_x11_side_specific_grab_modifiers_include_single_group_fallbacks() -> None:
    modifiers = _registration_grab_modifiers(
        modifiers_mask=0x41,
        required_modifiers=("shift_l", "win_l"),
    )
    assert modifiers == (0x41, 0x01, 0x40)


def test_x11_non_side_specific_grab_modifiers_stay_exact() -> None:
    modifiers = _registration_grab_modifiers(
        modifiers_mask=0x04,
        required_modifiers=(),
    )
    assert modifiers == (0x04,)


def test_x11_event_modifiers_from_pressed_maps_left_and_right_groups() -> None:
    side_keycodes = {
        "ctrl_l": {37},
        "ctrl_r": {105},
        "alt_l": {64},
        "alt_r": {108},
        "shift_l": {50},
        "shift_r": {62},
        "win_l": {133},
        "win_r": {134},
    }
    pressed = {37, 62, 133}
    event_modifiers = _event_modifiers_from_pressed(
        pressed_keycodes=pressed,
        side_keycodes=side_keycodes,
    )
    assert event_modifiers == (0x04 | 0x01 | 0x40)
