#!/usr/bin/env python3
"""Send a prototype GNOME bridge activation payload to EDMC-Hotkeys."""

from __future__ import annotations

import argparse
import json
import socket


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send bridge payload to EDMC-Hotkeys GNOME bridge backend")
    parser.add_argument("--socket", required=True, help="Path to Unix datagram socket")
    parser.add_argument("--binding-id", required=True, help="Binding id to activate")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Send payload as JSON {\"binding_id\": ...} instead of plain text",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.json:
        payload = json.dumps({"binding_id": args.binding_id}).encode("utf-8")
    else:
        payload = args.binding_id.encode("utf-8")

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sock.sendto(payload, args.socket)
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
