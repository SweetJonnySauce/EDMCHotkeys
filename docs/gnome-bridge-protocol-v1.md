# GNOME Bridge Protocol v1 (Phase 1 Freeze)

Status: Frozen for implementation planning (2026-02-26)

## Scope
Defines message envelope, compatibility behavior, and validation rules for GNOME bridge transport.

Notes:
- Current implementation still supports legacy payload forms for compatibility.
- Hardened strict-v1 enforcement is planned in later phases.

## Envelope
All v1 messages use JSON object envelope.

Required fields:
- `version` (string): protocol version. Must be `"1"`.
- `type` (string): message type.
- `timestamp_ms` (integer): sender wall-clock timestamp in ms.
- `nonce` (string): sender-generated unique nonce.

Type-specific required fields:
- `activate`: `binding_id` (string)
- `sync_full`: `bindings` (array)
- `sync_delta`: `added` (array), `updated` (array), `removed` (array)
- `sync_clear`: no extra required fields
- `ack`: `request_id` (string), `status` (string)
- `error`: `code` (string), `message` (string)

Optional fields:
- `token` (string): auth token (required once hardened mode is enabled).
- `request_id` (string): correlation id.
- `sender_id` (string): sender identity hint.
- `meta` (object): additional forward-compatible metadata.

## Message Types
- `activate`:
  - Sender -> Plugin backend
  - Requests action dispatch for one `binding_id`.
- `sync_full`:
  - Plugin -> Sender abstraction
  - Full binding snapshot.
- `sync_delta`:
  - Plugin -> Sender abstraction
  - Incremental update.
- `sync_clear`:
  - Plugin -> Sender abstraction
  - Remove all managed registrations.
- `ack` / `error`:
  - Optional bidirectional response types for future sender/helper path.

## Compatibility Rules
| Condition | Behavior | Log Level |
| --- | --- | --- |
| Unknown `version` | Reject message | Warning |
| Missing required envelope field | Reject message | Warning |
| Unknown `type` | Ignore message | Warning |
| Missing type-specific field | Reject message | Warning |
| Extra unknown fields | Accept and ignore | Debug |

## Validation Rules
- `binding_id` must be non-empty trimmed string.
- `timestamp_ms` must be parseable integer.
- `nonce` must be non-empty and unique within replay window.
- `token` is mandatory when hardened auth mode is enabled.

## Legacy Compatibility Mode
Until strict-v1 is enabled in hardening phases, backend may accept:
- plain text payload: `binding-id`
- JSON payload: `{"binding_id":"binding-id"}`

Behavior:
- Legacy payloads are treated as implicit `activate` messages.
- Legacy payloads are unauthenticated and non-versioned.
- Log migration diagnostics when legacy payloads are consumed.

## Examples
Valid `activate`:
```json
{
  "version": "1",
  "type": "activate",
  "binding_id": "hotkeys_test_toggle",
  "timestamp_ms": 1772090400000,
  "nonce": "1f6b9a93-c72f-4f40-9d7e-cd6c95e8f9a2",
  "request_id": "req-001"
}
```

Invalid (missing `nonce`):
```json
{
  "version": "1",
  "type": "activate",
  "binding_id": "hotkeys_test_toggle",
  "timestamp_ms": 1772090400000
}
```

Unknown version:
```json
{
  "version": "2",
  "type": "activate",
  "binding_id": "hotkeys_test_toggle",
  "timestamp_ms": 1772090400000,
  "nonce": "abc"
}
```

## Mapping to Current Sender Path
- Current sender command path emits legacy payloads.
- Plugin-side sender sync currently happens via GNOME `gsettings`, not protocol transport.
- Future hardened path should converge on strict v1 for sender/helper transport.
