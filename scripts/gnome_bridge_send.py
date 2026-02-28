#!/usr/bin/env python3
"""Send a prototype GNOME bridge activation payload to EDMCHotkeys."""

from __future__ import annotations

import argparse
import json
import secrets
import socket
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send bridge payload to EDMCHotkeys GNOME bridge backend")
    parser.add_argument("--socket", required=True, help="Path to Unix datagram socket")
    parser.add_argument("--binding-id", required=True, help="Binding id to activate")
    parser.add_argument("--token", default="", help="Authentication token for hardened bridge mode")
    parser.add_argument("--token-file", default="", help="Path to file containing authentication token")
    parser.add_argument("--sender-id", default="gnome-bridge-send", help="Sender id included in v1 payload")
    parser.add_argument(
        "--json",
        action="store_true",
        help="When used with --legacy, send payload as JSON {\"binding_id\": ...} instead of plain text",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Send legacy payload format (plain binding id or JSON binding_id)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = args.token.strip()
    if not token and args.token_file:
        token_path = Path(args.token_file)
        token = token_path.read_text(encoding="utf-8").strip()

    if args.legacy:
        if args.json:
            payload = json.dumps({"binding_id": args.binding_id}).encode("utf-8")
        else:
            payload = args.binding_id.encode("utf-8")
    else:
        payload = json.dumps(
            {
                "version": "1",
                "type": "activate",
                "binding_id": args.binding_id,
                "timestamp_ms": int(time.time() * 1000),
                "nonce": secrets.token_hex(16),
                "token": token,
                "sender_id": args.sender_id,
            }
        ).encode("utf-8")

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sock.sendto(payload, args.socket)
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
