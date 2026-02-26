"""Linux X11 backend using python-xlib when available."""

from __future__ import annotations

import importlib
import logging
import sys
import threading
import time
from dataclasses import dataclass
from typing import Optional, Protocol

from .base import BackendAvailability, BackendCapabilities, HotkeyBackend, HotkeyCallback
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

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_side_specific_modifiers=True)

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
                "Cannot register X11 hotkey: backend '%s' unavailable: %s",
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
                "Cannot unregister X11 hotkey: backend '%s' client is unavailable",
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


@dataclass(frozen=True)
class _X11Registration:
    keycode: int
    modifiers_mask: int
    required_modifiers: tuple[str, ...]
    grab_modifiers: tuple[int, ...]


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
        self._reverse_lookup: dict[int, list[str]] = {}
        self._active_side_bindings: dict[str, bool] = {}
        self._lock_modifiers = (
            0,
            self._X.LockMask,
            self._X.Mod2Mask,
            self._X.LockMask | self._X.Mod2Mask,
        )
        self._allowed_modifiers = (
            self._X.ShiftMask | self._X.ControlMask | self._X.Mod1Mask | self._X.Mod4Mask
        )
        self._side_modifier_keycodes = _resolve_side_modifier_keycodes(self._XK, self._display)
        self._poll_interval_seconds = 0.01

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
        self._callback = None
        self._registrations.clear()
        self._reverse_lookup.clear()
        self._active_side_bindings.clear()

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

        # Side-specific bindings are evaluated via keymap polling to avoid
        # passive-grab delivery variance across X11 setups.
        if parsed.modifiers:
            grab_modifiers: tuple[int, ...] = ()
        else:
            grab_modifiers = _registration_grab_modifiers(
                modifiers_mask=modifiers,
                required_modifiers=parsed.modifiers,
            )
            if not grab_modifiers:
                self._logger.warning("No X11 grab modifiers resolved for hotkey '%s'", hotkey)
                return False
            if not self._register_grabs(keycode=keycode, modifiers=grab_modifiers, hotkey=hotkey):
                return False

        self._registrations[binding_id] = _X11Registration(
            keycode=keycode,
            modifiers_mask=modifiers,
            required_modifiers=parsed.modifiers,
            grab_modifiers=grab_modifiers,
        )
        if grab_modifiers:
            self._reverse_lookup.setdefault(keycode, []).append(binding_id)
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        registration = self._registrations.pop(binding_id, None)
        if registration is None:
            return False
        self._active_side_bindings.pop(binding_id, None)

        if registration.grab_modifiers:
            candidates = self._reverse_lookup.get(registration.keycode, [])
            self._reverse_lookup[registration.keycode] = [candidate for candidate in candidates if candidate != binding_id]
            if not self._reverse_lookup[registration.keycode]:
                self._reverse_lookup.pop(registration.keycode, None)
        try:
            for modifiers_mask in registration.grab_modifiers:
                for lock_modifier in self._lock_modifiers:
                    self._root.ungrab_key(registration.keycode, modifiers_mask | lock_modifier)
            self._display.sync()
            return True
        except Exception:
            self._logger.exception("Failed to unregister X11 hotkey for '%s'", binding_id)
            return False

    def _register_grabs(self, *, keycode: int, modifiers: tuple[int, ...], hotkey: str) -> bool:
        primary_mask = modifiers[0]
        for modifiers_mask in modifiers:
            for lock_modifier in self._lock_modifiers:
                try:
                    self._root.grab_key(
                        keycode,
                        modifiers_mask | lock_modifier,
                        False,
                        self._X.GrabModeAsync,
                        self._X.GrabModeAsync,
                    )
                except Exception:
                    if modifiers_mask == primary_mask:
                        self._logger.exception("Failed to register X11 hotkey '%s'", hotkey)
                        return False
                    self._logger.debug(
                        "Skipping X11 fallback grab for hotkey '%s' (mask=0x%X)",
                        hotkey,
                        modifiers_mask | lock_modifier,
                    )
        try:
            self._display.sync()
        except Exception:
            self._logger.exception("Failed to sync X11 hotkey registration for '%s'", hotkey)
            return False
        return True

    def _event_loop(self) -> None:
        while self._running:
            try:
                had_event = False
                while self._running and self._display.pending_events():
                    had_event = True
                    event = self._display.next_event()
                    if event.type != self._X.KeyPress:
                        continue
                    keycode = int(event.detail)
                    candidates = self._reverse_lookup.get(keycode, [])
                    if not candidates or self._callback is None:
                        continue
                    pressed_keycodes = _pressed_keycodes(self._display)
                    event_modifiers = int(event.state) & self._allowed_modifiers
                    for binding_id in list(candidates):
                        registration = self._registrations.get(binding_id)
                        if registration is None:
                            continue
                        if not _registration_matches_event(
                            registration=registration,
                            event_modifiers=event_modifiers,
                            pressed_keycodes=pressed_keycodes,
                            side_keycodes=self._side_modifier_keycodes,
                        ):
                            continue
                        self._invoke_callback(binding_id)
                self._poll_side_specific_bindings()
                if not had_event:
                    time.sleep(self._poll_interval_seconds)
            except Exception:
                if self._running:
                    self._logger.exception("X11 event loop failed")
                break

    def _poll_side_specific_bindings(self) -> None:
        if self._callback is None:
            return
        if not any(registration.required_modifiers for registration in self._registrations.values()):
            return

        pressed_keycodes = _pressed_keycodes(self._display)
        event_modifiers = _event_modifiers_from_pressed(
            pressed_keycodes=pressed_keycodes,
            side_keycodes=self._side_modifier_keycodes,
        )

        for binding_id, registration in list(self._registrations.items()):
            if not registration.required_modifiers:
                continue
            is_active = registration.keycode in pressed_keycodes and _registration_matches_event(
                registration=registration,
                event_modifiers=event_modifiers,
                pressed_keycodes=pressed_keycodes,
                side_keycodes=self._side_modifier_keycodes,
            )
            previously_active = self._active_side_bindings.get(binding_id, False)
            if is_active and not previously_active:
                self._invoke_callback(binding_id)
            self._active_side_bindings[binding_id] = is_active

        for binding_id in list(self._active_side_bindings):
            registration = self._registrations.get(binding_id)
            if registration is None or not registration.required_modifiers:
                self._active_side_bindings.pop(binding_id, None)

    def _invoke_callback(self, binding_id: str) -> None:
        if self._callback is None:
            return
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


def _to_x11_key(X: object, XK: object, display: object, modifiers: tuple[str, ...], key: str) -> Optional[tuple[int, int]]:
    mod_mask = 0
    if any(token.startswith("shift_") for token in modifiers):
        mod_mask |= int(X.ShiftMask)
    if any(token.startswith("ctrl_") for token in modifiers):
        mod_mask |= int(X.ControlMask)
    if any(token.startswith("alt_") for token in modifiers):
        mod_mask |= int(X.Mod1Mask)
    if any(token.startswith("win_") for token in modifiers):
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


def _resolve_side_modifier_keycodes(XK: object, display: object) -> dict[str, set[int]]:
    token_to_keysyms = {
        "ctrl_l": ("Control_L",),
        "ctrl_r": ("Control_R",),
        "alt_l": ("Alt_L", "Meta_L"),
        "alt_r": ("Alt_R", "Meta_R", "ISO_Level3_Shift"),
        "shift_l": ("Shift_L",),
        "shift_r": ("Shift_R",),
        "win_l": ("Super_L", "Meta_L", "Hyper_L"),
        "win_r": ("Super_R", "Meta_R", "Hyper_R"),
    }
    keycodes: dict[str, set[int]] = {}
    for token, keysym_tokens in token_to_keysyms.items():
        resolved: set[int] = set()
        for keysym_token in keysym_tokens:
            keysym = int(XK.string_to_keysym(keysym_token))
            if keysym == 0:
                continue
            keycode = int(display.keysym_to_keycode(keysym))
            if keycode:
                resolved.add(keycode)
        keycodes[token] = resolved
    return keycodes


def _pressed_keycodes(display: object) -> set[int]:
    pressed: set[int] = set()

    # Query keymap twice and union the result; this reduces transient misses
    # around modifier ordering/timing differences on some X11 setups.
    for _ in range(2):
        try:
            keymap = display.query_keymap()
        except Exception:
            continue

        for index, value in enumerate(keymap):
            byte_value = int(value)
            for bit in range(8):
                if byte_value & (1 << bit):
                    pressed.add(index * 8 + bit)
    return pressed


def _side_modifiers_match(
    *,
    required: tuple[str, ...],
    pressed_keycodes: set[int],
    side_keycodes: dict[str, set[int]],
    event_modifiers: int,
) -> bool:
    required_set = set(required)
    groups = {
        "ctrl": {"tokens": {"ctrl_l", "ctrl_r"}, "mask": 0x04},
        "alt": {"tokens": {"alt_l", "alt_r"}, "mask": 0x08},
        "shift": {"tokens": {"shift_l", "shift_r"}, "mask": 0x01},
        "win": {"tokens": {"win_l", "win_r"}, "mask": 0x40},
    }

    for token in required_set:
        codes = side_keycodes.get(token, set())
        if codes and any(code in pressed_keycodes for code in codes):
            continue

        group_name = _modifier_group_for_token(token)
        if group_name is None:
            return False
        group_tokens = groups[group_name]["tokens"]
        opposite_tokens = group_tokens - {token}
        for opposite_token in opposite_tokens:
            opposite_codes = side_keycodes.get(opposite_token, set())
            if opposite_codes and any(code in pressed_keycodes for code in opposite_codes):
                return False
        if not (event_modifiers & int(groups[group_name]["mask"])):
            return False

    for group in groups.values():
        tokens = set(group["tokens"])
        if tokens.intersection(required_set):
            continue
        for token in tokens:
            codes = side_keycodes.get(token, set())
            if any(code in pressed_keycodes for code in codes):
                return False
        if event_modifiers & int(group["mask"]):
            return False
    return True


def _registration_matches_event(
    *,
    registration: _X11Registration,
    event_modifiers: int,
    pressed_keycodes: set[int],
    side_keycodes: dict[str, set[int]],
) -> bool:
    # Non-side-specific bindings (no required side tokens) keep strict mask matching.
    if not registration.required_modifiers:
        return event_modifiers == registration.modifiers_mask

    # For side-specific bindings, rely on explicit left/right key state instead of
    # strict X11 state-mask equality so modifier press order/state timing variance
    # does not suppress otherwise-valid matches.
    return _side_modifiers_match(
        required=registration.required_modifiers,
        pressed_keycodes=pressed_keycodes,
        side_keycodes=side_keycodes,
        event_modifiers=event_modifiers,
    )


def _event_modifiers_from_pressed(
    *,
    pressed_keycodes: set[int],
    side_keycodes: dict[str, set[int]],
) -> int:
    groups = {
        "ctrl": {"tokens": ("ctrl_l", "ctrl_r"), "mask": 0x04},
        "alt": {"tokens": ("alt_l", "alt_r"), "mask": 0x08},
        "shift": {"tokens": ("shift_l", "shift_r"), "mask": 0x01},
        "win": {"tokens": ("win_l", "win_r"), "mask": 0x40},
    }
    event_modifiers = 0
    for group in groups.values():
        group_codes: set[int] = set()
        for token in group["tokens"]:
            group_codes.update(side_keycodes.get(token, set()))
        if group_codes and any(code in pressed_keycodes for code in group_codes):
            event_modifiers |= int(group["mask"])
    return event_modifiers


def _registration_grab_modifiers(*, modifiers_mask: int, required_modifiers: tuple[str, ...]) -> tuple[int, ...]:
    if not required_modifiers:
        return (modifiers_mask,)

    required_groups = {
        group_mask
        for token in required_modifiers
        if (group_mask := _modifier_mask_for_token(token)) is not None
    }
    if not required_groups:
        return (modifiers_mask,)

    fallback_masks = {modifiers_mask}
    for group_mask in required_groups:
        fallback = modifiers_mask & ~group_mask
        if fallback != 0:
            fallback_masks.add(fallback)
    ordered = [modifiers_mask]
    ordered.extend(mask for mask in sorted(fallback_masks) if mask != modifiers_mask)
    return tuple(ordered)


def _modifier_group_for_token(token: str) -> str | None:
    if token.startswith("ctrl_"):
        return "ctrl"
    if token.startswith("alt_"):
        return "alt"
    if token.startswith("shift_"):
        return "shift"
    if token.startswith("win_"):
        return "win"
    return None


def _modifier_mask_for_token(token: str) -> int | None:
    group = _modifier_group_for_token(token)
    if group == "ctrl":
        return 0x04
    if group == "alt":
        return 0x08
    if group == "shift":
        return 0x01
    if group == "win":
        return 0x40
    return None
