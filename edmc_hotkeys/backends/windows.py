"""Windows global hotkey backend using RegisterHotKey with fallback support."""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional, Protocol

from .base import BackendAvailability, HotkeyBackend, HotkeyCallback
from .hotkey_parser import parse_hotkey


WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008


class _POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", _POINT),
    ]


class LowLevelHookFallback(Protocol):
    """Fallback used for no-modifier hotkeys on Windows."""

    def availability(self) -> BackendAvailability:
        """Return fallback availability."""

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        """Start fallback listener."""

    def stop(self) -> None:
        """Stop fallback listener."""

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        """Register hotkey in fallback path."""

    def unregister_hotkey(self, binding_id: str) -> bool:
        """Unregister hotkey in fallback path."""


class NullLowLevelHookFallback:
    """Fallback placeholder when low-level hook support is unavailable."""

    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")

    def availability(self) -> BackendAvailability:
        return BackendAvailability(
            name="windows-low-level-hook",
            available=False,
            reason="Low-level hook fallback is not available",
        )

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        del on_hotkey
        return False

    def stop(self) -> None:
        return None

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        del binding_id, hotkey
        self._logger.warning("Low-level fallback is unavailable")
        return False

    def unregister_hotkey(self, binding_id: str) -> bool:
        del binding_id
        return False


@dataclass(frozen=True)
class _RegisteredWindowsHotkey:
    hotkey_id: int
    hotkey: str


class WindowsHotkeyBackend(HotkeyBackend):
    """Windows backend based on RegisterHotKey with fallback for no modifiers."""

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        platform_name: Optional[str] = None,
        user32: Optional[object] = None,
        kernel32: Optional[object] = None,
        fallback: Optional[LowLevelHookFallback] = None,
    ) -> None:
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")
        self._platform_name = platform_name or sys.platform
        self._user32 = user32
        self._kernel32 = kernel32
        self._fallback = fallback or NullLowLevelHookFallback(logger=self._logger)
        self._callback: Optional[HotkeyCallback] = None
        self._running = False
        self._registered: dict[str, _RegisteredWindowsHotkey] = {}
        self._id_to_binding: dict[int, str] = {}
        self._next_hotkey_id = 1
        self._loop_thread: Optional[threading.Thread] = None
        self._loop_thread_id: Optional[int] = None

    @property
    def name(self) -> str:
        return "windows-registerhotkey"

    def availability(self) -> BackendAvailability:
        if self._platform_name != "win32":
            return BackendAvailability(
                name=self.name,
                available=False,
                reason=f"Unsupported platform '{self._platform_name}'",
            )
        if self._resolve_user32() is None:
            return BackendAvailability(
                name=self.name,
                available=False,
                reason="Windows user32 APIs are unavailable",
            )
        return BackendAvailability(name=self.name, available=True)

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        availability = self.availability()
        if not availability.available:
            return False
        self._callback = on_hotkey
        self._running = True
        self._start_message_loop_if_supported()
        self._fallback.start(on_hotkey)
        return True

    def stop(self) -> None:
        for binding_id in list(self._registered.keys()):
            self.unregister_hotkey(binding_id)
        self._running = False
        self._fallback.stop()

        user32 = self._resolve_user32()
        if user32 is not None and self._loop_thread_id is not None and hasattr(user32, "PostThreadMessageW"):
            user32.PostThreadMessageW(self._loop_thread_id, WM_QUIT, 0, 0)
        if self._loop_thread is not None and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=0.5)
        self._loop_thread = None
        self._loop_thread_id = None
        self._callback = None

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        parsed = parse_hotkey(hotkey)
        if parsed is None:
            self._logger.warning("Could not parse hotkey '%s'", hotkey)
            return False

        modifiers, virtual_key = _to_windows_hotkey(parsed.modifiers, parsed.key)
        if virtual_key is None:
            self._logger.warning("Unsupported Windows hotkey key '%s'", parsed.key)
            return False

        if modifiers == 0:
            return self._fallback.register_hotkey(binding_id, hotkey)

        user32 = self._resolve_user32()
        if user32 is None:
            return False

        hotkey_id = self._next_hotkey_id
        self._next_hotkey_id += 1
        if not bool(user32.RegisterHotKey(None, hotkey_id, modifiers, virtual_key)):
            self._logger.warning("RegisterHotKey failed for binding '%s' (%s)", binding_id, hotkey)
            return False

        self._registered[binding_id] = _RegisteredWindowsHotkey(hotkey_id=hotkey_id, hotkey=hotkey)
        self._id_to_binding[hotkey_id] = binding_id
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        registered = self._registered.pop(binding_id, None)
        fallback_result = self._fallback.unregister_hotkey(binding_id)
        if registered is None:
            return fallback_result

        self._id_to_binding.pop(registered.hotkey_id, None)
        user32 = self._resolve_user32()
        if user32 is None:
            return False
        return bool(user32.UnregisterHotKey(None, registered.hotkey_id))

    def _resolve_user32(self) -> Optional[object]:
        if self._user32 is not None:
            return self._user32
        if self._platform_name != "win32":
            return None
        try:
            self._user32 = ctypes.windll.user32
            return self._user32
        except Exception:
            return None

    def _resolve_kernel32(self) -> Optional[object]:
        if self._kernel32 is not None:
            return self._kernel32
        if self._platform_name != "win32":
            return None
        try:
            self._kernel32 = ctypes.windll.kernel32
            return self._kernel32
        except Exception:
            return None

    def _start_message_loop_if_supported(self) -> None:
        user32 = self._resolve_user32()
        kernel32 = self._resolve_kernel32()
        if user32 is None or kernel32 is None:
            return
        if not hasattr(user32, "GetMessageW"):
            return
        if self._loop_thread is not None and self._loop_thread.is_alive():
            return

        self._loop_thread = threading.Thread(target=self._message_loop, daemon=True, name="edmc-hotkeys-winmsg")
        self._loop_thread.start()

    def _message_loop(self) -> None:
        user32 = self._resolve_user32()
        kernel32 = self._resolve_kernel32()
        if user32 is None or kernel32 is None:
            return

        try:
            self._loop_thread_id = int(kernel32.GetCurrentThreadId())
        except Exception:
            self._loop_thread_id = None

        msg = _MSG()
        while self._running:
            try:
                result = int(user32.GetMessageW(ctypes.byref(msg), None, 0, 0))
            except Exception:
                self._logger.exception("Windows message loop failed")
                break
            if result <= 0:
                break
            if msg.message == WM_HOTKEY:
                binding_id = self._id_to_binding.get(int(msg.wParam))
                if binding_id and self._callback is not None:
                    try:
                        self._callback(binding_id)
                    except Exception:
                        self._logger.exception("Windows hotkey callback failed")


def _to_windows_hotkey(modifiers: frozenset[str], key: str) -> tuple[int, Optional[int]]:
    mod_mask = 0
    if "alt" in modifiers:
        mod_mask |= MOD_ALT
    if "ctrl" in modifiers:
        mod_mask |= MOD_CONTROL
    if "shift" in modifiers:
        mod_mask |= MOD_SHIFT
    if "super" in modifiers:
        mod_mask |= MOD_WIN

    token = key.upper()
    if len(token) == 1 and token.isalnum():
        return mod_mask, ord(token)
    if token.startswith("F") and token[1:].isdigit():
        fn_number = int(token[1:])
        if 1 <= fn_number <= 24:
            return mod_mask, 0x70 + (fn_number - 1)

    special = {
        "SPACE": 0x20,
        "TAB": 0x09,
        "ENTER": 0x0D,
        "ESC": 0x1B,
        "ESCAPE": 0x1B,
    }
    return mod_mask, special.get(token)

