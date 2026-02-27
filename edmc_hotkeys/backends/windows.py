"""Windows global hotkey backend with side-specific modifier support."""

from __future__ import annotations

import ctypes
import logging
import queue
import sys
import threading
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

from .base import BackendAvailability, BackendCapabilities, HotkeyBackend, HotkeyCallback
from .hotkey_parser import parse_hotkey


WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_APP = 0x8000
WM_TASK = WM_APP + 1
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


class WindowsClient(Protocol):
    """Protocol for Windows hotkey client implementations."""

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        """Start Windows hotkey listener."""

    def stop(self) -> None:
        """Stop Windows hotkey listener."""

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        """Register hotkey for binding."""

    def unregister_hotkey(self, binding_id: str) -> bool:
        """Unregister hotkey for binding."""


class WindowsHotkeyBackend(HotkeyBackend):
    """Windows backend wrapper."""

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        platform_name: Optional[str] = None,
        client: Optional[WindowsClient] = None,
        user32: Optional[object] = None,
        kernel32: Optional[object] = None,
    ) -> None:
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")
        self._platform_name = platform_name or sys.platform
        self._client = client
        self._user32 = user32
        self._kernel32 = kernel32

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
        if self._client is None:
            self._client = _try_build_windows_client(
                logger=self._logger,
                platform_name=self._platform_name,
                user32=self._user32,
                kernel32=self._kernel32,
            )
        if self._client is None:
            return BackendAvailability(
                name=self.name,
                available=False,
                reason="Windows user32/kernel32 APIs are unavailable",
            )
        return BackendAvailability(name=self.name, available=True)

    def capabilities(self) -> BackendCapabilities:
        available = self.availability().available
        return BackendCapabilities(supports_side_specific_modifiers=available)

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        availability = self.availability()
        if not availability.available or self._client is None:
            self._logger.warning(
                "Hotkey backend '%s' unavailable: %s",
                self.name,
                availability.reason,
            )
            return False
        started = self._client.start(on_hotkey)
        if started:
            self._logger.info("Hotkey backend '%s' started", self.name)
        else:
            self._logger.warning("Hotkey backend '%s' failed to start", self.name)
        return started

    def stop(self) -> None:
        if self._client is not None:
            self._client.stop()
        self._logger.info("Hotkey backend '%s' stopped", self.name)

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        availability = self.availability()
        if self._client is None and not availability.available:
            self._logger.warning(
                "Cannot register Windows hotkey: backend '%s' unavailable: %s",
                self.name,
                availability.reason,
            )
            return False
        assert self._client is not None
        registered = self._client.register_hotkey(binding_id, hotkey)
        if not registered:
            self._logger.warning(
                "Backend '%s' failed to register hotkey: id=%s hotkey=%s",
                self.name,
                binding_id,
                hotkey,
            )
        return registered

    def unregister_hotkey(self, binding_id: str) -> bool:
        if self._client is None:
            self._logger.warning(
                "Cannot unregister Windows hotkey: backend '%s' client is unavailable",
                self.name,
            )
            return False
        unregistered = self._client.unregister_hotkey(binding_id)
        if not unregistered:
            self._logger.warning(
                "Backend '%s' failed to unregister hotkey: id=%s",
                self.name,
                binding_id,
            )
        return unregistered


@dataclass
class _ThreadTask:
    func: Callable[[], object]
    event: threading.Event = field(default_factory=threading.Event)
    result: Optional[object] = None
    error: Optional[BaseException] = None


@dataclass(frozen=True)
class _RegisteredWindowsHotkey:
    hotkey_id: int
    hotkey: str


@dataclass(frozen=True)
class _RegisteredSideHotkey:
    key_vk: int
    modifiers: tuple[str, ...]


class WindowsMessageLoopClient:
    """Windows hotkey client using RegisterHotKey and low-level hooks."""

    def __init__(self, *, logger: logging.Logger, user32: object, kernel32: object) -> None:
        self._logger = logger
        self._user32 = user32
        self._kernel32 = kernel32
        self._callback: Optional[HotkeyCallback] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._thread_ready = threading.Event()
        self._tasks: queue.Queue[_ThreadTask] = queue.Queue()
        self._hook_handle: Optional[int] = None
        self._hook_proc_ref = None
        self._registered: dict[str, _RegisteredWindowsHotkey] = {}
        self._id_to_binding: dict[int, str] = {}
        self._next_hotkey_id = 1
        self._side_bindings: dict[str, _RegisteredSideHotkey] = {}
        self._side_bindings_by_key: dict[int, set[str]] = {}
        self._active_side_bindings: set[str] = set()
        self._side_lock = threading.Lock()

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        if self._running:
            return True
        self._callback = on_hotkey
        self._running = True
        self._thread_ready.clear()
        self._thread = threading.Thread(target=self._message_loop, daemon=True, name="edmc-hotkeys-win")
        self._thread.start()
        if not self._thread_ready.wait(timeout=1.0):
            self._logger.warning("Windows message loop did not start")
            self._running = False
            return False
        return True

    def stop(self) -> None:
        if not self._running:
            return
        self._invoke_on_thread(self._unregister_all_hotkeys)
        self._running = False
        self._post_message(WM_QUIT)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None
        self._thread_id = None
        self._callback = None
        self._registered.clear()
        self._id_to_binding.clear()
        with self._side_lock:
            self._side_bindings.clear()
            self._side_bindings_by_key.clear()
            self._active_side_bindings.clear()

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        parsed = parse_hotkey(hotkey)
        if parsed is None:
            self._logger.warning("Could not parse Windows hotkey '%s'", hotkey)
            return False
        if _requires_side_specific(parsed.modifiers):
            return self._register_side_specific(binding_id, parsed)
        modifiers, virtual_key = _to_windows_hotkey(parsed.modifiers, parsed.key)
        if virtual_key is None:
            self._logger.warning("Unsupported Windows hotkey key '%s'", parsed.key)
            return False
        result = self._invoke_on_thread(
            lambda: self._register_with_registerhotkey(binding_id, hotkey, modifiers, virtual_key)
        )
        return bool(result)

    def unregister_hotkey(self, binding_id: str) -> bool:
        removed_side = self._unregister_side_specific(binding_id)
        removed_register = bool(self._invoke_on_thread(lambda: self._unregister_registerhotkey(binding_id)))
        return removed_side or removed_register

    def _register_side_specific(self, binding_id: str, parsed) -> bool:
        if not self._hook_handle:
            self._logger.warning(
                "Low-level hook unavailable; cannot register side-specific hotkey '%s'",
                binding_id,
            )
            return False
        key_vk = _to_windows_virtual_key(parsed.key)
        if key_vk is None:
            self._logger.warning("Unsupported Windows hotkey key '%s'", parsed.key)
            return False
        with self._side_lock:
            self._side_bindings[binding_id] = _RegisteredSideHotkey(key_vk=key_vk, modifiers=parsed.modifiers)
            self._side_bindings_by_key.setdefault(key_vk, set()).add(binding_id)
        return True

    def _unregister_side_specific(self, binding_id: str) -> bool:
        with self._side_lock:
            registration = self._side_bindings.pop(binding_id, None)
            if registration is None:
                return False
            self._active_side_bindings.discard(binding_id)
            bindings = self._side_bindings_by_key.get(registration.key_vk)
            if bindings is not None:
                bindings.discard(binding_id)
                if not bindings:
                    self._side_bindings_by_key.pop(registration.key_vk, None)
        return True

    def _register_with_registerhotkey(
        self,
        binding_id: str,
        hotkey: str,
        modifiers: int,
        virtual_key: int,
    ) -> bool:
        hotkey_id = self._next_hotkey_id
        self._next_hotkey_id += 1
        if not bool(self._user32.RegisterHotKey(None, hotkey_id, modifiers, virtual_key)):
            self._logger.warning("RegisterHotKey failed for binding '%s' (%s)", binding_id, hotkey)
            return False
        self._registered[binding_id] = _RegisteredWindowsHotkey(hotkey_id=hotkey_id, hotkey=hotkey)
        self._id_to_binding[hotkey_id] = binding_id
        return True

    def _unregister_registerhotkey(self, binding_id: str) -> bool:
        registration = self._registered.pop(binding_id, None)
        if registration is None:
            return False
        self._id_to_binding.pop(registration.hotkey_id, None)
        return bool(self._user32.UnregisterHotKey(None, registration.hotkey_id))

    def _unregister_all_hotkeys(self) -> None:
        for binding_id in list(self._registered.keys()):
            self._unregister_registerhotkey(binding_id)
        with self._side_lock:
            self._side_bindings.clear()
            self._side_bindings_by_key.clear()
            self._active_side_bindings.clear()

    def _message_loop(self) -> None:
        try:
            self._thread_id = int(self._kernel32.GetCurrentThreadId())
        except Exception:
            self._thread_id = None
        msg = _MSG()
        if hasattr(self._user32, "PeekMessageW"):
            try:
                self._user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
            except Exception:
                pass
        self._install_hook()
        self._thread_ready.set()

        while self._running:
            try:
                result = int(self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0))
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
            elif msg.message == WM_TASK:
                self._drain_tasks()

        self._remove_hook()

    def _install_hook(self) -> None:
        hook_proc_type = ctypes.WINFUNCTYPE(wintypes.LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

        def _proc(n_code: int, w_param: int, l_param: int) -> int:
            return self._keyboard_proc(n_code, w_param, l_param)

        self._hook_proc_ref = hook_proc_type(_proc)
        module_handle = None
        if hasattr(self._kernel32, "GetModuleHandleW"):
            try:
                module_handle = self._kernel32.GetModuleHandleW(None)
            except Exception:
                module_handle = None
        try:
            handle = self._user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_proc_ref, module_handle, 0)
            self._hook_handle = int(handle) if handle else None
        except Exception:
            self._hook_handle = None
        if not self._hook_handle:
            self._logger.warning("Failed to install low-level keyboard hook")

    def _remove_hook(self) -> None:
        if self._hook_handle and hasattr(self._user32, "UnhookWindowsHookEx"):
            try:
                self._user32.UnhookWindowsHookEx(self._hook_handle)
            except Exception:
                self._logger.debug("Failed to unhook low-level keyboard hook", exc_info=True)
        self._hook_handle = None
        self._hook_proc_ref = None

    def _keyboard_proc(self, n_code: int, w_param: int, l_param: int) -> int:
        if n_code == HC_ACTION:
            try:
                event = ctypes.cast(l_param, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                key_vk = int(event.vkCode)
                if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    self._handle_low_level_keydown(key_vk)
                elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                    self._handle_low_level_keyup(key_vk)
            except Exception:
                self._logger.exception("Low-level hook callback failed")
        return int(self._user32.CallNextHookEx(self._hook_handle or 0, n_code, w_param, l_param))

    def _handle_low_level_keydown(self, key_vk: int) -> None:
        binding_ids = self._side_bindings_for_key(key_vk)
        if not binding_ids:
            self._prune_inactive_side_bindings()
            return
        for binding_id in binding_ids:
            with self._side_lock:
                if binding_id in self._active_side_bindings:
                    continue
                registration = self._side_bindings.get(binding_id)
            if registration is None:
                continue
            if not self._side_modifiers_match(registration.modifiers):
                continue
            with self._side_lock:
                self._active_side_bindings.add(binding_id)
            if self._callback is not None:
                try:
                    self._callback(binding_id)
                except Exception:
                    self._logger.exception("Windows low-level hotkey callback failed")
        self._prune_inactive_side_bindings()

    def _handle_low_level_keyup(self, key_vk: int) -> None:
        with self._side_lock:
            binding_ids = list(self._side_bindings_by_key.get(key_vk, set()))
            for binding_id in binding_ids:
                self._active_side_bindings.discard(binding_id)
        self._prune_inactive_side_bindings()

    def _prune_inactive_side_bindings(self) -> None:
        with self._side_lock:
            active_bindings = list(self._active_side_bindings)
        for binding_id in active_bindings:
            registration = self._side_bindings.get(binding_id)
            if registration is None:
                with self._side_lock:
                    self._active_side_bindings.discard(binding_id)
                continue
            if not self._is_pressed(registration.key_vk):
                with self._side_lock:
                    self._active_side_bindings.discard(binding_id)
                continue
            if not self._side_modifiers_match(registration.modifiers):
                with self._side_lock:
                    self._active_side_bindings.discard(binding_id)

    def _side_bindings_for_key(self, key_vk: int) -> list[str]:
        with self._side_lock:
            return list(self._side_bindings_by_key.get(key_vk, set()))

    def _side_modifiers_match(self, required_modifiers: tuple[str, ...]) -> bool:
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
        try:
            return bool(int(self._user32.GetAsyncKeyState(vk_code)) & 0x8000)
        except Exception:
            return False

    def _invoke_on_thread(self, func: Callable[[], object]) -> Optional[object]:
        if not self._running or self._thread_id is None:
            return None
        task = _ThreadTask(func=func)
        self._tasks.put(task)
        self._post_message(WM_TASK)
        if not task.event.wait(timeout=1.0):
            self._logger.warning("Windows message loop task timed out")
            return None
        if task.error is not None:
            self._logger.exception("Windows message loop task failed", exc_info=task.error)
            return None
        return task.result

    def _post_message(self, message: int) -> None:
        if self._thread_id is None or not hasattr(self._user32, "PostThreadMessageW"):
            return
        try:
            self._user32.PostThreadMessageW(self._thread_id, message, 0, 0)
        except Exception:
            self._logger.debug("Failed to post Windows message", exc_info=True)

    def _drain_tasks(self) -> None:
        while True:
            try:
                task = self._tasks.get_nowait()
            except queue.Empty:
                break
            try:
                task.result = task.func()
            except BaseException as exc:
                task.error = exc
            finally:
                task.event.set()


def _try_build_windows_client(
    *,
    logger: logging.Logger,
    platform_name: str,
    user32: Optional[object],
    kernel32: Optional[object],
) -> Optional[WindowsMessageLoopClient]:
    if platform_name != "win32":
        return None
    if user32 is None:
        try:
            user32 = ctypes.windll.user32
        except Exception:
            user32 = None
    if kernel32 is None:
        try:
            kernel32 = ctypes.windll.kernel32
        except Exception:
            kernel32 = None
    if user32 is None or kernel32 is None:
        return None
    required_user32 = {
        "RegisterHotKey",
        "UnregisterHotKey",
        "GetMessageW",
        "PostThreadMessageW",
        "CallNextHookEx",
        "SetWindowsHookExW",
        "UnhookWindowsHookEx",
        "GetAsyncKeyState",
    }
    if any(not hasattr(user32, symbol) for symbol in required_user32):
        logger.debug("Windows user32 APIs missing required symbols")
        return None
    if not hasattr(kernel32, "GetCurrentThreadId"):
        logger.debug("Windows kernel32 APIs missing required symbols")
        return None
    return WindowsMessageLoopClient(logger=logger, user32=user32, kernel32=kernel32)


def _requires_side_specific(modifiers: tuple[str, ...]) -> bool:
    return any(token.endswith("_l") or token.endswith("_r") for token in modifiers)


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
