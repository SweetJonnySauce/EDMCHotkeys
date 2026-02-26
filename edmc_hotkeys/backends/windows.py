"""Windows global hotkey backend with optional low-level side-specific support."""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional, Protocol

from ..feature_flags import ENABLE_WINDOWS_LOW_LEVEL_HOOK
from .base import BackendAvailability, BackendCapabilities, HotkeyBackend, HotkeyCallback
from .hotkey_parser import parse_hotkey


WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WH_KEYBOARD_LL = 13
HC_ACTION = 0
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LWIN = 0x5B
VK_RWIN = 0x5C
_ULONG_PTR = getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)


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


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", _ULONG_PTR),
    ]


class LowLevelHookFallback(Protocol):
    """Low-level path for no-modifier and side-specific hotkeys on Windows."""

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

    def __init__(self, *, logger: Optional[logging.Logger] = None, reason: str = "Low-level hook is disabled") -> None:
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")
        self._reason = reason

    def availability(self) -> BackendAvailability:
        return BackendAvailability(
            name="windows-low-level-hook",
            available=False,
            reason=self._reason,
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
class _RegisteredLowLevelHotkey:
    key_vk: int
    modifiers: tuple[str, ...]


class WindowsLowLevelHookFallback:
    """Low-level keyboard hook fallback for side-specific modifier handling."""

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        platform_name: Optional[str] = None,
        user32: Optional[object] = None,
        kernel32: Optional[object] = None,
    ) -> None:
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")
        self._platform_name = platform_name or sys.platform
        self._user32 = user32
        self._kernel32 = kernel32
        self._callback: Optional[HotkeyCallback] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._hook_handle: Optional[int] = None
        self._hook_proc_ref = None
        self._registered: dict[str, _RegisteredLowLevelHotkey] = {}

    def availability(self) -> BackendAvailability:
        if self._platform_name != "win32":
            return BackendAvailability(
                name="windows-low-level-hook",
                available=False,
                reason=f"Unsupported platform '{self._platform_name}'",
            )
        user32 = self._resolve_user32()
        kernel32 = self._resolve_kernel32()
        if user32 is None or kernel32 is None:
            return BackendAvailability(
                name="windows-low-level-hook",
                available=False,
                reason="Windows user32/kernel32 APIs are unavailable",
            )
        required_symbols = (
            "SetWindowsHookExW",
            "UnhookWindowsHookEx",
            "CallNextHookEx",
            "GetMessageW",
            "PostThreadMessageW",
            "GetAsyncKeyState",
        )
        if any(not hasattr(user32, symbol) for symbol in required_symbols):
            return BackendAvailability(
                name="windows-low-level-hook",
                available=False,
                reason="Required Windows hook APIs are unavailable",
            )
        return BackendAvailability(name="windows-low-level-hook", available=True)

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        if not self.availability().available:
            return False
        self._callback = on_hotkey
        self._running = True
        if self._thread is not None and self._thread.is_alive():
            return True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="edmc-hotkeys-winll")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        user32 = self._resolve_user32()
        if user32 is not None and self._thread_id is not None and hasattr(user32, "PostThreadMessageW"):
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None
        self._thread_id = None
        self._callback = None
        self._registered.clear()

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        parsed = parse_hotkey(hotkey)
        if parsed is None:
            self._logger.warning("Could not parse low-level hotkey '%s'", hotkey)
            return False
        key_vk = _to_windows_virtual_key(parsed.key)
        if key_vk is None:
            self._logger.warning("Unsupported key token for low-level hotkey '%s'", hotkey)
            return False
        self._registered[binding_id] = _RegisteredLowLevelHotkey(key_vk=key_vk, modifiers=parsed.modifiers)
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        return self._registered.pop(binding_id, None) is not None

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

    def _run_loop(self) -> None:
        user32 = self._resolve_user32()
        kernel32 = self._resolve_kernel32()
        if user32 is None or kernel32 is None:
            return

        try:
            self._thread_id = int(kernel32.GetCurrentThreadId())
        except Exception:
            self._thread_id = None

        hook_proc_type = ctypes.WINFUNCTYPE(wintypes.LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

        def _proc(n_code: int, w_param: int, l_param: int) -> int:
            return self._keyboard_proc(n_code, w_param, l_param)

        self._hook_proc_ref = hook_proc_type(_proc)
        module_handle = kernel32.GetModuleHandleW(None) if hasattr(kernel32, "GetModuleHandleW") else None
        try:
            self._hook_handle = int(user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_proc_ref, module_handle, 0))
        except Exception:
            self._hook_handle = None
        if not self._hook_handle:
            self._logger.warning("Failed to install low-level keyboard hook")
            return

        msg = _MSG()
        while self._running:
            try:
                result = int(user32.GetMessageW(ctypes.byref(msg), None, 0, 0))
            except Exception:
                self._logger.exception("Low-level hook message loop failed")
                break
            if result <= 0:
                break

        try:
            user32.UnhookWindowsHookEx(self._hook_handle)
        except Exception:
            self._logger.debug("Failed to unhook low-level keyboard hook", exc_info=True)
        self._hook_handle = None
        self._hook_proc_ref = None

    def _keyboard_proc(self, n_code: int, w_param: int, l_param: int) -> int:
        user32 = self._resolve_user32()
        if user32 is None:
            return 0

        if n_code == HC_ACTION and w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
            try:
                event = ctypes.cast(l_param, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                key_vk = int(event.vkCode)
                for binding_id in self._matching_bindings(key_vk):
                    if self._callback is not None:
                        self._callback(binding_id)
            except Exception:
                self._logger.exception("Low-level hook callback failed")
        return int(user32.CallNextHookEx(self._hook_handle or 0, n_code, w_param, l_param))

    def _matching_bindings(self, key_vk: int) -> list[str]:
        matches: list[str] = []
        for binding_id, registration in self._registered.items():
            if registration.key_vk != key_vk:
                continue
            if self._modifiers_match(registration.modifiers):
                matches.append(binding_id)
        return matches

    def _modifiers_match(self, required_modifiers: tuple[str, ...]) -> bool:
        required = set(required_modifiers)
        groups = {
            "ctrl": {"ctrl_l", "ctrl_r"},
            "alt": {"alt_l", "alt_r"},
            "shift": {"shift_l", "shift_r"},
            "win": {"win_l", "win_r"},
        }
        state = {
            "ctrl_l": self._is_pressed(VK_LCONTROL),
            "ctrl_r": self._is_pressed(VK_RCONTROL),
            "alt_l": self._is_pressed(VK_LMENU),
            "alt_r": self._is_pressed(VK_RMENU),
            "shift_l": self._is_pressed(VK_LSHIFT),
            "shift_r": self._is_pressed(VK_RSHIFT),
            "win_l": self._is_pressed(VK_LWIN),
            "win_r": self._is_pressed(VK_RWIN),
        }

        for token in required:
            if token in groups:
                continue
            if token not in state:
                return False
            if not state.get(token, False):
                return False

        for group_name, tokens in groups.items():
            requires_group = group_name in required
            required_sides = required.intersection(tokens)
            if requires_group and not any(state.get(token, False) for token in tokens):
                return False
            if required_sides and not all(state.get(token, False) for token in required_sides):
                return False
            if requires_group or required_sides:
                continue
            if any(state.get(token, False) for token in tokens):
                return False
        return True

    def _is_pressed(self, vk_code: int) -> bool:
        user32 = self._resolve_user32()
        if user32 is None:
            return False
        try:
            return bool(int(user32.GetAsyncKeyState(vk_code)) & 0x8000)
        except Exception:
            return False


@dataclass(frozen=True)
class _RegisteredWindowsHotkey:
    hotkey_id: int
    hotkey: str


class WindowsHotkeyBackend(HotkeyBackend):
    """Windows backend with RegisterHotKey + optional low-level side-specific path."""

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
        self._low_level_enabled = ENABLE_WINDOWS_LOW_LEVEL_HOOK
        if fallback is not None:
            self._fallback = fallback
        elif self._low_level_enabled:
            self._fallback = WindowsLowLevelHookFallback(
                logger=self._logger,
                platform_name=self._platform_name,
                user32=self._user32,
                kernel32=self._kernel32,
            )
        else:
            self._fallback = NullLowLevelHookFallback(
                logger=self._logger,
                reason="Low-level hook disabled (set EDMC_HOTKEYS_ENABLE_WINDOWS_LOW_LEVEL_HOOK=1 to enable)",
            )
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

    def capabilities(self) -> BackendCapabilities:
        availability = self._fallback.availability()
        return BackendCapabilities(supports_side_specific_modifiers=availability.available)

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

        requires_side_specific = any(_is_side_specific_modifier(token) for token in parsed.modifiers)
        if requires_side_specific:
            if not self.capabilities().supports_side_specific_modifiers:
                self._logger.warning(
                    "Side-specific modifiers require low-level hook support, but it is unavailable"
                )
                return False
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


def _to_windows_hotkey(modifiers: tuple[str, ...], key: str) -> tuple[int, Optional[int]]:
    mod_mask = _to_windows_modifier_mask(modifiers)
    return mod_mask, _to_windows_virtual_key(key)


def _to_windows_modifier_mask(modifiers: tuple[str, ...]) -> int:
    mod_mask = 0
    for token in modifiers:
        group = _modifier_group_for_token(token)
        if group == "alt":
            mod_mask |= MOD_ALT
        elif group == "ctrl":
            mod_mask |= MOD_CONTROL
        elif group == "shift":
            mod_mask |= MOD_SHIFT
        elif group == "win":
            mod_mask |= MOD_WIN
    return mod_mask


def _modifier_group_for_token(token: str) -> str | None:
    if token == "ctrl" or token.startswith("ctrl_"):
        return "ctrl"
    if token == "alt" or token.startswith("alt_"):
        return "alt"
    if token == "shift" or token.startswith("shift_"):
        return "shift"
    if token == "win" or token.startswith("win_"):
        return "win"
    return None


def _is_side_specific_modifier(token: str) -> bool:
    return token.endswith("_l") or token.endswith("_r")


def _to_windows_virtual_key(key: str) -> Optional[int]:
    token = key.upper()
    if len(token) == 1 and token.isalnum():
        return ord(token)
    if token.startswith("F") and token[1:].isdigit():
        fn_number = int(token[1:])
        if 1 <= fn_number <= 24:
            return 0x70 + (fn_number - 1)

    special = {
        "SPACE": 0x20,
        "TAB": 0x09,
        "ENTER": 0x0D,
        "ESC": 0x1B,
        "ESCAPE": 0x1B,
    }
    return special.get(token)
