# Companion Helper Sender

Primary entrypoint:
- `gnome_bridge_companion_send.py`

Responsibilities:
- Build protocol-v1 `activate` payloads.
- Load auth token from explicit token or token file.
- Send datagram payloads with bounded retry/backoff.
- Write optional telemetry JSON for troubleshooting.

Fallback behavior:
- Missing/invalid token file: exits non-zero with explicit error.
- Missing socket or send failure: retries up to configured limit, then exits non-zero.
- Helper failure is isolated to activation event; plugin startup is unaffected.
