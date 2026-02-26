"""GNOME Wayland bridge backend using local Unix-socket IPC."""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
import time
from typing import Callable, Mapping, Optional

from .base import BackendAvailability, BackendCapabilities, HotkeyCallback
from .gnome_sender_sync import GnomeBridgeSenderSync, default_sender_script_path

_ENABLE_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE"
_SOCKET_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_SOCKET"
_AUTOSYNC_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_AUTOSYNC"
_SENDER_SCRIPT_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_SENDER_SCRIPT"
_NO_EVENTS_WARN_SECONDS_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_NO_EVENTS_WARN_SECONDS"
_DEFAULT_SOCKET_PATH = "/tmp/edmc_hotkeys_gnome_bridge.sock"
_DEFAULT_NO_EVENTS_WARN_SECONDS = 15.0
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_flag_enabled(environ: Mapping[str, str], key: str, *, default: bool = False) -> bool:
    value = environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


class GnomeWaylandBridgeBackend:
    """Optional companion bridge backend for GNOME Wayland."""

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        platform_name: Optional[str] = None,
        environ: Optional[Mapping[str, str]] = None,
        socket_path: Optional[str] = None,
        socket_factory: Optional[Callable[[], socket.socket]] = None,
        sender_sync: Optional[GnomeBridgeSenderSync] = None,
    ) -> None:
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")
        self._platform_name = platform_name or sys.platform
        self._environ = dict(os.environ) if environ is None else dict(environ)
        self._socket_path = socket_path or self._environ.get(_SOCKET_ENV, _DEFAULT_SOCKET_PATH)
        self._socket_factory = socket_factory
        self._sender_autosync_enabled = _env_flag_enabled(self._environ, _AUTOSYNC_ENV, default=True)
        sender_script_path = self._environ.get(_SENDER_SCRIPT_ENV, default_sender_script_path())
        self._sender_sync = sender_sync
        if self._sender_sync is None and self._sender_autosync_enabled:
            self._sender_sync = GnomeBridgeSenderSync(
                socket_path=self._socket_path,
                sender_script_path=sender_script_path,
                logger=self._logger,
            )
        self._sender_status = "disabled" if not self._sender_autosync_enabled else "unknown"
        self._sender_last_error: Optional[str] = None
        self._sender_synced_bindings = 0
        self._events_seen = 0
        self._started_at_mono = 0.0
        self._receiver_only_warned = False
        self._batch_depth = 0
        self._sync_pending = False
        self._no_events_warn_seconds = _parse_warn_seconds(self._environ.get(_NO_EVENTS_WARN_SECONDS_ENV, ""))
        self._callback: Optional[HotkeyCallback] = None
        self._registered: dict[str, str] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None

    @property
    def name(self) -> str:
        return "linux-wayland-gnome-bridge"

    def availability(self) -> BackendAvailability:
        if not self._platform_name.startswith("linux"):
            return BackendAvailability(
                name=self.name,
                available=False,
                reason=f"Unsupported platform '{self._platform_name}'",
            )
        if not self._environ.get("WAYLAND_DISPLAY"):
            return BackendAvailability(name=self.name, available=False, reason="WAYLAND_DISPLAY is not set")
        if not _env_flag_enabled(self._environ, _ENABLE_ENV, default=False):
            return BackendAvailability(
                name=self.name,
                available=False,
                reason=f"Set {_ENABLE_ENV}=1 to enable GNOME bridge backend",
            )
        return BackendAvailability(name=self.name, available=True)

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
        if self._running:
            self._callback = on_hotkey
            return True

        self._callback = on_hotkey
        try:
            sock = self._socket_factory() if self._socket_factory is not None else socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.settimeout(0.2)
            try:
                os.unlink(self._socket_path)
            except FileNotFoundError:
                pass
            sock.bind(self._socket_path)
            self._socket = sock
            self._running = True
            self._started_at_mono = time.monotonic()
            self._events_seen = 0
            self._receiver_only_warned = False
            self._thread = threading.Thread(
                target=self._listen_loop,
                daemon=True,
                name="edmc-hotkeys-gnome-bridge",
            )
            self._thread.start()
            self._sync_sender_bindings(reason="startup")
            self._logger.info("Hotkey backend '%s' started on %s", self.name, self._socket_path)
            self._log_startup_summary()
            return True
        except Exception as exc:
            self._logger.warning("GNOME bridge startup failed: %s", exc)
            self._running = False
            self._callback = None
            self._close_socket()
            return False

    def stop(self) -> None:
        self._running = False
        self._close_socket()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None
        self._callback = None
        self._registered.clear()
        self._sync_pending = False
        self._batch_depth = 0
        if self._sender_sync is not None and self._sender_autosync_enabled:
            result = self._sender_sync.clear_managed_bindings()
            self._sender_status = "ready" if result.ok else "error"
            self._sender_last_error = result.error
            self._sender_synced_bindings = result.synced_bindings
        self._logger.info("Hotkey backend '%s' stopped", self.name)

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        self._registered[binding_id] = hotkey
        self._queue_or_apply_sender_sync(reason="register")
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        self._registered.pop(binding_id, None)
        self._queue_or_apply_sender_sync(reason="unregister")
        return True

    def begin_binding_batch(self) -> None:
        self._batch_depth += 1

    def end_binding_batch(self) -> None:
        if self._batch_depth == 0:
            return
        self._batch_depth -= 1
        if self._batch_depth == 0 and self._sync_pending:
            self._sync_pending = False
            self._sync_sender_bindings(reason="batch-complete")

    def runtime_status(self) -> dict[str, object]:
        return {
            "socket_path": self._socket_path,
            "sender_autosync_enabled": self._sender_autosync_enabled,
            "sender_status": self._sender_status,
            "sender_last_error": self._sender_last_error,
            "sender_synced_bindings": self._sender_synced_bindings,
            "events_seen": self._events_seen,
            "registered_bindings": len(self._registered),
        }

    def _listen_loop(self) -> None:
        while self._running:
            sock = self._socket
            if sock is None:
                break
            try:
                payload, _addr = sock.recvfrom(4096)
            except socket.timeout:
                self._maybe_warn_receiver_only()
                continue
            except OSError:
                if self._running:
                    self._logger.debug("GNOME bridge listener socket closed unexpectedly", exc_info=True)
                break

            self._process_payload(payload)

    def _close_socket(self) -> None:
        sock = self._socket
        self._socket = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                self._logger.debug("GNOME bridge socket close failed", exc_info=True)
        try:
            os.unlink(self._socket_path)
        except FileNotFoundError:
            pass
        except OSError:
            self._logger.debug("GNOME bridge socket cleanup failed for %s", self._socket_path, exc_info=True)

    @staticmethod
    def _extract_binding_id(payload: bytes) -> str:
        text = payload.decode("utf-8", errors="ignore").strip()
        if not text:
            return ""
        if text.startswith("{"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return ""
            binding_id = parsed.get("binding_id")
            if isinstance(binding_id, str):
                return binding_id.strip()
            return ""
        return text

    def _process_payload(self, payload: bytes) -> None:
        binding_id = self._extract_binding_id(payload)
        if not binding_id:
            self._logger.debug("Ignoring GNOME bridge payload with no binding id")
            return
        if binding_id not in self._registered:
            self._logger.debug("Ignoring GNOME bridge activation for unknown binding '%s'", binding_id)
            return
        callback = self._callback
        if callback is None:
            return
        try:
            self._events_seen += 1
            callback(binding_id)
        except Exception:
            self._logger.exception("GNOME bridge callback failed for '%s'", binding_id)

    def _queue_or_apply_sender_sync(self, *, reason: str) -> None:
        if self._batch_depth > 0:
            self._sync_pending = True
            return
        self._sync_sender_bindings(reason=reason)

    def _sync_sender_bindings(self, *, reason: str) -> None:
        if not self._sender_autosync_enabled:
            self._sender_status = "disabled"
            self._sender_last_error = None
            self._sender_synced_bindings = 0
            return
        if self._sender_sync is None:
            self._sender_status = "error"
            self._sender_last_error = "sender sync is not configured"
            self._sender_synced_bindings = 0
            self._logger.warning("GNOME bridge sender sync unavailable: %s", self._sender_last_error)
            return
        result = self._sender_sync.sync_bindings(self._registered)
        self._sender_status = "ready" if result.ok else "error"
        self._sender_last_error = result.error
        self._sender_synced_bindings = result.synced_bindings
        if result.ok:
            self._logger.debug(
                "GNOME bridge sender sync applied: reason=%s bindings=%d",
                reason,
                result.synced_bindings,
            )
            return
        self._logger.warning(
            "GNOME bridge sender sync failed: reason=%s error=%s",
            reason,
            result.error,
        )

    def _log_startup_summary(self) -> None:
        self._logger.info(
            "GNOME bridge startup summary: socket=%s sender_autosync=%s sender_status=%s synced_bindings=%d",
            self._socket_path,
            self._sender_autosync_enabled,
            self._sender_status,
            self._sender_synced_bindings,
        )

    def _maybe_warn_receiver_only(self) -> None:
        if self._receiver_only_warned:
            return
        if not self._sender_autosync_enabled:
            return
        if not self._registered:
            return
        if self._events_seen > 0:
            return
        if self._started_at_mono <= 0:
            return
        elapsed = time.monotonic() - self._started_at_mono
        if elapsed < self._no_events_warn_seconds:
            return
        self._receiver_only_warned = True
        self._logger.warning(
            "GNOME bridge receiver active but no companion events observed yet: socket=%s registered_bindings=%d sender_status=%s",
            self._socket_path,
            len(self._registered),
            self._sender_status,
        )


def _parse_warn_seconds(raw: str) -> float:
    value = raw.strip()
    if not value:
        return _DEFAULT_NO_EVENTS_WARN_SECONDS
    try:
        parsed = float(value)
    except ValueError:
        return _DEFAULT_NO_EVENTS_WARN_SECONDS
    if parsed <= 0:
        return _DEFAULT_NO_EVENTS_WARN_SECONDS
    return parsed
