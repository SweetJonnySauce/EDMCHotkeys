# GNOME Wayland Bridge Hardening Implementation Plan

Status: In Progress (Phases 1, 2, 3, 4, and 6 completed; Phase 5 in progress)  
Owner: EDMCHotkeys  
Last Updated: 2026-02-27

## Goal
Harden the GNOME Wayland bridge from prototype to production-ready optional sender architecture, with secure local IPC, deterministic failure handling, and releasable packaging/docs.

## Scope
- Plugin-side hardening of `linux-wayland-gnome-bridge` backend.
- Companion-artifact architecture definition for GNOME Shell global shortcut capture.
- Release gating, test coverage, and operational documentation.

## Terminology
- Sender Path (Current):
  - Plugin-managed GNOME custom-keybinding sync via `gsettings` plus `gnome_bridge_send.py`.
- Companion Artifact (Future):
  - Separate GNOME extension/helper delivery track not yet shipped.

## Non-Goals
- Do not change default backend behavior for users who do not enable the bridge mode.
- Do not remove existing X11/Wayland portal backends.
- Do not weaken current non-fatal startup guarantees.

## Success Criteria
- Bridge mode is secure-by-default for same-user local operation.
- Bridge startup/connection failures are explicit, actionable, and non-fatal.
- End-to-end hotkey flow works on GNOME Wayland with the current sender path enabled.
- Rollout supports opt-in alpha/beta before general release.

## Current Baseline (After Phase 6 First)
- Implemented now:
  - GNOME bridge receiver + GNOME custom-keybinding sender auto-sync via `gsettings`.
  - Automatic bridge-binding sync on startup/settings updates.
  - Runtime diagnostics for sender sync status and receiver-only mode.
- Not implemented yet:
  - Hardened authenticated protocol (`token`, `nonce`, replay window).
  - Secure runtime socket move to `$XDG_RUNTIME_DIR`.
  - Separate GNOME extension/helper companion artifact track.

## Phase Ordering Note
- Execution intentionally ran Phase 6 before Phases 1-5 to prove user workflow viability on GNOME Wayland.
- Remaining phases are still required for production hardening and security posture.

## Phase 1 — Architecture and Security Freeze (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Finalize production bridge architecture (plugin backend + sender boundary) | Completed |
| 1.2 | Define versioned bridge protocol and compatibility policy | Completed |
| 1.3 | Define local security model (authn, replay, permissions, trust boundaries) | Completed |
| 1.4 | Define backend selection precedence and user-facing mode policy | Completed |

### Phase 1 Implementation Order
1. Complete `1.1` first (architecture freeze with explicit current vs future sender tracks).
2. Complete `1.2` next (protocol and compatibility contract).
3. Complete `1.3` next (security controls and abuse constraints).
4. Complete `1.4` last (selection policy and user-visible mode semantics).

### Stage 1.1 Plan — Architecture Freeze
Goal: freeze architecture boundaries so future implementation work cannot leak platform-specific behavior into plugin core.

Tasks:
- Document two explicit tracks:
  - current sender path (`gsettings` + `gnome_bridge_send.py`)
  - future companion-artifact path (extension/helper)
- Decide ownership boundaries:
  - plugin backend responsibilities
  - sender responsibilities
  - transport responsibilities
- Decide future companion-artifact topology:
  - extension -> plugin direct
  - extension -> helper -> plugin
- Record hard invariants:
  - startup non-fatal
  - missing sender never crashes EDMC
  - fallback remains possible and explicit

Deliverables:
- Architecture section with component diagram (logical, not implementation detail).
- Responsibility matrix by component.
- Invariants list with “must/should” wording.

Touch Points:
- this plan file
- optional architecture annex: `docs/architecture/gnome_bridge_architecture.md`

Exit Criteria:
- No unresolved architecture ambiguity blocking protocol definition.
- Current sender path and future companion-artifact path are explicitly separated.

### Stage 1.2 Plan — Protocol and Compatibility Freeze
Goal: define one versioned message contract that supports both current sender path and future companion-artifact path.

Tasks:
- Define envelope fields:
  - `version`
  - `type`
  - `binding_id`
  - `timestamp`
  - `nonce`
  - optional metadata fields
- Define message types:
  - sender->plugin activation
  - plugin->sender sync (`full`, `delta`, `clear`) conceptual contract
  - ack/error semantics for future bidirectional use
- Define compatibility matrix:
  - unknown `version`
  - unknown `type`
  - missing required fields
  - forward-compatible optional fields

Deliverables:
- Protocol v1 document with examples for valid and invalid messages.
- Compatibility rules table (`accept`, `ignore`, `warn`, `reject`).

Touch Points:
- this plan file
- protocol spec file: `docs/gnome-bridge-protocol-v1.md` (planned output)

Exit Criteria:
- Any developer can implement parser/validator from spec alone.
- Compatibility behavior is deterministic and testable.

### Stage 1.3 Plan — Security Model Freeze
Goal: define concrete local security controls before hardening implementation phases.

Tasks:
- Define secure transport location/permissions baseline:
  - target runtime path under `$XDG_RUNTIME_DIR`
  - directory and socket permission expectations
  - ownership checks and startup behavior when violated
- Define sender authentication model:
  - token generation/distribution/rotation lifecycle
  - rejection semantics for missing/invalid tokens
- Define replay/abuse protections:
  - timestamp window
  - nonce cache policy
  - rate-limit policy and overflow behavior
- Define logging policy for security failures:
  - actionable warnings
  - no sensitive token disclosure

Deliverables:
- Threat model table (threat, mitigation, residual risk).
- Security controls checklist mapped to future implementation stages.

Touch Points:
- this plan file
- optional security annex: `docs/security/gnome_bridge_threat_model.md`

Exit Criteria:
- Security controls are specific enough to translate directly into tests.
- Residual risks are explicitly documented and accepted.

### Stage 1.4 Plan — Backend Mode and UX Policy Freeze
Goal: freeze mode semantics and fallback behavior so user-facing behavior is predictable.

Tasks:
- Define mode set and persistence behavior:
  - `auto`
  - `wayland_portal`
  - `wayland_gnome_bridge`
  - `x11`
- Define `auto` precedence policy on GNOME Wayland:
  - current sender path availability
  - portal availability
  - deterministic fallback order
- Define startup/diagnostic UX contract:
  - what gets logged
  - what appears as warning vs info
  - how unsupported modes are surfaced

Deliverables:
- Mode decision table with explicit precedence rules.
- User-visible behavior matrix per session type (`wayland`, `x11`, unknown).

Touch Points:
- this plan file
- settings/prefs design notes (if mode selector is added later)

Exit Criteria:
- No ambiguity in mode selection outcomes.
- Policy is compatible with non-fatal startup guarantees.

### Phase 1 Validation Plan
Documentation/contract validation (required):
1. Architecture walkthrough review with at least one maintainer.
2. Protocol examples exercised via parser test stubs (dry-run docs validation accepted in this phase).
3. Security checklist reviewed for enforceability in code.
4. Mode precedence table reviewed against existing selector behavior.

Readiness checks for next phases:
1. Each Stage (`1.1`..`1.4`) has explicit deliverable links.
2. Open decisions reduced to only post-freeze rollout choices.
3. Implementation phases can proceed without redefining architecture/protocol/security fundamentals.

### Phase 1 Acceptance Criteria
- Architecture boundaries and sender tracks are clearly frozen and documented.
- Protocol v1 and compatibility rules are explicit, complete, and implementation-ready.
- Security controls are concrete, testable, and mapped to subsequent implementation phases.
- Backend mode policy is deterministic and user-facing behavior is documented.

### Phase 1 Implementation Results (2026-02-26)
- Stage 1.1 completed:
  - Added architecture freeze document with explicit current sender path vs future companion-artifact path:
    - [gnome_bridge_architecture.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/architecture/gnome_bridge_architecture.md)
  - Resolved future companion-artifact topology for v1 planning:
    - extension -> helper -> plugin (no direct extension-to-plugin IPC in v1 plan).
- Stage 1.2 completed:
  - Added protocol v1 specification and compatibility contract:
    - [gnome-bridge-protocol-v1.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/gnome-bridge-protocol-v1.md)
  - Defined versioning/type behavior and legacy compatibility mode guidance.
- Stage 1.3 completed:
  - Added local threat model and security controls checklist:
    - [gnome_bridge_threat_model.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/security/gnome_bridge_threat_model.md)
  - Defined token/replay/rate-limit target controls for future hardening phases.
- Stage 1.4 completed:
  - Mode policy and precedence frozen for current implementation and future explicit mode model.
  - `auto` policy frozen as portal-preferred on Wayland with bridge opt-in behavior preserved.

### Phase 1 Verification Results (2026-02-26)
1. Cross-checked mode policy against current selector behavior (`wayland` + bridge flag -> bridge backend; otherwise portal backend).
2. Cross-checked protocol/security docs against current implementation and documented required hardening deltas for Phase 2.
3. Confirmed all Stage 1 deliverable links exist and are referenced from this plan.

## Phase 2 — Plugin Bridge Hardening (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Move socket endpoint to secure runtime path + strict validation | Completed |
| 2.2 | Implement authenticated/versioned message parsing | Completed |
| 2.3 | Add replay protection, rate limiting, and bounded queues | Completed |
| 2.4 | Add health/state telemetry and actionable diagnostics | Completed |
| 2.5 | Add explicit backend mode configuration plumbing | Completed |

### Phase 2 Implementation Order
1. Stage `2.1` first (secure runtime path/perms are prerequisite for trust boundary).
2. Stage `2.2` next (strict protocol parser + auth gating).
3. Stage `2.3` next (replay/rate-limit/queue protections).
4. Stage `2.4` next (operational diagnostics and failure taxonomy).
5. Stage `2.5` last (mode/config UX wiring after backend hardening semantics are stable).

### Stage 2.1 Plan — Secure Runtime Path and Permission Validation
Goal: move bridge transport to a secure runtime location with explicit ownership and permission checks.

Tasks:
- Move default socket from `/tmp/...` to `$XDG_RUNTIME_DIR/edmc_hotkeys/bridge.sock`.
- Create runtime directory if missing and enforce restrictive permissions.
- Validate owner/perms on startup and refuse unsafe transport setup.
- Preserve non-fatal behavior: startup failure logs warning and returns unavailable/failed.

Deliverables:
- Secure path resolver utility and permission validation helpers.
- Backend startup path updated to enforce secure runtime checks.
- Clear warning diagnostics for path/permission failures.

Touch Points (expected):
- `edmc_hotkeys/backends/gnome_bridge.py`
- `edmc_hotkeys/backends/gnome_sender_sync.py`
- `tests/test_backends.py`

Exit Criteria:
- Backend never binds insecure socket path by default.
- Unsafe runtime dir/socket state is detected and logged deterministically.

### Stage 2.2 Plan — Strict Protocol Validation and Authentication
Goal: enforce protocol-v1 message handling and auth in hardened mode.

Tasks:
- Add strict JSON message parser for protocol v1 envelope.
- Validate required envelope/type-specific fields.
- Add hardened mode auth gate requiring token on accepted message types.
- Keep legacy payload acceptance behind explicit compatibility mode flag.

Deliverables:
- Parser/validator module with explicit reject reasons.
- Backend message intake path switched to strict validator in hardened mode.
- Compatibility mode behavior documented and logged when used.

Touch Points (expected):
- `edmc_hotkeys/backends/gnome_bridge.py`
- new parser module if needed under `edmc_hotkeys/backends/`
- `docs/gnome-bridge-protocol-v1.md`
- `tests/test_backends.py`

Exit Criteria:
- Invalid/unauthenticated payloads are rejected with clear reason.
- Valid v1 messages are accepted and dispatched.

### Stage 2.3 Plan — Replay Protection, Rate Limits, and Bounded Queue
Goal: prevent abuse and accidental overload while preserving deterministic behavior.

Tasks:
- Implement timestamp acceptance window checks.
- Implement nonce replay cache with TTL and max-size policy.
- Add sender/global rate-limit counters with drop-and-log behavior.
- Add bounded in-memory intake queue and explicit overload handling.

Deliverables:
- Replay guard utility (`timestamp + nonce` checks).
- Rate-limiter and queue policy implementation.
- Structured warning logs for replay/rate-limit/queue drops.

Touch Points (expected):
- `edmc_hotkeys/backends/gnome_bridge.py`
- potential helper module(s) under `edmc_hotkeys/backends/`
- `tests/test_backends.py`
- `tests/test_backend_contract.py` (if contract extensions are added)

Exit Criteria:
- Replayed or flood traffic is mitigated and observable.
- Queue growth is bounded under sustained load.

### Stage 2.4 Plan — Diagnostics and Failure Taxonomy Hardening
Goal: make hardening outcomes operationally clear in logs and runtime status.

Tasks:
- Expand runtime status snapshot with security/transport state fields.
- Standardize warnings by failure class:
  - transport path/permission
  - auth reject
  - replay reject
  - rate-limit drop
  - malformed payload
- Ensure startup summary reflects hardened mode and compatibility mode states.

Deliverables:
- Stable diagnostic key set for backend runtime status.
- Updated startup summary and warning messages with actionable context.
- Troubleshooting doc updates for hardened failure classes.

Touch Points (expected):
- `edmc_hotkeys/backends/gnome_bridge.py`
- `edmc_hotkeys/plugin.py`
- `docs/gnome-wayland-bridge-prototype.md`
- `docs/linux-user-setup.md`

Exit Criteria:
- Operators can identify root failure class from logs without code inspection.
- Runtime status output is consistent across runs and test fixtures.

### Stage 2.5 Plan — Mode Configuration and Policy Plumbing
Goal: make backend mode selection explicit/persisted while preserving current safe defaults.

Tasks:
- Add persisted mode setting support aligned with Phase 1 policy:
  - `auto`
  - `wayland_portal`
  - `wayland_gnome_bridge`
  - `x11`
- Validate mode values and apply migration-safe default.
- Keep non-bridge users unaffected by default configuration.
- Ensure bridge hardening flags/config are compatible with mode selection.

Deliverables:
- Config model updates and validation logic.
- Selector plumbing honoring explicit mode override.
- Docs for mode behavior and rollback steps.

Touch Points (expected):
- `load.py`
- `edmc_hotkeys/backends/selector.py`
- `edmc_hotkeys/settings_state.py`
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_state.py`
- `tests/test_backends.py`

Exit Criteria:
- Mode selection behavior is deterministic and persisted safely.
- Bridge mode can be enabled/disabled via config without code changes.

### Phase 2 Validation Plan
Automated validation gates (per-stage + final):
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "bridge or selector or wayland"`
2. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py`
3. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "replace_bindings or backend"`
4. `source .venv/bin/activate && python -m pytest`
5. `source .venv/bin/activate && make check`

Security-focused validation expectations:
1. Unsafe runtime path/perms fail closed (non-fatal startup).
2. Invalid token and missing token in hardened mode are rejected.
3. Replay payloads are rejected within window.
4. Rate-limit thresholds trigger deterministic drop-and-log behavior.
5. Queue bounds hold under synthetic burst tests.

### Phase 2 Acceptance Criteria
- Hardened bridge backend passes targeted security and lifecycle tests.
- Logs clearly distinguish config, security, and runtime transport failures.
- Mode/config plumbing remains deterministic and backward-safe.
- Bridge mode can be enabled/disabled without code changes.

### Phase 2 Implementation Results (2026-02-26)
- Stage 2.1 completed:
  - Secure runtime defaults implemented in [gnome_bridge.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/backends/gnome_bridge.py):
    - default socket path moved to `$XDG_RUNTIME_DIR/edmc_hotkeys/bridge.sock`
    - runtime directory ownership/permission enforcement
    - secure token file creation/validation (`0600`)
  - Sender sync now receives token-file path wiring through [gnome_sender_sync.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/backends/gnome_sender_sync.py).
- Stage 2.2 completed:
  - Hardened protocol-v1 parsing and auth gate implemented in [gnome_bridge.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/backends/gnome_bridge.py).
  - Legacy payload handling is compatibility-only behind explicit flags.
  - Sender script updated to emit v1 payloads by default in [gnome_bridge_send.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/scripts/gnome_bridge_send.py).
- Stage 2.3 completed:
  - Replay/timestamp guard, nonce cache, per-sender/global rate limits, and bounded intake queue added in [gnome_bridge.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/backends/gnome_bridge.py).
- Stage 2.4 completed:
  - Runtime status expanded with hardening counters and startup summary context in [gnome_bridge.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/backends/gnome_bridge.py).
  - Diagnostics/startup logging updated in [plugin.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/plugin.py).
  - User troubleshooting docs updated:
    - [gnome-wayland-bridge-prototype.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/gnome-wayland-bridge-prototype.md)
    - [linux-user-setup.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/linux-user-setup.md)
- Stage 2.5 completed:
  - Explicit backend mode selection/persistence plumbing implemented in:
    - [selector.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/backends/selector.py)
    - [plugin.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/plugin.py)
    - [load.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/load.py)
  - Modes supported: `auto`, `wayland_portal`, `wayland_gnome_bridge`, `x11`.
  - Added backend-mode resolution coverage in [test_load_backend_mode.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/tests/test_load_backend_mode.py).

### Phase 2 Verification Results (2026-02-26)
1. Targeted phase-2 coverage passed:
   - `source .venv/bin/activate && python -m pytest tests/test_backends.py tests/test_backend_contract.py tests/test_hotkey_plugin.py tests/test_gnome_sender_sync.py tests/test_phase6_smoke.py tests/test_phase7_side_specific.py tests/test_load_backend_mode.py`
2. Full suite passed:
   - `source .venv/bin/activate && python -m pytest` (124 passed).
3. Release gate passed:
   - `source .venv/bin/activate && make check` (lint/test/compile successful).

## Phase 3 — Companion Artifact Delivery (Extension/Helper Track, Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Implement GNOME extension hotkey capture and registration lifecycle | Completed |
| 3.2 | Implement companion-artifact event emitter compatible with hardened protocol | Completed |
| 3.3 | Add companion-artifact install/upgrade/uninstall workflows | Completed |
| 3.4 | Add compatibility matrix for GNOME Shell versions | Completed |

### Phase 3 Implementation Order
1. Stage `3.1` first (capture lifecycle contract and registration model).
2. Stage `3.2` next (hardened message emission over local socket).
3. Stage `3.3` next (packaging and install/rollback UX).
4. Stage `3.4` last (cross-version verification and support matrix freeze).

### Stage 3.1 Plan — GNOME Extension Capture and Lifecycle
Goal: implement a GNOME Shell companion extension that owns keybinding capture lifecycle without affecting plugin stability.

Tasks:
- Create extension skeleton with explicit enable/disable lifecycle handlers.
- Register keybindings via GNOME Shell APIs on enable; unregister on disable/reload.
- Implement deterministic mapping from binding ids to extension-side handlers.
- Add helper-facing bridge integration boundary in extension code (single sender interface module).
- Ensure extension failures stay isolated; plugin must continue running if extension is absent/broken.

Deliverables:
- Extension source tree with manifest metadata, version, and lifecycle hooks.
- Keybinding registration manager with explicit add/remove/update flows.
- Internal design note covering extension error isolation and restart behavior.

Touch Points (expected):
- `companion/gnome-extension/` (new)
- `docs/architecture/gnome_bridge_architecture.md`
- `docs/gnome-bridge-protocol-v1.md` (if extension-facing constraints are clarified)

Exit Criteria:
- Extension can be enabled/disabled repeatedly without orphaned keybindings.
- Keybinding registration state is deterministic across Shell reload/extension restart.
- Extension failures do not crash EDMC or plugin backend.

### Stage 3.2 Plan — Hardened Event Sender (Extension/Helper -> Plugin)
Goal: deliver authenticated protocol-v1 activation events from companion artifact to plugin bridge backend.

Tasks:
- Implement sender module that emits protocol-v1 `activate` payloads:
  - required fields (`version`, `type`, `binding_id`, `timestamp_ms`, `nonce`, `token`, `sender_id`)
- Load and cache sender token from plugin-managed token file with safe refresh behavior.
- Add sender retry/backoff policy for transient socket errors.
- Add sender-side dedupe/drop telemetry for local troubleshooting.
- Maintain deterministic binding-id mapping semantics between extension trigger and payload.

Deliverables:
- Companion sender implementation compatible with Phase 2 hardened backend.
- Sender runtime diagnostics (last send error, send/drop counters, token-load status).
- Compatibility note for fallback behavior when plugin socket/token file is unavailable.

Touch Points (expected):
- `companion/gnome-extension/` and/or `companion/helper/` (new)
- `scripts/gnome_bridge_send.py` (reference/compat behavior only)
- `docs/gnome-bridge-protocol-v1.md`

Exit Criteria:
- Valid extension-triggered activations dispatch actions in plugin backend.
- Invalid/missing token scenarios fail safely with actionable logs.
- Sender retry behavior is bounded and does not stall Shell UI thread.

### Stage 3.3 Plan — Packaging, Install, Upgrade, and Rollback UX
Goal: make companion artifact shippable and user-operable as an optional release component.

Tasks:
- Define release artifact layout for extension/helper deliverables separate from plugin zip.
- Implement install/upgrade/uninstall scripts for local user session scope.
- Add explicit version compatibility checks in install flow.
- Provide one-command local verification script for install sanity.
- Document rollback steps that restore receiver-only or portal/x11 mode safely.

Deliverables:
- Companion packaging scripts and release checklist entries.
- Install/upgrade/uninstall helper scripts with clear error messages.
- User docs for setup, verification, and rollback.

Touch Points (expected):
- `scripts/` (installer/verifier helpers)
- `docs/linux-user-setup.md`
- `docs/gnome-wayland-bridge-prototype.md`
- release notes/template docs

Exit Criteria:
- Users can install companion artifact without modifying plugin source.
- Upgrade path preserves user keybinding state or clearly migrates it.
- Uninstall fully removes companion registration and leaves plugin operational.

### Stage 3.4 Plan — Compatibility Matrix and Support Policy
Goal: define and verify supported GNOME Shell/version combinations before rollout.

Tasks:
- Validate companion artifact on target matrix:
  - GNOME Shell versions (current LTS + current stable)
  - Ubuntu releases used by EDMC Linux users
- Capture behavior diffs for API/permission changes by Shell version.
- Classify environments as supported/experimental/unsupported.
- Document known limitations and escalation guidance for unsupported sessions.

Deliverables:
- Compatibility matrix document with pass/fail notes and known issues.
- Version-gated support policy section in user docs.
- Phase-5 rollout input: minimum required versions and blockers.

Touch Points (expected):
- `docs/linux-user-setup.md`
- `docs/gnome-wayland-bridge-prototype.md`
- `docs/plans/GNOME_WAYLAND_BRIDGE_HARDENING_IMPLEMENTATION_PLAN.md`

Exit Criteria:
- Support matrix is complete and linked from setup docs.
- Known limitations are explicit and actionable for users.
- No unresolved critical compatibility blockers remain for alpha rollout.

### Phase 3 Validation Plan
Automated and manual validation gates:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "bridge or selector or wayland"`
2. `source .venv/bin/activate && python -m pytest tests/test_phase6_smoke.py -k "backend or dispatch"`
3. Companion artifact local smoke:
   - install companion artifact in user session
   - trigger registered shortcut
   - verify plugin action dispatch in EDMC log
4. Failure-mode validation:
   - invalid token file
   - missing socket
   - extension disabled/reloaded
5. Uninstall/rollback validation:
   - remove companion artifact
   - verify plugin remains non-fatal and backend-mode fallback works.

Evidence capture requirements:
1. Log excerpts for successful activation dispatch.
2. Log excerpts for each failure mode with expected rejection class.
3. Shell/version identifiers for each compatibility test row.

### Phase 3 Acceptance Criteria
- Companion artifact can be installed, upgraded, and removed independently of plugin package.
- End-to-end shortcut -> companion sender -> hardened plugin bridge -> action dispatch path is implemented, with manual runtime smoke defined for Phase 4 QA.
- Failure modes are isolated and non-fatal to EDMC/plugin startup.
- Compatibility/support matrix is complete and referenced in user docs.

### Phase 3 Implementation Results (2026-02-26)
- Stage 3.1 completed:
  - Added GNOME extension skeleton with lifecycle + accelerator registration manager:
    - [metadata.json](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/companion/gnome-extension/edmc-hotkeys@edcd/metadata.json)
    - [extension.js](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/companion/gnome-extension/edmc-hotkeys@edcd/extension.js)
    - [helper_bridge.js](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/companion/gnome-extension/edmc-hotkeys@edcd/helper_bridge.js)
  - Added lifecycle architecture note:
    - [gnome_companion_extension_lifecycle.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/architecture/gnome_companion_extension_lifecycle.md)
- Stage 3.2 completed:
  - Added hardened companion helper sender with token loading, protocol-v1 payloads, retry/backoff, and telemetry:
    - [gnome_bridge_companion_send.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/companion/helper/gnome_bridge_companion_send.py)
  - Added plugin-bindings export utility for extension config sync:
    - [companion_bindings_export.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/companion/helper/companion_bindings_export.py)
    - [export_companion_bindings.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/scripts/export_companion_bindings.py)
  - Added helper documentation:
    - [companion/helper/README.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/companion/helper/README.md)
- Stage 3.3 completed:
  - Added companion artifact lifecycle scripts:
    - [install_gnome_bridge_companion.sh](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/scripts/install_gnome_bridge_companion.sh)
    - [uninstall_gnome_bridge_companion.sh](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/scripts/uninstall_gnome_bridge_companion.sh)
    - [verify_gnome_bridge_companion.sh](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/scripts/verify_gnome_bridge_companion.sh)
    - [package_gnome_bridge_companion.sh](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/scripts/package_gnome_bridge_companion.sh)
  - Added `Makefile` targets for install/uninstall/verify/package companion workflows.
- Stage 3.4 completed:
  - Added compatibility/support matrix document:
    - [gnome-companion-compatibility-matrix.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/gnome-companion-compatibility-matrix.md)
  - Updated user docs with companion install/export/rollback references:
    - [gnome-wayland-bridge-prototype.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/gnome-wayland-bridge-prototype.md)
    - [linux-user-setup.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/linux-user-setup.md)

### Phase 3 Verification Results (2026-02-26)
1. New companion unit/layout tests passed:
   - `source .venv/bin/activate && python -m pytest tests/test_companion_helper_send.py tests/test_companion_bindings_export.py tests/test_companion_artifact_layout.py`
2. Phase-3 targeted gates passed:
   - `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "bridge or selector or wayland"`
   - `source .venv/bin/activate && python -m pytest tests/test_phase6_smoke.py -k "backend or dispatch"`
3. Full project validation passed:
   - `source .venv/bin/activate && python -m pytest` (136 passed)
   - `source .venv/bin/activate && make check`
4. Local environment baseline captured for compatibility matrix:
   - GNOME Shell `46.0`
   - Ubuntu `24.04.3 LTS`
5. Manual validation closure:
   - Full extension-runtime accelerator smoke and restart/recovery scenarios were executed and captured in the Phase 4 manual matrix.

## Phase 4 — Test and Verification Hardening (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Expand unit tests for auth, replay, malformed payload, and rate limits | Completed |
| 4.2 | Add integration tests for bridge lifecycle and reconnect behavior | Completed |
| 4.3 | Add manual QA matrix for Wayland GNOME scenarios | Completed |
| 4.4 | Add release checks for artifact completeness and docs accuracy | Completed |

### Phase 4 Implementation Order
1. Stage `4.1` first (unit-level deterministic guards).
2. Stage `4.2` next (integration lifecycle and reconnect coverage).
3. Stage `4.3` next (manual GNOME Wayland runtime matrix).
4. Stage `4.4` last (release artifact/doc completeness gates).

### Stage 4.1 Plan — Security and Parser Unit Coverage Expansion
Goal: harden deterministic unit coverage around every security guard and protocol reject path.

Tasks:
- Add explicit unit tests for:
  - auth reject (`missing/invalid token`)
  - replay reject (`duplicate nonce`, `stale timestamp`)
  - malformed payload reject (`invalid JSON`, missing required fields, unsupported version/type)
  - rate-limit drop (`per-sender`, `global`)
  - queue bound/drop behavior under burst input
- Add helper/export edge-case tests:
  - token file missing/invalid
  - retry backoff boundaries
  - binding export skip semantics (disabled/unsupported hotkeys)
- Ensure runtime-status counters are asserted per reject/drop class.

Deliverables:
- Expanded unit test modules under `tests/` with deterministic fixtures.
- Counter/assertion coverage for hardening telemetry keys.
- Updated comments/docstrings for non-obvious guard behavior.

Touch Points (expected):
- `tests/test_backends.py`
- `tests/test_companion_helper_send.py`
- `tests/test_companion_bindings_export.py`
- optional new targeted test files under `tests/`

Exit Criteria:
- Each hardening reject/drop class has at least one positive and one negative-path assertion.
- Unit tests are stable (no timing flake) and pass consistently in local/CI runs.

### Stage 4.2 Plan — Integration Lifecycle and Reconnect Verification
Goal: validate multi-component behavior (backend + sender helper + artifact scripts) across startup/shutdown/reconnect edges.

Tasks:
- Add integration tests (or high-fidelity smoke harnesses) for:
  - backend start/stop with companion sender enabled
  - stale/missing socket path recovery
  - sender retry success after transient send failure
  - bridge backend restart while extension/helper path remains installed
- Validate script workflow integration:
  - install -> verify -> export bindings -> uninstall
- Confirm non-fatal invariants under integration failures:
  - plugin remains operational
  - clear warning reason logged

Deliverables:
- Integration tests or scripted smoke checks captured in repo.
- Deterministic expected log pattern assertions for lifecycle failures.
- Evidence snippets for reconnect/stale-socket recovery behavior.

Touch Points (expected):
- `tests/test_phase6_smoke.py` (or new integration test module)
- `scripts/install_gnome_bridge_companion.sh`
- `scripts/verify_gnome_bridge_companion.sh`
- `scripts/uninstall_gnome_bridge_companion.sh`
- `scripts/export_companion_bindings.py`

Exit Criteria:
- Lifecycle and reconnect scenarios are reproducible and test-gated.
- No integration failure causes plugin fatal startup behavior.

### Stage 4.3 Plan — Manual GNOME Wayland QA Matrix Execution
Goal: execute and capture real-session QA evidence for companion artifact behavior across core user scenarios.

Tasks:
- Execute manual QA scenarios on GNOME Wayland sessions:
  - extension enabled with valid token path
  - extension enabled with invalid/missing token
  - extension disabled while bridge backend active
  - stale runtime directory/socket before startup
  - backend mode changes across restart (`auto`, `wayland_gnome_bridge`, `wayland_portal`)
  - rollback (`uninstall companion`, fallback backend selection)
- Capture for each row:
  - environment (`Ubuntu`, `GNOME Shell`, session type)
  - expected vs observed behavior
  - key log excerpts and timestamps
  - pass/fail and defect IDs

Deliverables:
- Completed QA matrix with evidence links.
- Issue list with severity classification and reproduction notes.
- Updated compatibility matrix statuses from `Partial/Planned` as evidence permits.

Touch Points (expected):
- `docs/gnome-companion-compatibility-matrix.md`
- `docs/linux-user-setup.md`
- `docs/plans/GNOME_WAYLAND_BRIDGE_HARDENING_IMPLEMENTATION_PLAN.md`

Exit Criteria:
- Core GNOME Wayland scenarios have explicit pass/fail evidence.
- Any failures have tracked issues with rollback guidance.

### Stage 4.4 Plan — Release Gate and Documentation Completeness Checks
Goal: ensure artifact packaging, install UX, and operational docs are release-ready and internally consistent.

Tasks:
- Add/verify release checks for:
  - companion package generation
  - install/verify/uninstall scripts present and executable
  - required docs linked and current
- Validate Make targets for companion workflows.
- Confirm rollback instructions are accurate and tested.
- Add release checklist entries for companion artifact track.

Deliverables:
- Release-gate checklist section for companion track.
- Verified script/target matrix and doc cross-links.
- Final Phase 4 readiness summary for Phase 5 rollout.

Touch Points (expected):
- `Makefile`
- `scripts/package_gnome_bridge_companion.sh`
- `docs/gnome-wayland-bridge-prototype.md`
- `docs/linux-user-setup.md`
- this plan file

Exit Criteria:
- Companion artifact and plugin artifact are both build/verify capable.
- Docs provide complete install/troubleshoot/rollback coverage.
- No high-severity release-blocking checklist gaps remain.

### Phase 4 Validation Plan
Automated gates:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "bridge or selector or wayland"`
2. `source .venv/bin/activate && python -m pytest tests/test_companion_helper_send.py tests/test_companion_bindings_export.py tests/test_companion_artifact_layout.py`
3. `source .venv/bin/activate && python -m pytest tests/test_phase6_smoke.py -k "backend or dispatch"`
4. `source .venv/bin/activate && python -m pytest`
5. `source .venv/bin/activate && make check`

Manual gates:
1. Execute Stage 4.3 QA matrix rows on at least one supported GNOME Wayland environment.
2. Capture EDMC log evidence for success/failure/recovery scenarios.
3. Verify install/uninstall rollback leaves plugin operational.

Evidence requirements:
1. Test command outputs (pass/fail counts).
2. QA matrix with environment metadata and timestamps.
3. Log excerpts for each failure class and recovery case.

### Phase 4 Acceptance Criteria
- Automated security/lifecycle/companion tests pass with no regressions.
- Manual QA matrix is completed with traceable evidence and issue linkage.
- Release artifact/doc checks are complete and no high-severity blockers remain.

### Phase 4 Implementation Results (2026-02-27)
- Stage 4.1 completed:
  - Added missing deterministic hardening unit tests in [test_backends.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/tests/test_backends.py):
    - missing-token auth reject
    - stale timestamp replay reject
    - global rate-limit drop
    - malformed JSON reject counter
    - backend restart lifecycle dispatch/reset behavior
- Stage 4.2 completed:
  - Added script-level integration tests in [test_companion_scripts_integration.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/tests/test_companion_scripts_integration.py):
    - install -> verify -> uninstall workflow in isolated HOME
    - export script end-to-end config generation
  - Fixed integration defect discovered during testing:
    - [export_companion_bindings.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/scripts/export_companion_bindings.py) now bootstraps repo root into `sys.path` for standalone execution.
    - [install_gnome_bridge_companion.sh](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/scripts/install_gnome_bridge_companion.sh) now falls back to sample config when export fails.
- Stage 4.3 completed:
  - Added and completed QA matrix with scripted-manual + interactive evidence:
    - [GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/qa/GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md)
  - Scripted rows (install/verify/export/uninstall and helper failure modes) passed.
  - Interactive rows passed:
    - extension disable while backend active
    - valid keypress activation dispatch
    - backend mode switch across restart (`auto`, `wayland_gnome_bridge`, `wayland_portal`)
    - stale runtime dir/socket recovery in live EDMC session
- Stage 4.4 completed:
  - Added release completeness check script:
    - [check_companion_release.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/scripts/check_companion_release.py)
  - Added automated check coverage:
    - [test_companion_release_check.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/tests/test_companion_release_check.py)
  - Wired release check into [Makefile](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/Makefile) (`companion-release-check`, included in `make check`).
  - Updated companion docs to link QA/matrix artifacts:
    - [gnome-wayland-bridge-prototype.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/gnome-wayland-bridge-prototype.md)
    - [linux-user-setup.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/linux-user-setup.md)
    - [gnome-companion-compatibility-matrix.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/gnome-companion-compatibility-matrix.md)

### Phase 4 Verification Results (2026-02-27)
1. Stage 4.1 targeted unit tests passed:
   - `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "gnome_bridge_backend_rejects_missing_token or gnome_bridge_backend_rejects_stale_timestamp or gnome_bridge_backend_rate_limits_globally_across_senders or gnome_bridge_backend_invalid_json_counts_as_malformed or gnome_bridge_backend_restart_resets_runtime_and_dispatches"`
2. Stage 4.2/4.4 integration and release-check tests passed:
   - `source .venv/bin/activate && python -m pytest tests/test_companion_scripts_integration.py tests/test_companion_release_check.py`
3. Stage 4.3 scripted QA evidence executed in isolated HOME:
   - `install_rc=0`
   - `verify_rc=0`
   - `export_rc=0`
   - `uninstall_rc=0`
   - helper failure-mode checks: missing token file `rc=2`, missing socket `rc=1`
4. Stage 4.3 interactive QA evidence executed in live GNOME Wayland session:
   - extension active path dispatch observed (`Hotkey pressed ... source=backend:linux-wayland-gnome-bridge`)
   - extension disable path verified (no new `Hotkey pressed` lines in bounded post-disable slice)
   - restart mode matrix verified:
     - `auto` selected/started `linux-wayland-gnome-bridge`
     - `wayland_gnome_bridge` selected/started `linux-wayland-gnome-bridge`
     - `wayland_portal` selected `linux-wayland-portal` and failed non-fatally with explicit `GlobalShortcuts` warning
   - stale runtime/socket injection recovered on restart with hardened permissions restored (`0700` dir, `0600` token)
5. Full regression and release gate passed:
   - `source .venv/bin/activate && python -m pytest`
   - `source .venv/bin/activate && make check`
6. Phase 4 completion:
   - `QA-4.3-01` through `QA-4.3-10` are all marked `Pass` in the Phase 4 QA matrix.

## Phase 5 — Rollout and Stabilization (Status: In Progress)
| Stage | Description | Status |
| --- | --- | --- |
| 5.1 | Alpha rollout behind explicit opt-in mode | Completed |
| 5.2 | Beta rollout with broader documentation and telemetry review | Deferred |
| 5.3 | General availability decision and default-policy confirmation | Completed |

### Phase 5 Implementation Order
1. Stage `5.1` first (alpha opt-in and controlled signal gathering).
2. Stage `5.2` next (beta expansion, defect burn-down, and doc hardening).
3. Stage `5.3` last (GA decision, default-policy confirmation, and support handoff).

### Stage 5.1 Plan — Alpha Rollout Behind Explicit Opt-In
Goal: run a controlled alpha on GNOME Wayland with bridge mode explicitly enabled, while preserving safe fallback behavior.

Tasks:
- Keep rollout strictly opt-in:
  - `EDMC_HOTKEYS_BACKEND_MODE=wayland_gnome_bridge`
  - `EDMC_HOTKEYS_GNOME_BRIDGE=1`
- Define alpha entry criteria:
  - companion artifact install/verify scripts succeed
  - Phase 4 QA matrix remains green
  - no open critical bridge regressions in main branch
- Capture alpha operational evidence from real users:
  - startup selection/status lines
  - dispatch success/failure classes
  - receiver-only/no-events warnings
  - startup non-fatal fallback behavior
- Define issue triage classes:
  - startup/fatality regressions
  - dispatch misses/duplicates
  - environment-specific extension/runtime incompatibility
  - documentation/install UX defects

Deliverables:
- Alpha rollout checklist and issue triage template.
- Curated alpha evidence log set (startup/dispatch/failure/recovery examples).
- Updated known-issues section for alpha scope.

Touch Points (expected):
- `docs/linux-user-setup.md`
- `docs/gnome-companion-compatibility-matrix.md`
- `RELEASE_NOTES.md`
- this plan file

Exit Criteria:
- Alpha users can complete install/enable/dispatch/rollback using docs alone.
- No unresolved high-severity regressions affecting startup safety or dispatch correctness.
- Alpha evidence is sufficient to prioritize beta hardening work.

### Stage 5.2 Plan — Beta Rollout and Stabilization
Goal: broaden validation coverage and stabilize behavior/documentation across additional GNOME/Ubuntu targets.

Tasks:
- Expand tested environments in compatibility matrix (additional GNOME versions/Ubuntu rows).
- Burn down alpha-found defects by severity with explicit fix verification evidence.
- Freeze protocol/transport behavior for beta:
  - only bug/security fixes
  - no contract-shape churn without documented migration impact
- Tighten operational docs:
  - install/update/rollback paths
  - troubleshooting by log signature
  - explicit mode selection guidance (`auto` vs bridge vs portal)
- Run full regression gates on each beta candidate build.

Deliverables:
- Updated compatibility matrix with beta-tested rows and statuses.
- Defect burn-down summary with fixed/known-deferred items.
- Beta release notes and troubleshooting updates.

Touch Points (expected):
- `docs/gnome-companion-compatibility-matrix.md`
- `docs/linux-user-setup.md`
- `docs/qa/GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md` (reference evidence)
- `RELEASE_NOTES.md`
- this plan file

Exit Criteria:
- Beta defect trend is acceptable (no unresolved high-severity startup/dispatch defects in supported rows).
- Documentation is internally consistent and tested against real install/rollback workflows.
- Compatibility matrix contains at least one additional validated Wayland row beyond initial baseline.

### Stage 5.3 Plan — GA Decision and Default-Policy Confirmation
Goal: make a deliberate GA decision and finalize long-term backend mode/default guidance.

Tasks:
- Evaluate GA readiness using explicit inputs:
  - beta defect profile and severity distribution
  - compatibility matrix coverage and confidence level
  - operational support burden and troubleshooting clarity
- Decide and document `auto` mode policy for GNOME Wayland:
  - retain current precedence, or
  - adjust precedence with migration notes and rollback guidance
- Finalize support policy:
  - supported environments
  - known limitations
  - escalation path for unsupported shells/compositor variants
- Publish GA-ready operator/user docs and release notes.

Deliverables:
- GA decision record with rationale and risk assessment.
- Finalized backend mode/default policy documentation.
- Stable support guidance and release communication package.

Touch Points (expected):
- `docs/gnome-companion-compatibility-matrix.md`
- `docs/linux-user-setup.md`
- `RELEASE_NOTES.md`
- this plan file

Exit Criteria:
- GA sign-off is explicit and documented.
- Default-policy behavior is deterministic, documented, and rollback-safe.
- Support documentation covers install, operation, troubleshooting, and fallback paths.

### Phase 5 Validation Plan
Automated gates (per beta/GA candidate):
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "bridge or wayland or selector"`
2. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py`
3. `source .venv/bin/activate && python -m pytest`
4. `source .venv/bin/activate && make test`
5. `source .venv/bin/activate && make check`

Manual/operational gates:
1. Re-run critical interactive QA scenarios from Phase 4 matrix on each candidate environment row.
2. Verify install/update/rollback commands match observed runtime behavior.
3. Verify log-driven troubleshooting steps resolve at least one representative failure from each major class (startup, dispatch, sender sync, extension/runtime state).
4. Confirm fallback behavior remains non-fatal when bridge path is unavailable.

Evidence requirements:
1. Candidate-specific automated test outputs.
2. Updated compatibility matrix statuses and notes.
3. Release-note entries describing fixed issues and known limitations.
4. Issue tracker snapshot (open high-severity defects must be zero for GA).

### Phase 5 Acceptance Criteria
- Rollout progression (alpha -> beta -> GA decision) is documented with evidence-backed gates.
- Defect rate is acceptable for supported environments and no unresolved high-severity startup/dispatch regressions remain.
- Compatibility matrix and operational docs are current, internally consistent, and tested against real workflows.
- GA/default-policy decision is explicit, documented, and includes rollback guidance.

### Phase 5 Implementation Results (2026-02-27)
- Stage 5.1 completed:
  - Added alpha rollout checklist:
    - [GNOME_WAYLAND_BRIDGE_ALPHA_ROLLOUT_CHECKLIST.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/release/GNOME_WAYLAND_BRIDGE_ALPHA_ROLLOUT_CHECKLIST.md)
  - Added rollout issue triage template:
    - [GNOME_WAYLAND_BRIDGE_ISSUE_TRIAGE_TEMPLATE.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/release/GNOME_WAYLAND_BRIDGE_ISSUE_TRIAGE_TEMPLATE.md)
  - Updated compatibility guidance to reference completed Phase 4 evidence:
    - [gnome-companion-compatibility-matrix.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/gnome-companion-compatibility-matrix.md)
- Stage 5.2 deferred:
  - Beta expansion/trend tracking criteria are documented.
  - Rollout/ops docs were updated to expose Phase 5 artifacts:
    - [linux-user-setup.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/linux-user-setup.md)
    - [RELEASE_NOTES.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/RELEASE_NOTES.md)
  - Additional validated GNOME Wayland environment rows remain to be executed.
  - Execution is deferred pending access to at least one additional GNOME Wayland environment.
- Stage 5.3 completed:
  - Added GA/default-policy decision record:
    - [GNOME_WAYLAND_BRIDGE_GA_DECISION_RECORD.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/release/GNOME_WAYLAND_BRIDGE_GA_DECISION_RECORD.md)
  - Decision captured: defer GA promotion, keep bridge sender path opt-in, keep current `auto` behavior.

### Phase 5 Verification Results (2026-02-27)
1. Targeted rollout/release tests passed:
   - `source .venv/bin/activate && python -m pytest tests/test_companion_release_check.py tests/test_companion_scripts_integration.py` (`3 passed`)
2. Full project release gate passed:
   - `source .venv/bin/activate && make check` (`144 passed`, companion release check `OK`)
3. Documentation deliverables for Stage 5.1 and Stage 5.3 are present and linked from this plan.
4. Phase 4 QA evidence remains fully passing in:
   - [GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/qa/GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md)
5. Compatibility matrix reflects validated baseline rollout input for alpha:
   - [gnome-companion-compatibility-matrix.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/gnome-companion-compatibility-matrix.md)

### Phase 5 Remaining Work
- Complete Stage 5.2 by validating at least one additional GNOME Wayland environment row and updating compatibility statuses.
  - Current blocker: no access to additional GNOME Wayland environment hosts/images.
  - Resume trigger: obtain one target row environment (`22.04/42.x Wayland` or `24.10+/47.x Wayland`) and run the Phase 5.2 row-validation script.
- Re-assess GA readiness after beta defect trend and expanded matrix evidence are collected.

## Test Gates
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "bridge or wayland or selector"`
2. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py`
3. `source .venv/bin/activate && python -m pytest`
4. `source .venv/bin/activate && make test`
5. `source .venv/bin/activate && make check`

## Rollback Plan
- Disable bridge mode via backend mode setting or env flag.
- Fall back to existing backend selection (`wayland_portal` or `x11`).
- Keep sender-path rollback documented and reversible.

## Open Decisions
- Rollout timing for promoting future companion-artifact track beyond experimental/opt-in.
- Long-term GA decision for `auto` behavior after Phase 2 hardening and user beta feedback.

## Current Gap and Execution Plan (2026-02-26)
Pre-Phase-6 observed behavior:
- Plugin-side bridge receiver was functional (`linux-wayland-gnome-bridge` starts and dispatches when socket payloads are sent).
- Global keypresses did not fire actions unless users manually wired GNOME custom shortcuts to `scripts/gnome_bridge_send.py`.
- Therefore, the blocking gap was sender automation + binding synchronization, not backend event dispatch.

Current state after Phase 6:
- Sender automation and binding synchronization are implemented via GNOME custom-keybinding auto-sync.
- Remaining gap has shifted to optional extension/helper companion-artifact delivery and rollout stabilization.

### Execution Scope for Gap Closure
- Deliver an optional GNOME sender path that captures shortcuts and emits binding activations automatically.
- Eliminate manual one-off GNOME shortcut setup for each binding.
- Keep all bridge behavior opt-in and non-fatal.

## Phase 6 — Sender Automation and Binding Sync (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 6.1 | Define plugin-to-sender binding sync contract | Completed |
| 6.2 | Implement sender-side keybinding manager | Completed |
| 6.3 | Implement plugin-side sync endpoint/state export | Completed |
| 6.4 | Add diagnostics for sender-connected vs receiver-only mode | Completed |
| 6.5 | Add packaging/install UX for sender-first setup | Completed |

### Phase 6 Implementation Order
1. Stage 6.1 first (contract freeze).
2. Stages 6.2 and 6.3 in parallel once 6.1 is frozen.
3. Stage 6.4 after 6.2/6.3 plumbing is stable.
4. Stage 6.5 last, after behavior and logs are stable.

### Stage 6.1 Plan — Contract Freeze
Goal: define the exact, versioned contract between plugin and sender path before implementation changes.

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
- [GNOME_WAYLAND_BRIDGE_HARDENING_IMPLEMENTATION_PLAN.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/plans/GNOME_WAYLAND_BRIDGE_HARDENING_IMPLEMENTATION_PLAN.md)
- optional sender protocol spec file (if created): `docs/gnome-bridge-protocol-v1.md`

Exit Criteria:
- Contract is explicit enough to implement without interpretation gaps.
- Open decision for direct vs helper path is resolved for `v1`.

### Stage 6.2 Plan — Sender Keybinding Manager
Goal: sender path dynamically owns GNOME keybinding registration using synced bindings.

Deliverables:
- Sender-path runtime that:
  - registers enabled accelerators from latest sync snapshot
  - unregisters removed/disabled accelerators
  - preserves deterministic mapping `accelerator -> binding_id`
  - survives extension reload and shell restart without duplicate registrations
- Activation emitter that sends only valid, known `binding_id` values to plugin bridge socket.

Implementation Notes:
- Keep sender-path failures isolated; no crash propagation to EDMC.
- Enforce minimal retry/backoff for socket send failures.

Touch Points:
- sender path implementation path (to be finalized in 6.1)
- bridge sender compatibility with [gnome_bridge_send.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/scripts/gnome_bridge_send.py)

Exit Criteria:
- No manual GNOME custom-keybinding shell commands required for end users.
- Sender path restores key registrations after restart with same binding IDs.

### Stage 6.3 Plan — Plugin Sync Export
Goal: plugin publishes active binding state so sender path can register shortcuts automatically.

Deliverables:
- Plugin-side binding sync publisher with:
  - full-state export on startup
  - delta export on settings save
  - clear/unregister signal on shutdown/backend stop
- Compatibility guard:
  - if sender path is absent/unreachable, plugin stays fully operational and logs warning only.

Touch Points (expected):
- [load.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/load.py)
- [plugin.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/plugin.py)
- [gnome_bridge.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/backends/gnome_bridge.py)
- tests for sync lifecycle in `tests/`

Exit Criteria:
- Binding edits in prefs propagate to sender path without manual intervention.
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
- [plugin.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/plugin.py)
- [gnome_bridge.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/backends/gnome_bridge.py)
- docs troubleshooting section

Exit Criteria:
- Operators can distinguish transport failure vs sync failure vs no-sender condition from logs alone.

### Stage 6.5 Plan — Packaging, Install UX, and Rollback
Goal: ship sender path as a repeatable, supportable user workflow.

Deliverables:
- Bridge sender path release workflow and plugin compatibility mapping.
- Install docs with exact commands for:
  - install/update
  - enable/start
  - verify (`Ctrl+M` test and expected log line)
- Rollback docs with exact commands for:
  - disable/uninstall sender path
  - switch backend mode
  - verify fallback behavior

Touch Points (expected):
- `docs/linux-user-setup.md`
- `RELEASE_NOTES.md`
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
4. Modify binding in prefs and verify sender registration updates without manual shell commands.
5. Disable sender auto-sync and verify receiver-only warning appears while EDMC remains stable.

### Phase 6 Acceptance Criteria
- User can enable sender path and use bindings without manual GNOME custom keybinding commands.
- Binding changes in EDMCHotkeys automatically update sender-path key registrations.
- Logs clearly distinguish backend unavailable, receiver-only, sync failure, and successful dispatch.
- Full automated test gates pass.

### Phase 6 Scope Clarification
- Phase 6 completion in this document refers to the implemented GNOME custom-keybinding sender path.
- Separate extension/helper companion-artifact delivery remains planned under Phase 3.

### Phase 6 Implementation Results (2026-02-26)
- Added GNOME sender auto-sync module:
  - [gnome_sender_sync.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/backends/gnome_sender_sync.py)
  - Converts EDMC hotkeys to GNOME accelerators.
  - Manages GNOME custom-keybinding entries for active bridge bindings.
  - Preserves non-EDMC custom keybindings while replacing managed entries.
- Integrated auto-sync + diagnostics into bridge backend:
  - [gnome_bridge.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/backends/gnome_bridge.py)
  - Sync on startup/register/unregister and batch-complete.
  - Batch APIs to avoid repeated full sync during `replace_bindings`.
  - Runtime status snapshot for plugin logging.
  - Receiver-only warning when no events are observed after startup grace window.
- Integrated plugin reconciliation and status reporting:
  - [plugin.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/edmc_hotkeys/plugin.py)
  - Batched backend updates during `replace_bindings`.
  - Idempotent disabled-binding unregister path to avoid false failure warnings.
  - Startup backend runtime-status logging when backend exposes it.
- Added tests:
  - [test_gnome_sender_sync.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/tests/test_gnome_sender_sync.py)
  - [test_backends.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/tests/test_backends.py)
  - [test_hotkey_plugin.py](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/tests/test_hotkey_plugin.py)
- Added explicit optional backend extension interfaces for minimal-complexity contract hygiene:
  - batch binding update interface
  - runtime status interface
  - typed adapter helpers used by plugin core instead of raw duck-typing.

### Phase 6 Verification Results (2026-02-26)
1. `source .venv/bin/activate && python -m pytest tests/test_gnome_sender_sync.py tests/test_backends.py -k "gnome_bridge or sender_sync"` passed (`10 passed`).
2. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "replace_bindings"` passed (`2 passed`).
3. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py` passed (`4 passed`).
4. `source .venv/bin/activate && python -m pytest` passed (`110 passed`).
5. `source .venv/bin/activate && make test` passed.
6. `source .venv/bin/activate && make check` passed.
