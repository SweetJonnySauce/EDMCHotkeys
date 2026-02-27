# GNOME Bridge Threat Model (Phase 1 Freeze)

Status: Frozen for hardening implementation planning (2026-02-26)

## Scope
Threats and controls for local GNOME bridge transport between sender and EDMC plugin backend.

## Trust Boundaries
- Sender process boundary (GNOME keybinding command/helper).
- Local IPC boundary (Unix socket transport).
- Plugin backend boundary (activation dispatch into EDMC plugin runtime).

## Asset/Impact Summary
- Assets:
  - Correct binding activation routing.
  - Sender authenticity.
  - EDMC process stability.
- Primary impacts:
  - Unauthorized action triggers.
  - Replay-triggered repeated actions.
  - Event flood causing degraded responsiveness.

## Threat Table
| Threat | Scenario | Mitigation Target | Residual Risk |
| --- | --- | --- | --- |
| Unauthorized local sender | Any local process sends forged payload | Token auth + socket ownership checks | Same-user local compromise remains possible |
| Replay attack | Captured payload is resent repeatedly | Timestamp window + nonce replay cache | Small replay window false negatives possible on clock skew |
| Flood/DoS | Sender emits rapid payloads | Per-sender/global rate limits + bounded queues | Short-term dropped events under overload |
| Malformed payload abuse | Invalid payload shapes trigger parser issues | Strict schema validation + safe reject | Legacy compatibility path remains weaker until removed |
| Misconfigured runtime path | World-accessible socket path | `$XDG_RUNTIME_DIR` + restrictive perms | Deployment misconfiguration still possible |

## Security Controls (Frozen Targets)
- Runtime path:
  - socket under `$XDG_RUNTIME_DIR/edmc_hotkeys/bridge.sock`
  - directory permissions: `0700`
  - socket permissions: `0600`
- Ownership validation:
  - reject startup/operation when owner or permissions are unsafe
- Authentication:
  - random token (minimum 128-bit entropy)
  - token required in strict/hardened mode
- Replay protection:
  - `timestamp_ms` acceptance window (target: +/- 5 seconds)
  - nonce cache (target: 1024 recent nonces; TTL >= replay window)
- Rate limiting:
  - sender-level and global limits (target baseline: 30 events / 5 seconds / sender)
  - bounded queue with drop-and-log behavior

## Logging Policy
- Must log:
  - auth failures
  - replay rejections
  - malformed payload rejects
  - rate-limit drops
- Must not log:
  - raw tokens
  - sensitive secret material

## Implementation Mapping
| Control | Planned Phase |
| --- | --- |
| Secure runtime path/perms | Phase 2.1 |
| Strict v1 validation/auth | Phase 2.2 |
| Replay + rate limits + bounded queue | Phase 2.3 |
| Security diagnostics clarity | Phase 2.4 |

## Explicit Deferred Items
- Cryptographic transport security beyond local IPC constraints.
- Multi-user/session federation support.
- Remote sender trust model.
