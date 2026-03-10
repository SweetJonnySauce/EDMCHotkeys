"""Wayland keyd backend using local Unix datagram activation receiver."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import secrets
import socket
import stat
import sys
import threading
import time
from typing import Mapping, Optional

from .base import BackendAvailability, BackendCapabilities, HotkeyCallback

_SOCKET_ENV = "EDMC_HOTKEYS_KEYD_SOCKET_PATH"
_TOKEN_FILE_ENV = "EDMC_HOTKEYS_KEYD_TOKEN_FILE"
_TOKEN_ENV = "EDMC_HOTKEYS_KEYD_TOKEN"

_DEFAULT_SOCKET_REL_PATH = "keyd/runtime/keyd.sock"
_DEFAULT_TOKEN_FILE_REL_PATH = "keyd/runtime/sender.token"
_DEFAULT_QUEUE_MAX = 256
_DEFAULT_REPLAY_WINDOW_MS = 5_000


def _resolve_path(plugin_dir: Path, raw_path: str) -> Path:
    candidate = Path(raw_path.strip())
    if not candidate.is_absolute():
        return plugin_dir / candidate
    return candidate


class WaylandKeydBackend:
    """Backend that receives authenticated binding activations from keyd commands."""

    def __init__(
        self,
        *,
        plugin_dir: Path,
        logger: Optional[logging.Logger] = None,
        platform_name: Optional[str] = None,
        environ: Optional[Mapping[str, str]] = None,
        socket_path: Optional[str] = None,
        token_file_path: Optional[str] = None,
        queue_max: int = _DEFAULT_QUEUE_MAX,
    ) -> None:
        self._plugin_dir = plugin_dir
        self._logger = logger or logging.getLogger("EDMCHotkeys")
        self._platform_name = platform_name or sys.platform
        self._environ = dict(os.environ) if environ is None else dict(environ)
        configured_socket = socket_path or self._environ.get(_SOCKET_ENV, _DEFAULT_SOCKET_REL_PATH)
        configured_token_file = token_file_path or self._environ.get(_TOKEN_FILE_ENV, _DEFAULT_TOKEN_FILE_REL_PATH)
        self._socket_path = _resolve_path(plugin_dir, configured_socket)
        self._token_file_path = _resolve_path(plugin_dir, configured_token_file)
        self._queue_max = max(16, int(queue_max))

        self._auth_token = self._environ.get(_TOKEN_ENV, "").strip()
        self._callback: Optional[HotkeyCallback] = None
        self._registered: dict[str, str] = {}
        self._running = False
        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._events_seen = 0
        self._queue_drop_count = 0
        self._replay_reject_count = 0
        self._auth_reject_count = 0
        self._last_error = ""
        self._nonce_seen: dict[str, int] = {}
        self._nonce_lock = threading.Lock()

    @property
    def name(self) -> str:
        return "linux-wayland-keyd"

    def availability(self) -> BackendAvailability:
        if not self._platform_name.startswith("linux"):
            return BackendAvailability(
                name=self.name,
                available=False,
                reason=f"Unsupported platform '{self._platform_name}'",
            )
        if not self._environ.get("WAYLAND_DISPLAY"):
            return BackendAvailability(
                name=self.name,
                available=False,
                reason="WAYLAND_DISPLAY is not set",
            )
        return BackendAvailability(name=self.name, available=True)

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_side_specific_modifiers=True)

    def start(self, on_hotkey: HotkeyCallback) -> bool:
        availability = self.availability()
        if not availability.available:
            self._last_error = availability.reason or "unavailable"
            return False
        if self._running:
            self._callback = on_hotkey
            return True
        self._callback = on_hotkey
        self._prepare_runtime_paths()
        self._load_or_create_token()
        self._remove_existing_socket()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            sock.bind(str(self._socket_path))
            os.chmod(self._socket_path, stat.S_IRUSR | stat.S_IWUSR)
            sock.settimeout(0.2)
        except Exception:
            self._last_error = f"Failed to bind keyd socket at {self._socket_path}"
            self._logger.exception(self._last_error)
            try:
                sock.close()
            except OSError:
                pass
            return False

        self._socket = sock
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            name="edmc-hotkeys-wayland-keyd",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        sock = self._socket
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        self._socket = None
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=0.5)
        self._thread = None
        self._remove_existing_socket()

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        self._registered[binding_id] = hotkey
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        self._registered.pop(binding_id, None)
        return True

    def runtime_status(self) -> Mapping[str, object]:
        return {
            "socket_path": str(self._socket_path),
            "token_file_path": str(self._token_file_path),
            "registered_bindings": len(self._registered),
            "running": self._running,
            "events_seen": self._events_seen,
            "auth_reject": self._auth_reject_count,
            "replay_reject": self._replay_reject_count,
            "queue_drop": self._queue_drop_count,
            "last_error": self._last_error,
        }

    def _run_loop(self) -> None:
        while self._running:
            sock = self._socket
            if sock is None:
                break
            try:
                payload, _sender = sock.recvfrom(16384)
            except socket.timeout:
                continue
            except OSError:
                break
            if len(payload) > self._queue_max * 1024:
                self._queue_drop_count += 1
                continue
            self._handle_payload(payload)

    def _handle_payload(self, payload: bytes) -> None:
        try:
            message = json.loads(payload.decode("utf-8"))
        except Exception:
            self._logger.warning("keyd backend rejected malformed payload")
            return
        if not isinstance(message, dict):
            self._logger.warning("keyd backend rejected malformed payload object")
            return

        if str(message.get("version", "")).strip() != "1" or str(message.get("type", "")).strip() != "activate":
            self._logger.warning("keyd backend rejected payload with unsupported version/type")
            return

        binding_id = str(message.get("binding_id", "")).strip()
        nonce = str(message.get("nonce", "")).strip()
        token = str(message.get("token", "")).strip()
        timestamp_ms = int(message.get("timestamp_ms", 0) or 0)
        now_ms = int(time.time() * 1000)
        if abs(now_ms - timestamp_ms) > _DEFAULT_REPLAY_WINDOW_MS:
            self._replay_reject_count += 1
            self._logger.warning("keyd backend rejected stale payload: binding_id=%s", binding_id or "<missing>")
            return
        if not nonce or self._seen_nonce(nonce):
            self._replay_reject_count += 1
            self._logger.warning("keyd backend rejected replay payload: binding_id=%s", binding_id or "<missing>")
            return
        if not self._auth_token or not token or not secrets.compare_digest(self._auth_token, token):
            self._auth_reject_count += 1
            self._logger.warning("keyd backend rejected payload with invalid token")
            return
        if not binding_id:
            self._logger.warning("keyd backend rejected payload with missing binding_id")
            return
        if binding_id not in self._registered:
            self._logger.warning("keyd backend received unknown binding id '%s'", binding_id)
            return
        callback = self._callback
        if callback is None:
            return
        self._events_seen += 1
        callback(binding_id)

    def _seen_nonce(self, nonce: str) -> bool:
        now_ms = int(time.time() * 1000)
        with self._nonce_lock:
            if nonce in self._nonce_seen:
                return True
            self._nonce_seen[nonce] = now_ms
            stale_before = now_ms - _DEFAULT_REPLAY_WINDOW_MS
            stale = [key for key, ts in self._nonce_seen.items() if ts < stale_before]
            for key in stale:
                self._nonce_seen.pop(key, None)
        return False

    def _prepare_runtime_paths(self) -> None:
        self._socket_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_file_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_or_create_token(self) -> None:
        if self._auth_token:
            return
        if self._token_file_path.exists():
            self._auth_token = self._token_file_path.read_text(encoding="utf-8").strip()
        if len(self._auth_token) >= 16:
            return
        self._auth_token = secrets.token_hex(32)
        self._token_file_path.write_text(self._auth_token + "\n", encoding="utf-8")
        os.chmod(self._token_file_path, stat.S_IRUSR | stat.S_IWUSR)

    def _remove_existing_socket(self) -> None:
        if not self._socket_path.exists():
            return
        try:
            if self._socket_path.is_socket():
                self._socket_path.unlink()
        except Exception:
            self._logger.debug("Failed to remove existing keyd socket", exc_info=True)
