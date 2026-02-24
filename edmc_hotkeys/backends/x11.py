"""Linux X11 backend using python-xlib when available."""

from __future__ import annotations

import importlib
import logging
import sys
import threading
from dataclasses import dataclass
from typing import Optional, Protocol

from .base import BackendAvailability, HotkeyBackend, HotkeyCallback
from .hotkey_parser import parse_hotkey


class X11Client(Protocol):
    """Protocol for X11 client implementations."""

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        """Start X11 listener."""

    def stop(self) -> None:
        """Stop X11 listener."""

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        """Register hotkey."""

    def unregister_hotkey(self, binding_id: str) -> bool:
        """Unregister hotkey."""


class X11HotkeyBackend(HotkeyBackend):
    """X11 backend wrapper."""

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        platform_name: Optional[str] = None,
        client: Optional[X11Client] = None,
    ) -> None:
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")
        self._platform_name = platform_name or sys.platform
        self._client = client

    @property
    def name(self) -> str:
        return "linux-x11"

    def availability(self) -> BackendAvailability:
        if not self._platform_name.startswith("linux"):
            return BackendAvailability(
                name=self.name,
                available=False,
                reason=f"Unsupported platform '{self._platform_name}'",
            )
        if self._client is None:
            self._client = _try_build_python_xlib_client(logger=self._logger)
        if self._client is None:
            return BackendAvailability(
                name=self.name,
                available=False,
                reason="python-xlib is unavailable",
            )
        return BackendAvailability(name=self.name, available=True)

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        if not self.availability().available or self._client is None:
            return False
        return self._client.start(on_hotkey)

    def stop(self) -> None:
        if self._client is not None:
            self._client.stop()

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        if self._client is None and not self.availability().available:
            return False
        assert self._client is not None
        return self._client.register_hotkey(binding_id, hotkey)

    def unregister_hotkey(self, binding_id: str) -> bool:
        if self._client is None:
            return False
        return self._client.unregister_hotkey(binding_id)


@dataclass(frozen=True)
class _X11Registration:
    keycode: int
    modifiers: int


class PythonXlibClient:
    """In-process X11 hotkey client using python-xlib."""

    def __init__(self, *, logger: logging.Logger, modules: dict[str, object]) -> None:
        self._logger = logger
        self._X = modules["X"]
        self._XK = modules["XK"]
        display_module = modules["display"]
        self._display = display_module.Display()
        self._root = self._display.screen().root
        self._callback: Optional[HotkeyCallback] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._registrations: dict[str, _X11Registration] = {}
        self._reverse_lookup: dict[tuple[int, int], str] = {}
        self._lock_modifiers = (
            0,
            self._X.LockMask,
            self._X.Mod2Mask,
            self._X.LockMask | self._X.Mod2Mask,
        )
        self._allowed_modifiers = (
            self._X.ShiftMask | self._X.ControlMask | self._X.Mod1Mask | self._X.Mod4Mask
        )

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        if self._running:
            return True
        self._callback = on_hotkey
        self._running = True
        self._thread = threading.Thread(target=self._event_loop, daemon=True, name="edmc-hotkeys-x11")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        try:
            self._display.close()
        except Exception:
            pass
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        parsed = parse_hotkey(hotkey)
        if parsed is None:
            self._logger.warning("Could not parse X11 hotkey '%s'", hotkey)
            return False
        result = _to_x11_key(self._X, self._XK, self._display, parsed.modifiers, parsed.key)
        if result is None:
            self._logger.warning("Unsupported X11 hotkey '%s'", hotkey)
            return False
        keycode, modifiers = result

        try:
            for lock_modifier in self._lock_modifiers:
                self._root.grab_key(
                    keycode,
                    modifiers | lock_modifier,
                    False,
                    self._X.GrabModeAsync,
                    self._X.GrabModeAsync,
                )
            self._display.sync()
        except Exception:
            self._logger.exception("Failed to register X11 hotkey '%s'", hotkey)
            return False

        self._registrations[binding_id] = _X11Registration(keycode=keycode, modifiers=modifiers)
        self._reverse_lookup[(keycode, modifiers)] = binding_id
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        registration = self._registrations.pop(binding_id, None)
        if registration is None:
            return False
        self._reverse_lookup.pop((registration.keycode, registration.modifiers), None)
        try:
            for lock_modifier in self._lock_modifiers:
                self._root.ungrab_key(registration.keycode, registration.modifiers | lock_modifier)
            self._display.sync()
            return True
        except Exception:
            self._logger.exception("Failed to unregister X11 hotkey for '%s'", binding_id)
            return False

    def _event_loop(self) -> None:
        while self._running:
            try:
                event = self._display.next_event()
            except Exception:
                if self._running:
                    self._logger.exception("X11 event loop failed")
                break
            if event.type != self._X.KeyPress:
                continue
            modifiers = int(event.state) & self._allowed_modifiers
            binding_id = self._reverse_lookup.get((int(event.detail), modifiers))
            if binding_id is None or self._callback is None:
                continue
            try:
                self._callback(binding_id)
            except Exception:
                self._logger.exception("X11 hotkey callback failed")


def _try_build_python_xlib_client(*, logger: logging.Logger) -> Optional[PythonXlibClient]:
    modules = _load_python_xlib_modules()
    if modules is None:
        return None
    try:
        return PythonXlibClient(logger=logger, modules=modules)
    except Exception:
        logger.exception("Could not initialize python-xlib client")
        return None


def _load_python_xlib_modules() -> Optional[dict[str, object]]:
    try:
        x_module = importlib.import_module("Xlib.X")
        xk_module = importlib.import_module("Xlib.XK")
        display_module = importlib.import_module("Xlib.display")
    except Exception:
        return None
    return {"X": x_module, "XK": xk_module, "display": display_module}


def _to_x11_key(X: object, XK: object, display: object, modifiers: frozenset[str], key: str) -> Optional[tuple[int, int]]:
    mod_mask = 0
    if "shift" in modifiers:
        mod_mask |= int(X.ShiftMask)
    if "ctrl" in modifiers:
        mod_mask |= int(X.ControlMask)
    if "alt" in modifiers:
        mod_mask |= int(X.Mod1Mask)
    if "super" in modifiers:
        mod_mask |= int(X.Mod4Mask)

    keysym_token = _to_x11_keysym_token(key)
    if keysym_token is None:
        return None
    keysym = int(XK.string_to_keysym(keysym_token))
    if keysym == 0:
        return None
    keycode = int(display.keysym_to_keycode(keysym))
    if keycode == 0:
        return None
    return keycode, mod_mask


def _to_x11_keysym_token(key: str) -> Optional[str]:
    token = key.strip()
    if not token:
        return None
    if len(token) == 1 and token.isalnum():
        return token.lower()
    upper = token.upper()
    if upper.startswith("F") and upper[1:].isdigit():
        fn_number = int(upper[1:])
        if 1 <= fn_number <= 24:
            return upper
    lookup = {
        "SPACE": "space",
        "TAB": "Tab",
        "ENTER": "Return",
        "ESC": "Escape",
        "ESCAPE": "Escape",
    }
    return lookup.get(upper)
