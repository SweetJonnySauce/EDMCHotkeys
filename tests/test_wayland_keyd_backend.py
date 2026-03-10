from __future__ import annotations

import json
from pathlib import Path
import secrets
import time

from edmc_hotkeys.backends.wayland_keyd import WaylandKeydBackend


def test_wayland_keyd_backend_dispatches_registered_binding_payload(tmp_path: Path) -> None:
    backend = WaylandKeydBackend(
        plugin_dir=tmp_path,
        environ={"WAYLAND_DISPLAY": "wayland-0"},
    )
    received: list[str] = []
    assert backend.availability().available is True
    backend._callback = lambda binding_id: received.append(binding_id)  # type: ignore[attr-defined]
    backend._auth_token = "a" * 64  # type: ignore[attr-defined]
    assert backend.register_hotkey("binding-1", "ctrl_l+a")
    backend._handle_payload(  # type: ignore[attr-defined]
        json.dumps(
            {
                "version": "1",
                "type": "activate",
                "binding_id": "binding-1",
                "timestamp_ms": int(time.time() * 1000),
                "nonce": secrets.token_hex(16),
                "token": "a" * 64,
                "sender_id": "test",
            }
        ).encode("utf-8")
    )
    assert received == ["binding-1"]


def test_wayland_keyd_backend_rejects_invalid_token_payload(tmp_path: Path) -> None:
    backend = WaylandKeydBackend(
        plugin_dir=tmp_path,
        environ={"WAYLAND_DISPLAY": "wayland-0"},
    )
    received: list[str] = []
    backend._callback = lambda binding_id: received.append(binding_id)  # type: ignore[attr-defined]
    backend._auth_token = "a" * 64  # type: ignore[attr-defined]
    assert backend.register_hotkey("binding-1", "ctrl_l+a")
    backend._handle_payload(  # type: ignore[attr-defined]
        json.dumps(
            {
                "version": "1",
                "type": "activate",
                "binding_id": "binding-1",
                "timestamp_ms": int(time.time() * 1000),
                "nonce": secrets.token_hex(16),
                "token": "bad-token",
                "sender_id": "test",
            }
        ).encode("utf-8")
    )
    assert received == []
