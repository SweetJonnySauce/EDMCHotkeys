#!/usr/bin/env python3
"""Send authenticated keyd activation payloads to EDMCHotkeys keyd backend."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import time


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send keyd activation payload to EDMCHotkeys")
    parser.add_argument("--socket", required=True, help="Path to keyd backend Unix datagram socket")
    parser.add_argument("--binding-id", required=True, help="Binding id to activate")
    parser.add_argument("--token", default="", help="Authentication token override")
    parser.add_argument("--token-file", default="", help="Path to file containing authentication token")
    parser.add_argument("--sender-id", default="keyd-send", help="Sender id included in payload")
    return parser.parse_args(argv)


def _diag_log_path(socket_path: str) -> Path:
    socket_candidate = Path(socket_path)
    if socket_candidate.parent:
        return socket_candidate.with_name("keyd_send.log")
    return Path("/tmp/edmchotkeys/keyd_send.log")


def _diag_log(socket_path: str, message: str) -> None:
    try:
        log_path = _diag_log_path(socket_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"{timestamp} pid={os.getpid()} {message}\n"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except Exception:
        return


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    token = args.token.strip()
    token_file = args.token_file.strip()
    if not token:
        token_path = Path(token_file) if token_file else Path(args.socket).with_name("sender.token")
        try:
            token = token_path.read_text(encoding="utf-8").strip()
        except Exception as exc:
            _diag_log(args.socket, f"token-load-failed token_file={token_path} error={exc}")
            print(f"keyd_send: failed to load token file '{token_path}': {exc}", file=sys.stderr)
            return 2
    if len(token) < 16:
        _diag_log(args.socket, "token-invalid token-too-short")
        print("keyd_send: token is missing or too short", file=sys.stderr)
        return 2

    payload = {
        "version": "1",
        "type": "activate",
        "binding_id": args.binding_id.strip(),
        "timestamp_ms": int(time.time() * 1000),
        "nonce": secrets.token_hex(16),
        "token": token,
        "sender_id": args.sender_id.strip() or "keyd-send",
    }
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sock.sendto(encoded, args.socket)
        _diag_log(args.socket, f"send-ok binding_id={args.binding_id.strip()}")
    except Exception as exc:
        _diag_log(args.socket, f"send-failed binding_id={args.binding_id.strip()} error={exc}")
        raise
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
