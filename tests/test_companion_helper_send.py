from __future__ import annotations

import json
from pathlib import Path
import socket

from companion.helper import gnome_bridge_companion_send as helper


class _FakeSocket:
    def __init__(self, outcomes: list[object], sent: list[tuple[bytes, str]]) -> None:
        self._outcomes = outcomes
        self._sent = sent

    def sendto(self, payload: bytes, path: str) -> int:
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        self._sent.append((payload, path))
        return int(outcome)

    def close(self) -> None:
        return None


def test_resolve_token_prefers_explicit_over_file(tmp_path: Path) -> None:
    token_file = tmp_path / "sender.token"
    token_file.write_text("from-file-token-value\n", encoding="utf-8")

    resolved = helper.resolve_token(token="from-arg-token-value", token_file=str(token_file))

    assert resolved == "from-arg-token-value"


def test_resolve_token_loads_token_file(tmp_path: Path) -> None:
    token_file = tmp_path / "sender.token"
    token_file.write_text("from-file-token-value\n", encoding="utf-8")

    resolved = helper.resolve_token(token="", token_file=str(token_file))

    assert resolved == "from-file-token-value"


def test_build_activate_payload_contains_required_fields() -> None:
    payload = helper.build_activate_payload(
        binding_id="binding-1",
        token="token-value",
        sender_id="sender-test",
        timestamp_ms=1234,
        nonce_factory=lambda: "nonce-1",
    )

    assert payload["version"] == "1"
    assert payload["type"] == "activate"
    assert payload["binding_id"] == "binding-1"
    assert payload["timestamp_ms"] == 1234
    assert payload["nonce"] == "nonce-1"
    assert payload["token"] == "token-value"
    assert payload["sender_id"] == "sender-test"


def test_send_payload_with_retries_succeeds_after_retry() -> None:
    outcomes: list[object] = [socket.error("first failure"), 42]
    sent: list[tuple[bytes, str]] = []
    sleeps: list[float] = []

    result = helper.send_payload_with_retries(
        socket_path="/tmp/test.sock",
        payload=b"payload",
        retries=1,
        initial_backoff_ms=5,
        max_backoff_ms=20,
        socket_factory=lambda: _FakeSocket(outcomes, sent),  # type: ignore[arg-type]
        sleep_fn=sleeps.append,
    )

    assert result.sent is True
    assert result.attempts == 2
    assert sent == [(b"payload", "/tmp/test.sock")]
    assert sleeps == [0.005]


def test_send_payload_with_retries_fails_after_limit() -> None:
    outcomes: list[object] = [socket.error("fail-1"), socket.error("fail-2")]
    sent: list[tuple[bytes, str]] = []

    result = helper.send_payload_with_retries(
        socket_path="/tmp/test.sock",
        payload=b"payload",
        retries=1,
        initial_backoff_ms=1,
        max_backoff_ms=1,
        socket_factory=lambda: _FakeSocket(outcomes, sent),  # type: ignore[arg-type]
        sleep_fn=lambda _seconds: None,
    )

    assert result.sent is False
    assert result.attempts == 2
    assert "fail-2" in (result.error or "")
    assert sent == []


def test_write_telemetry_writes_json(tmp_path: Path) -> None:
    telemetry_file = tmp_path / "telemetry" / "last.json"
    result = helper.SendResult(sent=True, attempts=1, error=None, elapsed_ms=3)
    payload = {"binding_id": "b1", "sender_id": "sender"}

    helper.write_telemetry(
        telemetry_file=str(telemetry_file),
        result=result,
        payload=payload,
        socket_path="/tmp/test.sock",
    )

    written = json.loads(telemetry_file.read_text(encoding="utf-8"))
    assert written["sent"] is True
    assert written["attempts"] == 1
    assert written["binding_id"] == "b1"
    assert written["socket_path"] == "/tmp/test.sock"
