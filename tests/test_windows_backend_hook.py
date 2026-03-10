from __future__ import annotations

import ctypes
import logging

from edmc_hotkeys.backends.windows import (
    HC_ACTION,
    VK_LMENU,
    VK_LSHIFT,
    VK_RSHIFT,
    WM_KEYDOWN,
    WM_KEYUP,
    WindowsMessageLoopClient,
    _KBDLLHOOKSTRUCT,
    _RegisteredSideHotkey,
)


class _FakeUser32:
    def __init__(self) -> None:
        self.key_states: dict[int, int] = {}
        self.call_next_calls: list[tuple[int, int, int, int]] = []

    def CallNextHookEx(self, hook_handle: int, n_code: int, w_param: int, l_param: int) -> int:
        self.call_next_calls.append((hook_handle, n_code, w_param, l_param))
        return 4242

    def GetAsyncKeyState(self, vk_code: int) -> int:
        return self.key_states.get(vk_code, 0)


def _event_lparam(vk_code: int) -> tuple[_KBDLLHOOKSTRUCT, int]:
    event = _KBDLLHOOKSTRUCT()
    event.vkCode = vk_code
    return event, ctypes.addressof(event)


def _build_side_binding_client(*, key_vk: int) -> tuple[WindowsMessageLoopClient, _FakeUser32]:
    user32 = _FakeUser32()
    client = WindowsMessageLoopClient(
        logger=logging.getLogger("test.windows_hook"),
        user32=user32,
        kernel32=object(),
    )
    client._side_bindings["binding-side"] = _RegisteredSideHotkey(
        key_vk=key_vk,
        modifiers=("alt_l", "shift_l"),
    )
    client._side_bindings_by_key[key_vk] = {"binding-side"}
    return client, user32


def test_keyboard_proc_swallows_matched_side_specific_keydown() -> None:
    client, user32 = _build_side_binding_client(key_vk=ord("P"))
    user32.key_states[VK_LMENU] = 0x8000
    user32.key_states[VK_LSHIFT] = 0x8000
    user32.key_states[ord("P")] = 0x8000
    triggered: list[str] = []
    client._callback = triggered.append

    _event, l_param = _event_lparam(ord("P"))
    result = client._keyboard_proc(HC_ACTION, WM_KEYDOWN, l_param)

    assert result == 1
    assert triggered == ["binding-side"]
    assert user32.call_next_calls == []


def test_keyboard_proc_swallows_repeat_keydown_for_active_side_binding() -> None:
    client, user32 = _build_side_binding_client(key_vk=ord("P"))
    user32.key_states[VK_LMENU] = 0x8000
    user32.key_states[VK_LSHIFT] = 0x8000
    user32.key_states[ord("P")] = 0x8000
    triggered: list[str] = []
    client._callback = triggered.append
    _event, l_param = _event_lparam(ord("P"))

    first = client._keyboard_proc(HC_ACTION, WM_KEYDOWN, l_param)
    second = client._keyboard_proc(HC_ACTION, WM_KEYDOWN, l_param)

    assert first == 1
    assert second == 1
    assert triggered == ["binding-side"]
    assert user32.call_next_calls == []


def test_keyboard_proc_swallows_matched_side_specific_keyup() -> None:
    client, user32 = _build_side_binding_client(key_vk=ord("P"))
    user32.key_states[VK_LMENU] = 0x8000
    user32.key_states[VK_LSHIFT] = 0x8000
    user32.key_states[ord("P")] = 0x8000
    client._callback = lambda _binding_id: None
    _keydown_event, keydown_l_param = _event_lparam(ord("P"))

    keydown_result = client._keyboard_proc(HC_ACTION, WM_KEYDOWN, keydown_l_param)
    user32.key_states[ord("P")] = 0
    _keyup_event, keyup_l_param = _event_lparam(ord("P"))
    keyup_result = client._keyboard_proc(HC_ACTION, WM_KEYUP, keyup_l_param)

    assert keydown_result == 1
    assert keyup_result == 1
    assert "binding-side" not in client._active_side_bindings
    assert user32.call_next_calls == []


def test_keyboard_proc_forwards_unmatched_keydown() -> None:
    client, user32 = _build_side_binding_client(key_vk=ord("P"))
    triggered: list[str] = []
    client._callback = triggered.append

    _event, l_param = _event_lparam(ord("P"))
    result = client._keyboard_proc(HC_ACTION, WM_KEYDOWN, l_param)

    assert result == 4242
    assert triggered == []
    assert len(user32.call_next_calls) == 1


def test_keyboard_proc_forwards_when_shift_side_differs() -> None:
    client, user32 = _build_side_binding_client(key_vk=ord("P"))
    # Binding requires alt_l+shift_l; pressing alt_l+shift_r should not match.
    user32.key_states[VK_LMENU] = 0x8000
    user32.key_states[VK_RSHIFT] = 0x8000
    user32.key_states[ord("P")] = 0x8000
    triggered: list[str] = []
    client._callback = triggered.append

    _event, l_param = _event_lparam(ord("P"))
    result = client._keyboard_proc(HC_ACTION, WM_KEYDOWN, l_param)

    assert result == 4242
    # Side-specific action should not fire on opposite-side Shift and event is forwarded.
    assert triggered == []
    assert len(user32.call_next_calls) == 1
