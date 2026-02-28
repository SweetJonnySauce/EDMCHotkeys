#!/usr/bin/env python3
"""Companion helper for sending hardened protocol-v1 activate payloads."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import secrets
import socket
import sys
import time
from typing import Callable, Optional


DEFAULT_RETRIES = 2
DEFAULT_INITIAL_BACKOFF_MS = 25
DEFAULT_MAX_BACKOFF_MS = 250
DEFAULT_SENDER_ID = "gnome-bridge-companion"


@dataclass(frozen=True)
class SendResult:
    sent: bool
    attempts: int
    error: Optional[str]
    elapsed_ms: int


def build_activate_payload(
    *,
    binding_id: str,
    token: str,
    sender_id: str = DEFAULT_SENDER_ID,
    timestamp_ms: Optional[int] = None,
    nonce_factory: Optional[Callable[[], str]] = None,
) -> dict[str, object]:
    return {
        "version": "1",
        "type": "activate",
        "binding_id": binding_id,
        "timestamp_ms": int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms),
        "nonce": (nonce_factory or (lambda: secrets.token_hex(16)))(),
        "token": token,
        "sender_id": sender_id,
    }


def resolve_token(*, token: str, token_file: str) -> str:
    explicit = token.strip()
    if explicit:
        return explicit
    if not token_file.strip():
        return ""
    path = Path(token_file)
    resolved = path.read_text(encoding="utf-8").strip()
    if len(resolved) < 16:
        raise ValueError(f"token in '{path}' is too short")
    return resolved


def send_payload_with_retries(
    *,
    socket_path: str,
    payload: bytes,
    retries: int = DEFAULT_RETRIES,
    initial_backoff_ms: int = DEFAULT_INITIAL_BACKOFF_MS,
    max_backoff_ms: int = DEFAULT_MAX_BACKOFF_MS,
    socket_factory: Callable[[], socket.socket] = lambda: socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM),
    sleep_fn: Callable[[float], None] = time.sleep,
    logger: Optional[logging.Logger] = None,
) -> SendResult:
    log = logger or logging.getLogger("EDMCHotkeys.companion.send")
    attempts = 0
    start = time.monotonic()
    backoff_ms = max(1, initial_backoff_ms)
    last_error: Optional[str] = None
    max_attempts = max(1, retries + 1)

    for attempt_idx in range(max_attempts):
        attempts = attempt_idx + 1
        sock = socket_factory()
        try:
            sock.sendto(payload, socket_path)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return SendResult(sent=True, attempts=attempts, error=None, elapsed_ms=elapsed_ms)
        except OSError as exc:
            last_error = str(exc)
            if attempts >= max_attempts:
                break
            log.warning(
                "Companion send attempt failed: attempt=%d/%d socket=%s error=%s",
                attempts,
                max_attempts,
                socket_path,
                exc,
            )
            sleep_fn(backoff_ms / 1000.0)
            backoff_ms = min(max(1, max_backoff_ms), backoff_ms * 2)
        finally:
            try:
                sock.close()
            except OSError:
                pass

    elapsed_ms = int((time.monotonic() - start) * 1000)
    return SendResult(sent=False, attempts=attempts, error=last_error, elapsed_ms=elapsed_ms)


def write_telemetry(*, telemetry_file: str, result: SendResult, payload: dict[str, object], socket_path: str) -> None:
    if not telemetry_file.strip():
        return
    path = Path(telemetry_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp_ms": int(time.time() * 1000),
        "socket_path": socket_path,
        "binding_id": payload.get("binding_id"),
        "sender_id": payload.get("sender_id"),
        **asdict(result),
    }
    path.write_text(json.dumps(event, sort_keys=True), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send hardened activate payload to EDMC GNOME bridge backend")
    parser.add_argument("--socket", required=True, help="Path to bridge Unix datagram socket")
    parser.add_argument("--binding-id", required=True, help="Binding id to activate")
    parser.add_argument("--token", default="", help="Auth token override")
    parser.add_argument("--token-file", default="", help="Path to token file")
    parser.add_argument("--sender-id", default=DEFAULT_SENDER_ID, help="Sender id for payload")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Retry count after first attempt")
    parser.add_argument(
        "--initial-backoff-ms",
        type=int,
        default=DEFAULT_INITIAL_BACKOFF_MS,
        help="Initial retry backoff in milliseconds",
    )
    parser.add_argument(
        "--max-backoff-ms",
        type=int,
        default=DEFAULT_MAX_BACKOFF_MS,
        help="Maximum retry backoff in milliseconds",
    )
    parser.add_argument("--telemetry-file", default="", help="Optional file to write last send telemetry JSON")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("EDMCHotkeys.companion.send")

    if args.retries < 0:
        log.error("--retries must be >= 0")
        return 2
    if args.initial_backoff_ms <= 0 or args.max_backoff_ms <= 0:
        log.error("--initial-backoff-ms and --max-backoff-ms must be > 0")
        return 2

    try:
        token = resolve_token(token=args.token, token_file=args.token_file)
    except Exception as exc:
        log.error("Failed to resolve token: %s", exc)
        return 2

    payload = build_activate_payload(
        binding_id=args.binding_id.strip(),
        token=token,
        sender_id=args.sender_id.strip() or DEFAULT_SENDER_ID,
    )
    encoded_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    result = send_payload_with_retries(
        socket_path=args.socket,
        payload=encoded_payload,
        retries=args.retries,
        initial_backoff_ms=args.initial_backoff_ms,
        max_backoff_ms=args.max_backoff_ms,
        logger=log,
    )
    write_telemetry(
        telemetry_file=args.telemetry_file,
        result=result,
        payload=payload,
        socket_path=args.socket,
    )
    if result.sent:
        return 0
    log.error(
        "Companion send failed: attempts=%d socket=%s error=%s",
        result.attempts,
        args.socket,
        result.error,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
