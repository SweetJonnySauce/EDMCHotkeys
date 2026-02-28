"""GNOME Wayland bridge backend using local Unix-socket IPC."""

from __future__ import annotations

from collections import deque
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
from typing import Callable, Mapping, Optional

from .base import BackendAvailability, BackendCapabilities, HotkeyCallback
from .gnome_sender_sync import GnomeBridgeSenderSync, default_sender_script_path

_ENABLE_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE"
_SOCKET_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_SOCKET"
_AUTOSYNC_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_AUTOSYNC"
_SENDER_SCRIPT_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_SENDER_SCRIPT"
_NO_EVENTS_WARN_SECONDS_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_NO_EVENTS_WARN_SECONDS"
_BACKEND_MODE_ENV = "EDMC_HOTKEYS_BACKEND_MODE"
_TOKEN_FILE_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN_FILE"
_TOKEN_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN"
_HARDENED_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_HARDENED"
_ALLOW_LEGACY_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_ALLOW_LEGACY"
_REPLAY_WINDOW_MS_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_REPLAY_WINDOW_MS"
_NONCE_CACHE_SIZE_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_NONCE_CACHE_SIZE"
_RATE_LIMIT_WINDOW_SECONDS_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_RATE_LIMIT_WINDOW_SECONDS"
_RATE_LIMIT_PER_SENDER_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_RATE_LIMIT_PER_SENDER"
_RATE_LIMIT_GLOBAL_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_RATE_LIMIT_GLOBAL"
_QUEUE_MAX_ENV = "EDMC_HOTKEYS_GNOME_BRIDGE_QUEUE_MAX"

_DEFAULT_RUNTIME_SUBDIR = "edmc_hotkeys"
_DEFAULT_SOCKET_FILENAME = "bridge.sock"
_FALLBACK_SOCKET_PATH = "/tmp/edmc_hotkeys_gnome_bridge.sock"
_DEFAULT_NO_EVENTS_WARN_SECONDS = 15.0
_DEFAULT_REPLAY_WINDOW_MS = 5_000
_DEFAULT_NONCE_CACHE_SIZE = 1_024
_DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 5.0
_DEFAULT_RATE_LIMIT_PER_SENDER = 30
_DEFAULT_RATE_LIMIT_GLOBAL = 120
_DEFAULT_QUEUE_MAX = 256
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_flag_enabled(environ: Mapping[str, str], key: str, *, default: bool = False) -> bool:
    value = environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


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


def _parse_int(raw: str, *, default: int, minimum: int) -> int:
    value = raw.strip()
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    if parsed < minimum:
        return default
    return parsed


def _parse_float(raw: str, *, default: float, minimum: float) -> float:
    value = raw.strip()
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    if parsed < minimum:
        return default
    return parsed


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
        self._logger = logger or logging.getLogger("EDMCHotkeys")
        self._platform_name = platform_name or sys.platform
        self._environ = dict(os.environ) if environ is None else dict(environ)
        self._socket_factory = socket_factory
        self._runtime_uid = os.getuid() if hasattr(os, "getuid") else -1
        self._socket_path_is_explicit = socket_path is not None or bool(self._environ.get(_SOCKET_ENV))
        self._socket_path = socket_path or self._environ.get(_SOCKET_ENV) or self._default_socket_path()
        self._socket_runtime_dir = str(Path(self._socket_path).parent)
        self._token_file_path = self._environ.get(_TOKEN_FILE_ENV) or str(
            Path(self._socket_runtime_dir) / "sender.token"
        )
        self._hardened_mode = _env_flag_enabled(self._environ, _HARDENED_ENV, default=True)
        self._allow_legacy_payloads = _env_flag_enabled(self._environ, _ALLOW_LEGACY_ENV, default=False)
        self._sender_autosync_enabled = _env_flag_enabled(self._environ, _AUTOSYNC_ENV, default=True)
        self._no_events_warn_seconds = _parse_warn_seconds(self._environ.get(_NO_EVENTS_WARN_SECONDS_ENV, ""))
        self._replay_window_ms = _parse_int(
            self._environ.get(_REPLAY_WINDOW_MS_ENV, ""),
            default=_DEFAULT_REPLAY_WINDOW_MS,
            minimum=1_000,
        )
        self._nonce_cache_size = _parse_int(
            self._environ.get(_NONCE_CACHE_SIZE_ENV, ""),
            default=_DEFAULT_NONCE_CACHE_SIZE,
            minimum=64,
        )
        self._rate_limit_window_seconds = _parse_float(
            self._environ.get(_RATE_LIMIT_WINDOW_SECONDS_ENV, ""),
            default=_DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
            minimum=1.0,
        )
        self._rate_limit_per_sender = _parse_int(
            self._environ.get(_RATE_LIMIT_PER_SENDER_ENV, ""),
            default=_DEFAULT_RATE_LIMIT_PER_SENDER,
            minimum=1,
        )
        self._rate_limit_global = _parse_int(
            self._environ.get(_RATE_LIMIT_GLOBAL_ENV, ""),
            default=_DEFAULT_RATE_LIMIT_GLOBAL,
            minimum=1,
        )
        self._queue_max = _parse_int(
            self._environ.get(_QUEUE_MAX_ENV, ""),
            default=_DEFAULT_QUEUE_MAX,
            minimum=16,
        )

        sender_script_path = self._environ.get(_SENDER_SCRIPT_ENV, default_sender_script_path())
        self._sender_sync = sender_sync
        self._sender_script_path = sender_script_path
        self._sender_status = "disabled" if not self._sender_autosync_enabled else "unknown"
        self._sender_last_error: Optional[str] = None
        self._sender_synced_bindings = 0

        self._callback: Optional[HotkeyCallback] = None
        self._registered: dict[str, str] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None
        self._batch_depth = 0
        self._sync_pending = False
        self._events_seen = 0
        self._started_at_mono = 0.0
        self._receiver_only_warned = False
        self._payload_queue: deque[bytes] = deque()
        self._sender_windows: dict[str, deque[float]] = {}
        self._global_window: deque[float] = deque()
        self._nonce_seen: dict[str, int] = {}
        self._nonce_order: deque[tuple[str, int]] = deque()
        self._auth_token = ""
        self._last_legacy_warning = 0.0
        self._security_counters: dict[str, int] = {
            "auth_reject": 0,
            "replay_reject": 0,
            "malformed_reject": 0,
            "rate_limit_drop": 0,
            "queue_drop": 0,
        }

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
        if not self._socket_path_is_explicit and not self._environ.get("XDG_RUNTIME_DIR", "").strip():
            return BackendAvailability(
                name=self.name,
                available=False,
                reason="XDG_RUNTIME_DIR is required for secure bridge runtime path",
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
            secure_ok, secure_reason = self._prepare_security_prerequisites()
            if not secure_ok:
                self._logger.warning("GNOME bridge startup failed: %s", secure_reason)
                self._callback = None
                return False

            self._ensure_sender_sync()
            self._reset_runtime_state()

            sock = self._socket_factory() if self._socket_factory is not None else socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.settimeout(0.2)
            try:
                os.unlink(self._socket_path)
            except FileNotFoundError:
                pass
            sock.bind(self._socket_path)
            try:
                os.chmod(self._socket_path, 0o600)
            except OSError:
                self._logger.debug("Failed to set socket permissions on %s", self._socket_path, exc_info=True)
            self._socket = sock
            self._running = True
            self._started_at_mono = time.monotonic()
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
            "hardened_mode": self._hardened_mode,
            "allow_legacy_payloads": self._allow_legacy_payloads,
            "token_file_path": self._token_file_path,
            "auth_reject": self._security_counters["auth_reject"],
            "replay_reject": self._security_counters["replay_reject"],
            "malformed_reject": self._security_counters["malformed_reject"],
            "rate_limit_drop": self._security_counters["rate_limit_drop"],
            "queue_drop": self._security_counters["queue_drop"],
        }

    def _listen_loop(self) -> None:
        while self._running:
            sock = self._socket
            if sock is None:
                break
            try:
                payload, _addr = sock.recvfrom(4096)
                self._enqueue_payload(payload)
            except socket.timeout:
                self._drain_queue()
                self._maybe_warn_receiver_only()
                continue
            except OSError:
                if self._running:
                    self._logger.debug("GNOME bridge listener socket closed unexpectedly", exc_info=True)
                break

            self._drain_queue()

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

    def _enqueue_payload(self, payload: bytes) -> None:
        if len(self._payload_queue) >= self._queue_max:
            self._security_counters["queue_drop"] += 1
            self._logger.warning(
                "GNOME bridge dropped payload due to queue saturation: queue_max=%d drops=%d",
                self._queue_max,
                self._security_counters["queue_drop"],
            )
            return
        self._payload_queue.append(payload)

    def _drain_queue(self) -> None:
        while self._payload_queue:
            payload = self._payload_queue.popleft()
            self._process_payload(payload)

    def _process_payload(self, payload: bytes) -> None:
        parsed = self._parse_activation_payload(payload)
        if parsed is None:
            return
        binding_id, sender_id, timestamp_ms, nonce, is_legacy = parsed
        if self._is_rate_limited(sender_id):
            self._security_counters["rate_limit_drop"] += 1
            self._logger.warning(
                "GNOME bridge rejected activation due to rate limit: sender_id=%s drops=%d",
                sender_id,
                self._security_counters["rate_limit_drop"],
            )
            return
        if not is_legacy and self._is_replay_or_stale(timestamp_ms, nonce):
            self._security_counters["replay_reject"] += 1
            self._logger.warning(
                "GNOME bridge rejected activation due to replay/time window: sender_id=%s rejects=%d",
                sender_id,
                self._security_counters["replay_reject"],
            )
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

    def _parse_activation_payload(
        self, payload: bytes
    ) -> Optional[tuple[str, str, int, str, bool]]:
        text = payload.decode("utf-8", errors="ignore").strip()
        if not text:
            self._security_counters["malformed_reject"] += 1
            self._logger.warning("GNOME bridge rejected payload: empty payload")
            return None

        if text.startswith("{"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                self._security_counters["malformed_reject"] += 1
                self._logger.warning("GNOME bridge rejected payload: invalid JSON")
                return None
            if not isinstance(parsed, dict):
                self._security_counters["malformed_reject"] += 1
                self._logger.warning("GNOME bridge rejected payload: JSON root must be object")
                return None
            return self._parse_json_payload(parsed)

        if not self._allow_legacy_payloads:
            self._security_counters["malformed_reject"] += 1
            self._logger.warning("GNOME bridge rejected payload: legacy text payloads are disabled")
            return None
        return self._legacy_activation(text)

    def _parse_json_payload(
        self,
        parsed: dict[str, object],
    ) -> Optional[tuple[str, str, int, str, bool]]:
        if "version" in parsed or "type" in parsed or self._hardened_mode or not self._allow_legacy_payloads:
            return self._parse_v1_payload(parsed)

        binding_id = parsed.get("binding_id")
        if isinstance(binding_id, str):
            return self._legacy_activation(binding_id.strip())

        self._security_counters["malformed_reject"] += 1
        self._logger.warning("GNOME bridge rejected payload: missing binding_id")
        return None

    def _parse_v1_payload(
        self,
        parsed: dict[str, object],
    ) -> Optional[tuple[str, str, int, str, bool]]:
        version = parsed.get("version")
        if not isinstance(version, str) or version != "1":
            self._security_counters["malformed_reject"] += 1
            self._logger.warning("GNOME bridge rejected payload: unsupported version '%s'", version)
            return None
        msg_type = parsed.get("type")
        if not isinstance(msg_type, str) or msg_type != "activate":
            self._security_counters["malformed_reject"] += 1
            self._logger.warning("GNOME bridge rejected payload: unsupported type '%s'", msg_type)
            return None
        binding_id = parsed.get("binding_id")
        if not isinstance(binding_id, str) or not binding_id.strip():
            self._security_counters["malformed_reject"] += 1
            self._logger.warning("GNOME bridge rejected payload: invalid binding_id")
            return None
        timestamp_value = parsed.get("timestamp_ms")
        if not isinstance(timestamp_value, int):
            self._security_counters["malformed_reject"] += 1
            self._logger.warning("GNOME bridge rejected payload: invalid timestamp_ms")
            return None
        nonce = parsed.get("nonce")
        if not isinstance(nonce, str) or not nonce.strip():
            self._security_counters["malformed_reject"] += 1
            self._logger.warning("GNOME bridge rejected payload: invalid nonce")
            return None
        token_value = parsed.get("token")
        token = token_value if isinstance(token_value, str) else ""
        if self._hardened_mode and not self._token_matches(token):
            self._security_counters["auth_reject"] += 1
            self._logger.warning(
                "GNOME bridge rejected payload: authentication failed (rejects=%d)",
                self._security_counters["auth_reject"],
            )
            return None
        sender_value = parsed.get("sender_id")
        sender_id = sender_value if isinstance(sender_value, str) and sender_value.strip() else "unknown"
        return binding_id.strip(), sender_id.strip(), timestamp_value, nonce.strip(), False

    def _legacy_activation(self, binding_id: str) -> Optional[tuple[str, str, int, str, bool]]:
        clean_binding = binding_id.strip()
        if not clean_binding:
            self._security_counters["malformed_reject"] += 1
            self._logger.warning("GNOME bridge rejected payload: empty binding_id")
            return None
        now = time.monotonic()
        if now - self._last_legacy_warning > 30.0:
            self._last_legacy_warning = now
            self._logger.warning("GNOME bridge accepted legacy payload format; enable v1 sender payloads")
        timestamp_ms = int(time.time() * 1000)
        nonce = f"legacy-{secrets.token_hex(8)}"
        return clean_binding, "legacy", timestamp_ms, nonce, True

    def _token_matches(self, token: str) -> bool:
        if not self._auth_token:
            return False
        return secrets.compare_digest(token, self._auth_token)

    def _is_replay_or_stale(self, timestamp_ms: int, nonce: str) -> bool:
        now_ms = int(time.time() * 1000)
        if abs(now_ms - timestamp_ms) > self._replay_window_ms:
            return True
        self._prune_nonce_cache(now_ms)
        seen_at = self._nonce_seen.get(nonce)
        if seen_at is not None and now_ms - seen_at <= self._replay_window_ms:
            return True
        self._nonce_seen[nonce] = now_ms
        self._nonce_order.append((nonce, now_ms))
        self._prune_nonce_cache(now_ms)
        return False

    def _prune_nonce_cache(self, now_ms: int) -> None:
        while self._nonce_order:
            nonce, created_at = self._nonce_order[0]
            too_old = now_ms - created_at > self._replay_window_ms
            too_many = len(self._nonce_seen) > self._nonce_cache_size
            if not too_old and not too_many:
                break
            self._nonce_order.popleft()
            current = self._nonce_seen.get(nonce)
            if current == created_at:
                self._nonce_seen.pop(nonce, None)

    def _is_rate_limited(self, sender_id: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._rate_limit_window_seconds
        sender_window = self._sender_windows.setdefault(sender_id, deque())
        while sender_window and sender_window[0] < cutoff:
            sender_window.popleft()
        while self._global_window and self._global_window[0] < cutoff:
            self._global_window.popleft()
        if len(sender_window) >= self._rate_limit_per_sender:
            return True
        if len(self._global_window) >= self._rate_limit_global:
            return True
        sender_window.append(now)
        self._global_window.append(now)
        return False

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
            "GNOME bridge startup summary: mode=%s socket=%s hardened=%s legacy=%s sender_autosync=%s sender_status=%s synced_bindings=%d",
            self._environ.get(_BACKEND_MODE_ENV, "auto"),
            self._socket_path,
            self._hardened_mode,
            self._allow_legacy_payloads,
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

    def _prepare_security_prerequisites(self) -> tuple[bool, str]:
        runtime_dir_path = Path(self._socket_runtime_dir)
        ok, reason = self._ensure_secure_directory(runtime_dir_path)
        if not ok:
            return False, reason
        token = self._environ.get(_TOKEN_ENV, "").strip()
        if token:
            self._auth_token = token
            self._write_token_file(Path(self._token_file_path), token)
            return True, ""
        token_ok, token_or_reason = self._load_or_create_token_file(Path(self._token_file_path))
        if not token_ok:
            return False, token_or_reason
        self._auth_token = token_or_reason
        return True, ""

    def _ensure_secure_directory(self, directory: Path) -> tuple[bool, str]:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return False, f"unable to create runtime directory '{directory}': {exc}"
        try:
            st = directory.stat()
        except Exception as exc:
            return False, f"unable to stat runtime directory '{directory}': {exc}"
        if not stat.S_ISDIR(st.st_mode):
            return False, f"runtime path '{directory}' is not a directory"
        if self._runtime_uid >= 0 and st.st_uid != self._runtime_uid:
            return False, f"runtime directory '{directory}' is not owned by current user"
        if st.st_mode & 0o077:
            try:
                os.chmod(directory, 0o700)
                st = directory.stat()
            except Exception as exc:
                return False, f"unable to secure runtime directory '{directory}': {exc}"
            if st.st_mode & 0o077:
                return False, f"runtime directory '{directory}' permissions are too open"
        return True, ""

    def _load_or_create_token_file(self, token_file: Path) -> tuple[bool, str]:
        if token_file.exists():
            try:
                token = token_file.read_text(encoding="utf-8").strip()
            except Exception as exc:
                return False, f"unable to read token file '{token_file}': {exc}"
            if len(token) < 16:
                return False, f"token file '{token_file}' is invalid"
            ok, reason = self._validate_secure_file(token_file)
            if not ok:
                return False, reason
            return True, token

        token = secrets.token_urlsafe(32)
        try:
            self._write_token_file(token_file, token)
        except Exception as exc:
            return False, f"unable to write token file '{token_file}': {exc}"
        return True, token

    def _write_token_file(self, token_file: Path, token: str) -> None:
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(token + "\n", encoding="utf-8")
        os.chmod(token_file, 0o600)

    def _validate_secure_file(self, path: Path) -> tuple[bool, str]:
        try:
            st = path.stat()
        except Exception as exc:
            return False, f"unable to stat file '{path}': {exc}"
        if self._runtime_uid >= 0 and st.st_uid != self._runtime_uid:
            return False, f"file '{path}' is not owned by current user"
        if st.st_mode & 0o077:
            return False, f"file '{path}' permissions are too open"
        return True, ""

    def _ensure_sender_sync(self) -> None:
        if not self._sender_autosync_enabled:
            return
        if self._sender_sync is None:
            self._sender_sync = GnomeBridgeSenderSync(
                socket_path=self._socket_path,
                sender_script_path=self._sender_script_path,
                token_file_path=self._token_file_path,
                logger=self._logger,
            )
            return
        setter = getattr(self._sender_sync, "set_token_file_path", None)
        if callable(setter):
            setter(self._token_file_path)

    def _reset_runtime_state(self) -> None:
        self._events_seen = 0
        self._receiver_only_warned = False
        self._payload_queue.clear()
        self._sender_windows.clear()
        self._global_window.clear()
        self._nonce_seen.clear()
        self._nonce_order.clear()
        for key in self._security_counters:
            self._security_counters[key] = 0

    def _default_socket_path(self) -> str:
        runtime_dir = self._environ.get("XDG_RUNTIME_DIR", "").strip()
        if not runtime_dir:
            return _FALLBACK_SOCKET_PATH
        return str(Path(runtime_dir) / _DEFAULT_RUNTIME_SUBDIR / _DEFAULT_SOCKET_FILENAME)
