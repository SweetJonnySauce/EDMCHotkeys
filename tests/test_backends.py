from __future__ import annotations

import logging
from pathlib import Path

from edmc_hotkeys.backends.base import BackendAvailability, NullHotkeyBackend
from edmc_hotkeys.backends.selector import backend_mode, default_keyd_health_check, detect_linux_session, select_backend
from edmc_hotkeys.backends.windows import WindowsHotkeyBackend, _to_windows_hotkey
from edmc_hotkeys.backends.x11 import (
    X11HotkeyBackend,
    _X11Registration,
    _event_modifiers_from_pressed,
    _registration_grab_modifiers,
    _registration_matches_event,
    _to_x11_key,
)
from edmc_hotkeys.plugin import Binding, HotkeyPlugin
from edmc_hotkeys.registry import Action, InlineDispatchExecutor


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


class _FakeWindowsClient:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.registered: list[tuple[str, str]] = []
        self.unregistered: list[str] = []
        self.callback = None

    def start(self, on_hotkey):
        self.callback = on_hotkey
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

    def trigger(self, binding_id: str) -> None:
        if self.callback is not None:
            self.callback(binding_id)


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


def test_detect_linux_session_wayland_from_session_type() -> None:
    assert detect_linux_session({"XDG_SESSION_TYPE": "wayland"}) == "wayland"


def test_detect_linux_session_wayland_from_wayland_display() -> None:
    assert detect_linux_session({"WAYLAND_DISPLAY": "wayland-0"}) == "wayland"


def test_detect_linux_session_x11_from_display() -> None:
    assert detect_linux_session({"DISPLAY": ":0"}) == "x11"


def test_backend_mode_defaults_to_auto() -> None:
    assert backend_mode({}) == "auto"


def test_backend_mode_removed_values_fall_back_to_auto() -> None:
    removed_portal = "wayland_" + "portal"
    removed_bridge = "wayland_" + "gnome_bridge"
    assert backend_mode({"EDMC_HOTKEYS_BACKEND_MODE": removed_portal}) == "auto"
    assert backend_mode({"EDMC_HOTKEYS_BACKEND_MODE": removed_bridge}) == "auto"


def test_backend_mode_accepts_supported_modes() -> None:
    assert backend_mode({"EDMC_HOTKEYS_BACKEND_MODE": "wayland_keyd"}) == "wayland_keyd"
    assert backend_mode({"EDMC_HOTKEYS_BACKEND_MODE": "x11"}) == "x11"


def test_select_backend_windows_strategy() -> None:
    backend = select_backend(logger=logging.getLogger("test.backends"), platform_name="win32")
    assert isinstance(backend, WindowsHotkeyBackend)


def test_select_backend_x11_strategy() -> None:
    x11_backend = _FakeBackend("x11")
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"DISPLAY": ":0"},
        x11_backend=x11_backend,
        keyd_health_checker=lambda: (False, "keyd not active"),
    )
    assert selected is x11_backend


def test_select_backend_auto_prefers_keyd_when_healthy() -> None:
    keyd_backend = _FakeBackend("wayland-keyd")
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"XDG_SESSION_TYPE": "wayland"},
        keyd_backend=keyd_backend,
        keyd_health_checker=lambda: (True, "keyd service active via systemctl"),
    )
    assert selected is keyd_backend


def test_select_backend_auto_wayland_without_keyd_returns_null_backend() -> None:
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"XDG_SESSION_TYPE": "wayland"},
        keyd_health_checker=lambda: (False, "keyd not active"),
    )
    assert isinstance(selected, NullHotkeyBackend)
    assert "requires keyd" in (selected.availability().reason or "")


def test_select_backend_explicit_wayland_keyd_requires_keyd_health() -> None:
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"XDG_SESSION_TYPE": "wayland"},
        backend_mode_override="wayland_keyd",
        keyd_health_checker=lambda: (False, "keyd service not active"),
    )
    assert isinstance(selected, NullHotkeyBackend)
    assert "requires keyd to be active" in (selected.availability().reason or "")


def test_select_backend_rejects_explicit_x11_mode_on_wayland() -> None:
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"XDG_SESSION_TYPE": "wayland"},
        backend_mode_override="x11",
        keyd_health_checker=lambda: (False, "keyd not active"),
    )
    assert isinstance(selected, NullHotkeyBackend)
    assert "requires an X11 session" in (selected.availability().reason or "")


def test_select_backend_removed_mode_normalizes_to_auto_behavior() -> None:
    removed_portal = "wayland_" + "portal"
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={"XDG_SESSION_TYPE": "wayland"},
        backend_mode_override=removed_portal,
        keyd_health_checker=lambda: (False, "keyd not active"),
    )
    assert isinstance(selected, NullHotkeyBackend)
    assert "requires keyd" in (selected.availability().reason or "")


def test_select_backend_unknown_linux_session_returns_null() -> None:
    selected = select_backend(
        logger=logging.getLogger("test.backends"),
        platform_name="linux",
        environ={},
        keyd_health_checker=lambda: (False, "keyd not active"),
    )
    assert isinstance(selected, NullHotkeyBackend)
    assert selected.availability().available is False


def test_default_keyd_health_check_uses_systemctl_when_available(monkeypatch) -> None:
    monkeypatch.setattr("edmc_hotkeys.backends.selector.shutil.which", lambda name: "/usr/bin/systemctl" if name == "systemctl" else None)
    monkeypatch.setattr(
        "edmc_hotkeys.backends.selector._command_succeeds",
        lambda args: args[:4] == ["/usr/bin/systemctl", "is-active", "--quiet", "keyd"],
    )

    healthy, reason = default_keyd_health_check()
    assert healthy is True
    assert "systemctl" in reason


def test_default_keyd_health_check_falls_back_to_pgrep(monkeypatch) -> None:
    def _which(name: str):
        return {"systemctl": "/usr/bin/systemctl", "pgrep": "/usr/bin/pgrep"}.get(name)

    def _succeeds(args: list[str]) -> bool:
        if args[:4] == ["/usr/bin/systemctl", "is-active", "--quiet", "keyd"]:
            return False
        return args == ["/usr/bin/pgrep", "-x", "keyd"]

    monkeypatch.setattr("edmc_hotkeys.backends.selector.shutil.which", _which)
    monkeypatch.setattr("edmc_hotkeys.backends.selector._command_succeeds", _succeeds)

    healthy, reason = default_keyd_health_check()
    assert healthy is True
    assert "pgrep fallback" in reason


def test_windows_backend_uses_client_when_available() -> None:
    client = _FakeWindowsClient()
    backend = WindowsHotkeyBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="win32",
        client=client,
    )
    assert backend.availability().available is True
    assert backend.start(lambda _binding_id: None) is True
    assert backend.register_hotkey("binding-win", "Ctrl+Shift+O") is True
    assert client.registered == [("binding-win", "Ctrl+Shift+O")]
    assert backend.unregister_hotkey("binding-win") is True
    assert client.unregistered == ["binding-win"]


def test_windows_key_conversion_supports_function_keys() -> None:
    mod_mask, virtual_key = _to_windows_hotkey((), "f5")
    assert mod_mask == 0
    assert virtual_key == 0x74


def test_windows_key_conversion_supports_generic_modifiers() -> None:
    mod_mask, virtual_key = _to_windows_hotkey(("ctrl", "shift"), "o")
    assert mod_mask == 0x0002 | 0x0004
    assert virtual_key == ord("O")


def test_windows_backend_dispatch_pipeline_invokes_action() -> None:
    client = _FakeWindowsClient()
    backend = WindowsHotkeyBackend(
        logger=logging.getLogger("test.backends"),
        platform_name="win32",
        client=client,
    )
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.backends"),
        dispatch_executor=InlineDispatchExecutor(),
        hotkey_backend=backend,
    )
    received: list[dict[str, object]] = []
    assert plugin.register_action(
        Action(
            id="overlay.toggle",
            label="Toggle Overlay",
            plugin="overlay",
            callback=lambda **kwargs: received.append(kwargs),
        )
    )
    binding = Binding(
        id="binding-win",
        hotkey="Ctrl+Shift+O",
        action_id="overlay.toggle",
        payload={"visible": True},
        enabled=True,
    )
    plugin.start()
    try:
        assert plugin.register_binding(binding) is True
        client.trigger("binding-win")
    finally:
        plugin.stop()

    assert received == [
        {
            "payload": {"visible": True},
            "source": "backend:windows-registerhotkey",
            "hotkey": "Ctrl+Shift+O",
        }
    ]


def test_x11_helper_conversion_and_matching() -> None:
    result = _to_x11_key(_FakeX11Mask, _FakeX11Keysym, _FakeX11DisplayForMask, ("ctrl", "shift"), "a")
    assert result == (38, _FakeX11Mask.ControlMask | _FakeX11Mask.ShiftMask)

    registration = _X11Registration(
        keycode=38,
        modifiers_mask=_FakeX11Mask.ControlMask,
        required_modifiers=(),
        grab_modifiers=(
            _FakeX11Mask.ControlMask,
            _FakeX11Mask.ControlMask | _FakeX11Mask.ShiftMask,
        ),
    )
    assert _registration_grab_modifiers(modifiers_mask=registration.modifiers_mask, required_modifiers=())
    assert _registration_matches_event(
        registration=registration,
        event_modifiers=_FakeX11Mask.ControlMask,
        pressed_keycodes=set(),
        side_keycodes={},
    )


def test_x11_event_modifiers_from_pressed() -> None:
    modifiers = _event_modifiers_from_pressed(
        pressed_keycodes={1, 2},
        side_keycodes={
            "ctrl_l": {1},
            "shift_l": {2},
            "alt_l": set(),
            "win_l": set(),
        },
    )
    assert modifiers & 0x04
    assert modifiers & 0x01


def test_x11_registration_grab_modifiers_side_specific_avoids_partial_fallbacks() -> None:
    modifiers = _registration_grab_modifiers(
        modifiers_mask=_FakeX11Mask.ControlMask | _FakeX11Mask.ShiftMask,
        required_modifiers=("ctrl_l", "shift_l"),
    )
    assert modifiers == (_FakeX11Mask.ControlMask | _FakeX11Mask.ShiftMask,)


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
