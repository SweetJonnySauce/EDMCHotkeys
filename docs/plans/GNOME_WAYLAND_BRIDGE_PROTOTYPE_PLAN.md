# GNOME Wayland Bridge Prototype Plan

Status: Completed  
Owner: EDMC-Hotkeys  
Last Updated: 2026-02-26

## Goal
Prototype an optional companion-style backend for GNOME Wayland that accepts externally emitted hotkey events (from a GNOME extension/bridge process) and dispatches registered binding IDs inside EDMC-Hotkeys.

## Non-Goals
- No GNOME extension implementation in this phase.
- No default behavior change for existing Wayland portal, X11, or Windows paths.
- No new persistent settings schema in EDMC config for this prototype.

## Phase 1 — Design and Interface Freeze (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Define feature-flag gating and backend selection precedence | Completed |
| 1.2 | Define local IPC protocol and listener lifecycle | Completed |
| 1.3 | Define logging and failure behavior contracts | Completed |

### Stage 1.1 Output
- Feature flag: `EDMC_HOTKEYS_GNOME_BRIDGE=1` enables prototype backend selection on Linux Wayland.
- Socket path override: `EDMC_HOTKEYS_GNOME_BRIDGE_SOCKET` (default `/tmp/edmc_hotkeys_gnome_bridge.sock`).
- Selection precedence on Wayland:
  1. GNOME bridge backend when feature flag is enabled.
  2. Existing Wayland portal backend otherwise.

### Stage 1.2 Output
- IPC transport: Unix datagram socket.
- Message format accepted:
  - plain text binding id (`binding-id`)
  - JSON object with `binding_id` field (`{"binding_id":"binding-id"}`)
- Dispatch rule:
  - invoke callback only for currently registered binding IDs.

### Stage 1.3 Output
- Startup remains non-fatal (returns `False` on failure with warning log).
- Unknown/invalid bridge messages log diagnostics and are ignored.
- Existing backend capability contract remains unchanged (`supports_side_specific_modifiers=False` for Wayland bridge path).

## Phase 2 — Prototype Implementation (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Add `GnomeWaylandBridgeBackend` implementation | Completed |
| 2.2 | Wire selector for feature-flagged Wayland bridge selection | Completed |
| 2.3 | Add tests for backend behavior and selection precedence | Completed |
| 2.4 | Add prototype usage documentation | Completed |

## Phase 3 — Validation (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Run targeted backend tests | Completed |
| 3.2 | Run repository test/check targets | Completed |
| 3.3 | Record prototype limits and next steps | Completed |

## Tests To Run
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland or bridge or selector"`
2. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py`
3. `source .venv/bin/activate && python -m pytest`
4. `source .venv/bin/activate && make check`

## Implementation Results
### Phase 2 Results
- Added prototype backend: `edmc_hotkeys/backends/gnome_bridge.py`
  - feature-flag gated availability on Wayland (`EDMC_HOTKEYS_GNOME_BRIDGE=1`)
  - Unix datagram socket listener with payload support for plain binding IDs and JSON (`{"binding_id": ...}`)
  - callback dispatch only for registered binding IDs
- Selector wiring updated in `edmc_hotkeys/backends/selector.py`
  - new Wayland precedence path for GNOME bridge when feature flag is enabled
  - helper `gnome_bridge_enabled(...)`
- Backend exports updated in `edmc_hotkeys/backends/__init__.py`
- Added prototype send utility: `scripts/gnome_bridge_send.py`
- Added user documentation: `docs/gnome-wayland-bridge-prototype.md`

### Phase 3 Results
- `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland or bridge or selector"` passed (`19 passed, 16 deselected`).
- `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py` passed (`2 passed`).
- `source .venv/bin/activate && python -m pytest` passed (`91 passed`).
- `source .venv/bin/activate && make check` passed.

## Prototype Limits and Next Steps
- This prototype does not include a GNOME Shell extension; it only provides the plugin-side bridge backend.
- The bridge is opt-in and does not change default backend behavior.
- Next step for real user value:
  1. Build/publish a small GNOME extension companion that emits binding IDs to the configured socket.
  2. Define secure per-user socket permissions/handshake for production hardening.
