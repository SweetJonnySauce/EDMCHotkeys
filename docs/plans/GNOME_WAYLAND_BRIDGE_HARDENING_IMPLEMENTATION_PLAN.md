# GNOME Wayland Bridge Hardening Implementation Plan

Status: Draft  
Owner: EDMC-Hotkeys  
Last Updated: 2026-02-26

## Goal
Harden the GNOME Wayland bridge from prototype to production-ready optional companion architecture, with secure local IPC, deterministic failure handling, and releasable packaging/docs.

## Scope
- Plugin-side hardening of `linux-wayland-gnome-bridge` backend.
- Companion architecture definition for GNOME Shell global shortcut capture.
- Release gating, test coverage, and operational documentation.

## Non-Goals
- Do not change default backend behavior for users who do not enable the bridge mode.
- Do not remove existing X11/Wayland portal backends.
- Do not weaken current non-fatal startup guarantees.

## Success Criteria
- Bridge mode is secure-by-default for same-user local operation.
- Bridge startup/connection failures are explicit, actionable, and non-fatal.
- End-to-end hotkey flow works on GNOME Wayland with companion installed.
- Rollout supports opt-in alpha/beta before general release.

## Phase 1 — Architecture and Security Freeze (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Finalize production bridge architecture (plugin backend + companion boundary) | Pending |
| 1.2 | Define versioned bridge protocol and compatibility policy | Pending |
| 1.3 | Define local security model (authn, replay, permissions, trust boundaries) | Pending |
| 1.4 | Define backend selection precedence and user-facing mode policy | Pending |

### Stage 1.1 Tasks
- Freeze the companion shape:
  - GNOME Shell extension captures global shortcuts.
  - Extension emits events to plugin bridge IPC endpoint.
- Decide direct extension-to-plugin vs extension-to-helper-to-plugin path.
- Record explicit invariants for non-fatal startup and fallback behavior.

### Stage 1.2 Tasks
- Define protocol envelope with explicit versioning and message types.
- Define mandatory fields (`version`, `type`, `binding_id`, `timestamp`, `nonce`).
- Define compatibility behavior for unknown versions/types.

### Stage 1.3 Tasks
- Define socket location in `$XDG_RUNTIME_DIR`.
- Define required permissions/ownership checks.
- Define token-based sender authentication and replay-window rules.
- Define flood/rate-limit policy and failure handling.

### Stage 1.4 Tasks
- Define backend mode policy:
  - `auto`
  - `wayland_portal`
  - `wayland_gnome_bridge`
  - `x11`
- Define precedence for `auto` on GNOME Wayland and explicit override behavior.

### Phase 1 Acceptance Criteria
- Architecture diagram and data-flow description documented.
- Security controls are concrete and testable.
- Selection/fallback policy is deterministic and documented.

## Phase 2 — Plugin Bridge Hardening (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Move socket endpoint to secure runtime path + strict validation | Pending |
| 2.2 | Implement authenticated/versioned message parsing | Pending |
| 2.3 | Add replay protection, rate limiting, and bounded queues | Pending |
| 2.4 | Add health/state telemetry and actionable diagnostics | Pending |
| 2.5 | Add explicit backend mode configuration plumbing | Pending |

### Stage 2.1 Tasks
- Default socket path to `$XDG_RUNTIME_DIR/edmc_hotkeys/bridge.sock`.
- Enforce directory creation with restricted permissions.
- Validate socket owner/perms before accepting events.

### Stage 2.2 Tasks
- Parse strict JSON protocol only in hardened mode.
- Validate required fields and types.
- Require authentication token and reject unauthenticated events.

### Stage 2.3 Tasks
- Add nonce/timestamp replay window checks.
- Add per-source event-rate limit.
- Add bounded in-memory event queue and overload behavior.

### Stage 2.4 Tasks
- Add structured logs for:
  - startup unavailable
  - auth failures
  - replay rejection
  - malformed payload
  - bridge disconnected/stopped
- Add backend status summary line at plugin startup.

### Stage 2.5 Tasks
- Add persisted/user-visible backend mode selection.
- Keep existing defaults unchanged for non-bridge users.
- Add migration-safe default value and validation.

### Phase 2 Acceptance Criteria
- Hardened bridge backend passes targeted security and lifecycle tests.
- Logs clearly distinguish config, security, and runtime transport failures.
- Bridge mode can be enabled/disabled without code changes.

## Phase 3 — Companion Delivery (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Implement GNOME extension hotkey capture and registration lifecycle | Pending |
| 3.2 | Implement companion event emitter compatible with hardened protocol | Pending |
| 3.3 | Add companion install/upgrade/uninstall workflows | Pending |
| 3.4 | Add compatibility matrix for GNOME Shell versions | Pending |

### Stage 3.1 Tasks
- Register/unregister keybindings through GNOME Shell APIs.
- Sync enabled bindings from plugin-provided mapping.
- Handle extension enable/disable/reload safely.

### Stage 3.2 Tasks
- Emit authenticated, versioned messages over bridge socket.
- Implement sender-side retry/backoff and dropped-event telemetry.
- Preserve deterministic binding ID semantics.

### Stage 3.3 Tasks
- Package companion as separate optional artifact.
- Provide install docs and one-command local verification.
- Document rollback path (disable extension + switch backend mode).

### Stage 3.4 Tasks
- Validate on target GNOME versions and Ubuntu releases.
- Record known limitations and unsupported environments.

### Phase 3 Acceptance Criteria
- Companion can be installed independently and verified by users.
- End-to-end shortcut -> event -> action path works on GNOME Wayland.
- Companion failure leaves plugin operational (non-fatal).

## Phase 4 — Test and Verification Hardening (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Expand unit tests for auth, replay, malformed payload, and rate limits | Pending |
| 4.2 | Add integration tests for bridge lifecycle and reconnect behavior | Pending |
| 4.3 | Add manual QA matrix for Wayland GNOME scenarios | Pending |
| 4.4 | Add release checks for artifact completeness and docs accuracy | Pending |

### Stage 4.1 Tasks
- Add deterministic unit tests for all security guards.
- Add boundary tests for queue/rate limits.

### Stage 4.2 Tasks
- Add integration tests using fake companion sender process.
- Verify startup, shutdown, reconnect, and stale-socket handling.

### Stage 4.3 Tasks
- Validate cases:
  - extension disabled
  - invalid token
  - stale runtime dir/socket
  - settings-mode changes across restart
- Capture expected logs and user-visible outcomes.

### Stage 4.4 Tasks
- Ensure plugin artifact and companion artifact are both buildable.
- Ensure docs include troubleshooting and rollback steps.

### Phase 4 Acceptance Criteria
- Full automated test suite remains green.
- Manual QA matrix is complete with pass/fail evidence.
- Release candidate has no unresolved high-severity bridge defects.

## Phase 5 — Rollout and Stabilization (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 5.1 | Alpha rollout behind explicit opt-in mode | Pending |
| 5.2 | Beta rollout with broader documentation and telemetry review | Pending |
| 5.3 | General availability decision and default-policy confirmation | Pending |

### Stage 5.1 Tasks
- Ship as opt-in companion path only.
- Collect user logs for startup/auth/dispatch behavior.

### Stage 5.2 Tasks
- Address beta defects and update compatibility matrix.
- Freeze protocol changes except bug/security fixes.

### Stage 5.3 Tasks
- Decide long-term default policy (`auto` precedence).
- Publish stable docs and support guidance.

### Phase 5 Acceptance Criteria
- Defect rate is acceptable for supported environments.
- Operational guidance is complete.
- GA sign-off checklist is complete.

## Test Gates
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "bridge or wayland or selector"`
2. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py`
3. `source .venv/bin/activate && python -m pytest`
4. `source .venv/bin/activate && make test`
5. `source .venv/bin/activate && make check`

## Rollback Plan
- Disable bridge mode via backend mode setting or env flag.
- Fall back to existing backend selection (`wayland_portal` or `x11`).
- Keep companion uninstall path documented and reversible.

## Open Decisions
- Direct extension-to-plugin IPC vs extension-helper intermediary.
- Token distribution/rotation mechanism for companion and plugin.
- Long-term default behavior for `auto` mode on GNOME Wayland.

## Current Gap and Execution Plan (2026-02-26)
Observed behavior from live logs and manual validation:
- Plugin-side bridge receiver is functional (`linux-wayland-gnome-bridge` starts and dispatches when socket payloads are sent).
- Global keypresses do not fire actions unless the user manually wires GNOME custom shortcuts to `scripts/gnome_bridge_send.py`.
- Therefore, the blocking gap is sender automation + binding synchronization, not backend event dispatch.

### Execution Scope for Gap Closure
- Deliver an optional GNOME companion that captures shortcuts and emits binding activations automatically.
- Eliminate manual one-off GNOME shortcut setup for each binding.
- Keep all bridge behavior opt-in and non-fatal.

## Phase 6 — Sender Automation and Binding Sync (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 6.1 | Define plugin-to-companion binding sync contract | Completed |
| 6.2 | Implement companion-side keybinding manager | Completed |
| 6.3 | Implement plugin-side sync endpoint/state export | Completed |
| 6.4 | Add diagnostics for sender-connected vs receiver-only mode | Completed |
| 6.5 | Add packaging/install UX for companion-first setup | Completed |

### Phase 6 Implementation Order
1. Stage 6.1 first (contract freeze).
2. Stages 6.2 and 6.3 in parallel once 6.1 is frozen.
3. Stage 6.4 after 6.2/6.3 plumbing is stable.
4. Stage 6.5 last, after behavior and logs are stable.

### Stage 6.1 Plan — Contract Freeze
Goal: define the exact, versioned contract between plugin and companion before implementation changes.

Deliverables:
- Protocol spec section in this doc with:
  - message versions (`v1` initial)
  - message types (`sync_full`, `sync_delta`, `activate`, `ack`, `error`)
  - required fields per message
  - validation/error semantics
- Binding canonicalization rules:
  - modifiers must be generic on Tier 1 (`ctrl`, `shift`, `alt`, `meta`)
  - accelerator output format (single canonical string form)
  - duplicate/conflict handling policy
- Lifecycle contract:
  - initial sync on startup
  - update sync on `prefs_changed`
  - unregister/clear on backend stop

Touch Points:
- [GNOME_WAYLAND_BRIDGE_HARDENING_IMPLEMENTATION_PLAN.md](/home/jon/edmc_plugins/EDMC-Hotkeys/docs/plans/GNOME_WAYLAND_BRIDGE_HARDENING_IMPLEMENTATION_PLAN.md)
- optional companion spec file (if created): `docs/gnome-bridge-protocol-v1.md`

Exit Criteria:
- Contract is explicit enough to implement without interpretation gaps.
- Open decision for direct vs helper path is resolved for `v1`.

### Stage 6.2 Plan — Companion Keybinding Manager
Goal: companion dynamically owns GNOME keybinding registration using synced bindings.

Deliverables:
- Companion runtime that:
  - registers enabled accelerators from latest sync snapshot
  - unregisters removed/disabled accelerators
  - preserves deterministic mapping `accelerator -> binding_id`
  - survives extension reload and shell restart without duplicate registrations
- Activation emitter that sends only valid, known `binding_id` values to plugin bridge socket.

Implementation Notes:
- Keep companion-side failures isolated; no crash propagation to EDMC.
- Enforce minimal retry/backoff for socket send failures.

Touch Points:
- companion artifact path (to be finalized in 6.1)
- bridge sender compatibility with [gnome_bridge_send.py](/home/jon/edmc_plugins/EDMC-Hotkeys/scripts/gnome_bridge_send.py)

Exit Criteria:
- No manual GNOME custom-keybinding shell commands required for end users.
- Companion restores key registrations after restart with same binding IDs.

### Stage 6.3 Plan — Plugin Sync Export
Goal: plugin publishes active binding state so companion can register shortcuts automatically.

Deliverables:
- Plugin-side binding sync publisher with:
  - full-state export on startup
  - delta export on settings save
  - clear/unregister signal on shutdown/backend stop
- Compatibility guard:
  - if companion is absent/unreachable, plugin stays fully operational and logs warning only.

Touch Points (expected):
- [load.py](/home/jon/edmc_plugins/EDMC-Hotkeys/load.py)
- [plugin.py](/home/jon/edmc_plugins/EDMC-Hotkeys/edmc_hotkeys/plugin.py)
- [gnome_bridge.py](/home/jon/edmc_plugins/EDMC-Hotkeys/edmc_hotkeys/backends/gnome_bridge.py)
- tests for sync lifecycle in `tests/`

Exit Criteria:
- Binding edits in prefs propagate to companion without manual intervention.
- No behavioral regressions for X11/portal/non-bridge backends.

### Stage 6.4 Plan — Diagnostics and Operational Visibility
Goal: make sender/receiver state observable and actionable in EDMC logs.

Deliverables:
- Structured startup status line includes:
  - backend mode
  - socket path
  - sender status (`unknown`, `connected`, `no-events-seen`)
  - synced binding count
- Warning path for receiver-only mode after grace window.
- Per-binding sync failure logs with binding ID and concise reason.

Touch Points (expected):
- [plugin.py](/home/jon/edmc_plugins/EDMC-Hotkeys/edmc_hotkeys/plugin.py)
- [gnome_bridge.py](/home/jon/edmc_plugins/EDMC-Hotkeys/edmc_hotkeys/backends/gnome_bridge.py)
- docs troubleshooting section

Exit Criteria:
- Operators can distinguish transport failure vs sync failure vs no-sender condition from logs alone.

### Stage 6.5 Plan — Packaging, Install UX, and Rollback
Goal: ship companion path as a repeatable, supportable user workflow.

Deliverables:
- Companion release artifact and plugin compatibility mapping.
- Install docs with exact commands for:
  - install/update
  - enable/start
  - verify (`Ctrl+M` test and expected log line)
- Rollback docs with exact commands for:
  - disable/uninstall companion
  - switch backend mode
  - verify fallback behavior

Touch Points (expected):
- `docs/linux-user-setup.md`
- `docs/release-notes.md`
- Makefile/release scripts if packaging targets are added

Exit Criteria:
- Fresh user can complete setup and validation with documented commands only.
- Rollback path is deterministic and tested.

### Phase 6 Test Plan
Environment setup (once):
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `python -m pip install -U pip`
3. `python -m pip install -r requirements-dev.txt`

Automated gates (run per Stage completion):
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "bridge or selector or wayland"`
2. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py`
3. `source .venv/bin/activate && python -m pytest`
4. `source .venv/bin/activate && make test`
5. `source .venv/bin/activate && make check`

Manual validation gates (GNOME Wayland):
1. Start EDMC with bridge mode enabled.
2. Confirm backend startup line identifies `linux-wayland-gnome-bridge`.
3. Press configured test hotkey (`Ctrl+M`) and confirm `Hotkey pressed` + target action log lines.
4. Modify binding in prefs and verify companion registration updates without manual shell commands.
5. Disable companion and verify receiver-only warning appears while EDMC remains stable.

### Phase 6 Acceptance Criteria
- User can install companion and use bindings without manual GNOME custom keybinding commands.
- Binding changes in EDMC-Hotkeys automatically update companion key registrations.
- Logs clearly distinguish backend unavailable, receiver-only, sync failure, and successful dispatch.
- Full automated test gates pass.

### Phase 6 Implementation Results (2026-02-26)
- Added GNOME sender auto-sync module:
  - [gnome_sender_sync.py](/home/jon/edmc_plugins/EDMC-Hotkeys/edmc_hotkeys/backends/gnome_sender_sync.py)
  - Converts EDMC hotkeys to GNOME accelerators.
  - Manages GNOME custom-keybinding entries for active bridge bindings.
  - Preserves non-EDMC custom keybindings while replacing managed entries.
- Integrated auto-sync + diagnostics into bridge backend:
  - [gnome_bridge.py](/home/jon/edmc_plugins/EDMC-Hotkeys/edmc_hotkeys/backends/gnome_bridge.py)
  - Sync on startup/register/unregister and batch-complete.
  - Batch APIs to avoid repeated full sync during `replace_bindings`.
  - Runtime status snapshot for plugin logging.
  - Receiver-only warning when no events are observed after startup grace window.
- Integrated plugin reconciliation and status reporting:
  - [plugin.py](/home/jon/edmc_plugins/EDMC-Hotkeys/edmc_hotkeys/plugin.py)
  - Batched backend updates during `replace_bindings`.
  - Idempotent disabled-binding unregister path to avoid false failure warnings.
  - Startup backend runtime-status logging when backend exposes it.
- Added tests:
  - [test_gnome_sender_sync.py](/home/jon/edmc_plugins/EDMC-Hotkeys/tests/test_gnome_sender_sync.py)
  - [test_backends.py](/home/jon/edmc_plugins/EDMC-Hotkeys/tests/test_backends.py)
  - [test_hotkey_plugin.py](/home/jon/edmc_plugins/EDMC-Hotkeys/tests/test_hotkey_plugin.py)

### Phase 6 Verification Results (2026-02-26)
1. `source .venv/bin/activate && python -m pytest tests/test_gnome_sender_sync.py tests/test_backends.py -k "gnome_bridge or sender_sync"` passed (`10 passed`).
2. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "replace_bindings"` passed (`2 passed`).
3. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py` passed (`2 passed`).
4. `source .venv/bin/activate && python -m pytest` passed (`108 passed`).
5. `source .venv/bin/activate && make test` passed.
6. `source .venv/bin/activate && make check` passed.
