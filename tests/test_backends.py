from __future__ import annotations

import logging

from edmc_hotkeys.backends.base import BackendAvailability, NullHotkeyBackend
from edmc_hotkeys.backends.selector import detect_linux_session, select_backend
from edmc_hotkeys.backends.wayland import WaylandPortalBackend
from edmc_hotkeys.backends.windows import MOD_CONTROL, MOD_SHIFT, WindowsHotkeyBackend
from edmc_hotkeys.backends.x11 import X11HotkeyBackend


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


class _FakePortalClient:
    def __init__(self, available: bool = True) -> None:
        self.available = available
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
        return self.available

    def stop(self) -> None:
        self.started = False

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        if not self.available:
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
    assert backend.register_hotkey("binding-1", "Ctrl+Shift+O") is True
    assert fake_user32.register_calls
    _, modifiers, virtual_key = fake_user32.register_calls[0]
    assert modifiers == (MOD_CONTROL | MOD_SHIFT)
    assert virtual_key == ord("O")
    assert backend.unregister_hotkey("binding-1") is True


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
    assert backend.register_hotkey("binding-2", "F5") is True
    assert fake_fallback.registered == [("binding-2", "F5")]
    assert fake_user32.register_calls == []
    assert backend.unregister_hotkey("binding-2") is True
    assert fake_fallback.unregistered == ["binding-2"]


def test_x11_backend_uses_client_when_available() -> None:
    client = _FakeX11Client()
    backend = X11HotkeyBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        client=client,
    )
    assert backend.availability().available is True
    assert backend.start(lambda _binding_id: None) is True
    assert backend.register_hotkey("binding-x11", "Ctrl+Shift+O") is True
    assert client.registered == [("binding-x11", "Ctrl+Shift+O")]
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
    assert backend.register_hotkey("binding-wl", "Ctrl+Alt+M") is True
    assert portal_client.registered == [("binding-wl", "Ctrl+Alt+M")]
    assert backend.unregister_hotkey("binding-wl") is True
    assert portal_client.unregistered == ["binding-wl"]

