# Implementation Plan

Follow persona details in AGENTS.md
Document implementation results in the Implementation Results section.
After each stage is complete change status to Completed
When all stages are complete change the phase status to Completed
if something is not clear, ask clarifying questions

## Phase 1 — Architecture Decisions (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Finalize action registry API (fields, threading contract) | Completed |
| 1.2 | Decide backend selection strategy (Windows/X11/Wayland) | Completed |
| 1.3 | Define bindings file storage format | Completed |

## Phase 2 — Core Plugin Skeleton (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Internal action registry module in EDMCHotkeys | Completed |
| 2.2 | Hotkey plugin scaffolding + logging | Completed |
| 2.3 | Dispatch pipeline (main-thread default) | Completed |
| 2.4 | Unit tests for registry + dispatch added alongside implementation | Completed |

## Phase 3 — Backends (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Windows backend (RegisterHotKey + fallback) | Completed |
| 3.2 | X11 backend (python-xlib) | Completed |
| 3.3 | Wayland backend (XDG portal) | Completed |
| 3.4 | Unit tests for backend adapters added alongside implementation | Completed |

### Phase 3 Execution Plan (This Iteration)
- Touch points:
  - Add backend adapter modules under `edmc_hotkeys/backends/` for Windows/X11/Wayland plus backend selection.
  - Implement platform/session detection matching the normative strategy (`XDG_SESSION_TYPE`, `WAYLAND_DISPLAY`, `DISPLAY`).
  - Wire backend lifecycle into plugin startup/shutdown with safe no-op behavior when backend is unavailable.
  - Add backend unit tests for selection and adapter behavior.
- Expected unchanged behavior:
  - No settings UI, binding editor, or persisted binding management changes in this phase.
  - No feature-level action behavior changes beyond backend adapter lifecycle and registration hooks.
- Tests to run:
  - `source .venv/bin/activate && python -m pytest`
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`

## Phase 4 — Settings UI (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Binding table UI (hotkey / plugin / action) | Completed |
| 4.2 | Validation + conflict feedback | Completed |
| 4.3 | Persist & reload bindings | Completed |
| 4.4 | Unit tests for UI state + bindings file serialization added alongside implementation | Completed |

### Phase 4 Execution Plan (This Iteration)
- Touch points:
  - Add bindings file model/store modules (`edmc_hotkeys/bindings.py`, `edmc_hotkeys/storage.py`) for v1 schema load/save/defaults.
  - Add UI state module (`edmc_hotkeys/settings_state.py`) for binding rows, plugin/action options, and validation/conflict reporting.
  - Add EDMC settings hooks in `load.py` (`plugin_prefs`, `prefs_changed`) and a minimal table-like settings frame builder in `edmc_hotkeys/settings_ui.py`.
  - Wire load/start flow to read `bindings.json`, register bindings into backend, and persist on settings changes.
  - Add tests for bindings serialization, validation/conflict detection, and plugin persistence wiring.
- Expected unchanged behavior:
  - No backend-selection contract changes from Phase 3.
  - No changes to action-dispatch semantics from Phase 2.
- Tests to run:
  - `source .venv/bin/activate && python -m pytest`
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`

## Phase 5 — Packaging + Docs (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 5.1 | Dependency bundling plan (packaged EDMC) | Completed |
| 5.2 | User setup docs (Wayland portal, X11) | Completed |

### Phase 5 Execution Plan (This Iteration)
- Touch points:
  - Add dependency bundling guidance for packaged EDMC runtime in a dedicated doc.
  - Add Linux user setup docs for X11 and Wayland sessions, including verification/troubleshooting.
  - Cross-link packaging/setup notes from architecture requirements.
- Expected unchanged behavior:
  - No runtime behavior changes in plugin startup, backend selection, or settings UI.
  - No action registry or dispatch contract changes.
- Tests to run:
  - `source .venv/bin/activate && python -m pytest`
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`

## Phase 6 — Tests + Verification (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 6.1 | Unit tests for registry + dispatch | Completed |
| 6.2 | Backend smoke tests | Completed |
| 6.3 | Manual QA checklist | Completed |

### Phase 6 Execution Plan (This Iteration)
- Touch points:
  - Add focused smoke coverage for dispatch + backend lifecycle behavior that is currently only partially covered by unit tests.
  - Add a release-oriented manual QA checklist document for EDMC runtime verification.
  - Update phase/stage statuses and implementation results after verification.
- Expected unchanged behavior:
  - No feature changes to action dispatch, backend selection, or settings persistence.
  - No runtime API contract changes for `load.py` hooks.
- Tests to run:
  - `source .venv/bin/activate && python -m pytest`
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`
  - `make check` (if available)
  - `make test` (if available)

## Phase 7 — Side-Specific Modifiers (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 7.1 | Define canonical token format + binding schema update for side-specific modifiers (`ctrl_l`, `ctrl_r`, `alt_l`, `alt_r`, `shift_l`, `shift_r`, `win_l`, `win_r`) | Completed |
| 7.2 | Update settings capture/editor to emit side-aware tokens from key events and allow manual editing of canonical side-specific forms | Completed |
| 7.3 | Extend parser + binding model to accept canonical side-specific tokens only and emit one canonical representation to runtime | Completed |
| 7.4 | Implement capability matrix and selection logic so side-specific bindings route to side-aware backend paths only | Completed |
| 7.5 | Implement side-aware backend paths (Windows low-level hook + X11 side-aware matcher), with explicit unsupported handling on Wayland | Completed |
| 7.6 | Add tests + docs for schema, parser, UI capture, backend matching, and unsupported warnings; verify end-to-end in EDMC | Completed |

### Phase 7 Execution Plan (This Iteration)
- Current baseline from implemented work:
  - Settings hotkey field already captures key combinations from focused entry (`edmc_hotkeys/settings_ui.py`) and replaces the current value on keypress.
  - Current capture/parser path normalizes to non-side-specific modifier labels (`Ctrl`/`Alt`/`Shift`/`Super`) and does not preserve left/right modifier side.
  - `bindings.json` schema is still v1 string-based hotkeys (`BindingRecord.hotkey: str`) with free-form payload JSON in prefs.
  - Action callbacks can receive `hotkey` when declared, and external plugins can query assigned bindings with `list_bindings(plugin_name)` (`load.py`, `edmc_hotkeys/registry.py`).
  - These completed pieces are prerequisites for Phase 7 and should be extended, not replaced.
- Stage 7.1 details (format + schema):
  - Bump bindings schema to v3 and store canonical hotkey data as structured fields instead of a single free-form hotkey string.
  - Development mode allows breaking format changes and direct rewrite of existing `bindings.json`; no migration/back-compat required.
  - Canonical hotkey model:
    - `modifiers`: ordered list from `{ctrl_l, ctrl_r, alt_l, alt_r, shift_l, shift_r, win_l, win_r}`
    - `key`: normalized key token (`a`, `f10`, `1`, `esc`, etc.)
    - `plugin`: explicit owner plugin name for each binding row.
  - Keep payload model unchanged (`payload` remains free-form JSON object).
- Stage 7.2 details (settings capture/editor):
  - Extend capture logic to resolve side-specific modifier tokens from Tk keysyms (`Control_L`, `Control_R`, `Shift_L`, `Shift_R`, `Alt_L`, `Alt_R`, `Super_L`, `Super_R`).
  - Display a pretty hotkey label in prefs/editor (for example `LCtrl+RShift+A`) while persisting canonical tokens in schema fields.
  - Keep hotkey field keyboard-driven (press-to-set behavior), with validation for malformed canonical token sets.
  - On validation failure during save, show a user-facing error dialog and do not persist changes.
- Stage 7.3 details (parser + binding model):
  - Refactor parser/model to accept canonical side-specific tokens as the only source format for runtime matching.
  - Remove compatibility obligations for pre-Phase-7 token forms in this phase.
  - Ensure runtime `Binding` instances preserve canonical modifier-side intent through registration/invocation paths.
  - Render hotkey strings exposed to callbacks/public APIs in pretty form for consistency with prefs.
- Stage 7.4 details (capability matrix + routing):
  - Add backend capability flags (for example `supports_side_specific_modifiers`) and per-binding requirement checks.
  - Route side-specific bindings only to side-aware backend paths.
  - If capability is missing, auto-disable only affected bindings, continue loading compatible bindings, and present explicit diagnostics.
- Stage 7.5 details (backend implementation tracks):
  - Windows:
    - keep `RegisterHotKey` for bindings that do not require left/right modifier differentiation.
    - add a low-level keyboard hook path for side-specific modifier matching (always on).
  - X11:
    - extend matching beyond aggregate modifier masks to side-aware key state/keycode handling.
  - Wayland:
    - auto-disable side-specific bindings as unsupported unless a concrete portal/API path exists; log actionable diagnostics.
- Stage 7.6 details (tests + docs + QA):
  - Unit tests:
    - v3 schema serialization/deserialization and canonical token validation.
    - side-specific parser normalization and invalid-token rejection.
    - settings capture from left/right keysyms and canonical display output.
    - capability enforcement and unsupported-binding warnings.
  - Integration tests:
    - mixed side-specific/non-side-specific registration and invocation.
    - callback `hotkey` kwarg and `list_bindings(plugin_name)` expose canonical side-specific hotkey values.
  - Docs:
    - update `docs/requirements-architecture-notes.md` with canonical token + v3 schema spec.
    - update `docs/register-action-with-edmc-hotkeys.md` with side-specific examples and expected `hotkey` format.
- Key constraints discovered:
  - Current Windows path (`RegisterHotKey`) does not differentiate left/right modifiers.
  - Current X11 path (modifier masks only) does not differentiate left/right modifiers.
  - Wayland portal path currently has no side-specific contract in this plugin.
  - Therefore, true side-specific behavior requires low-level event hooks or backend-specific alternative APIs.
- Development-mode assumptions for this phase:
  - Existing assigned hotkeys may be changed as needed.
  - `bindings.json` schema/format may be changed if that simplifies or improves side-specific support.
  - Backward compatibility/migration is not required for this development phase.
  - Temporary rollout flags may be code-local/env-driven and removed once side-specific behavior is fully validated (none required for Windows low-level hook path).
- Acceptance criteria for Phase 7 completion:
  - Side-specific bindings can be entered in prefs and persisted.
  - Invalid canonical hotkey edits surface a blocking error dialog in prefs.
  - Side-specific matching works on implemented backend paths (Windows/X11).
  - Unsupported side-specific bindings are auto-disabled with clear diagnostics.
  - Canonical bindings (including entries with no modifiers) remain functional.
- Tests to run:
  - `source .venv/bin/activate && python -m pytest`
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`
  - Targeted backend tests for side-aware matching and unsupported-path warnings

# Implementation Results

## Phase 1 — Architecture Decisions
- Documented Action Registry API (normative), threading contract, and error handling in `docs/requirements-architecture-notes.md`.
- Documented backend selection strategy for Windows/X11/Wayland and session detection rules.
- Documented `bindings.json` storage schema and profile handling for v1 bindings.

## Phase 2 — Core Plugin Skeleton
- Added a single EDMC plugin entrypoint at `load.py` for `EDMCHotkeys`, with logger wiring and lifecycle hooks.
- Implemented internal action registry module under `edmc_hotkeys`, exposing register/list/get/invoke via the single plugin entrypoint.
- Implemented dispatch pipeline with queued main-thread marshalling by default and optional worker dispatch for actions with `thread_policy="worker"`.
- Added unit tests for registry registration rules, dispatch routing, main-thread marshalling/timeout behavior, missing/disabled action handling, callback exception handling, and hotkey plugin dispatch behavior.
- Verification:
  - `source .venv/bin/activate && python -m pip install -U pip && python -m pip install -r requirements-dev.txt` passed.
  - `source .venv/bin/activate && python -m pytest` passed (`13 passed`).
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests` passed.
  - `python3 -m pytest` still fails outside `.venv` (`No module named pytest`), expected unless global Python has dev deps installed.

## Phase 3 — Backends
- Added backend adapter package at `edmc_hotkeys/backends/` with:
  - platform adapter interface + disabled/null backend.
  - backend selection logic using `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY`, and `DISPLAY`.
  - Windows backend using `RegisterHotKey` with no-modifier fallback routing.
  - X11 backend wrapper with python-xlib client support when available.
  - Wayland backend wrapper for XDG Desktop Portal client integration.
- Wired backend lifecycle into `HotkeyPlugin` startup/shutdown and added binding register/unregister hooks for backend registration.
- Added backend unit tests for selection strategy and adapter behavior (Windows/X11/Wayland).
- Verification:
  - `source .venv/bin/activate && python -m pytest` passed (`25 passed`).
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests` passed.

## Phase 4 — Settings UI
- Added bindings schema + persistence modules:
  - `edmc_hotkeys/bindings.py` for v1 document model/defaults and JSON conversion.
  - `edmc_hotkeys/storage.py` for `bindings.json` load/create/save.
- Added settings state + validation module:
  - `edmc_hotkeys/settings_state.py` for binding table rows, action options, validation, and conflict detection.
- Added table-like settings UI:
  - `edmc_hotkeys/settings_ui.py` with editable row controls for binding id, hotkey, plugin, action, enabled state, plus vertical scrolling and validation feedback text.
- Wired EDMC prefs + persistence flow in `load.py`:
  - load/create `bindings.json` at startup.
  - apply active-profile bindings into plugin backend registration pipeline.
  - `plugin_prefs` builds settings panel from current bindings + registered actions.
  - `prefs_changed` validates, surfaces conflicts, persists to `bindings.json`, and re-applies bindings to backend.
- Extended plugin binding APIs in `edmc_hotkeys/plugin.py` with `list_bindings` and `replace_bindings` to support settings-driven reconciliation.
- Added tests:
  - `tests/test_storage.py` for bindings file serialization/load behavior.
  - `tests/test_settings_state.py` for validation/conflict logic and document conversion.
  - `tests/test_hotkey_plugin.py` coverage for binding replacement registration reconciliation.
- Verification:
  - `source .venv/bin/activate && python -m pytest` passed (`34 passed`).
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests` passed.

## Phase 5 — Packaging + Docs
- Added packaged-EDMC dependency bundling plan in `docs/packaged-edmc-dependency-bundling.md`:
  - runtime dependency matrix by platform/session.
  - vendoring workflow for optional X11 dependency (`python-xlib` / `Xlib` package).
  - release verification checklist for bundled dependencies.
- Added vendoring automation:
  - `scripts/vendor_xlib.sh` for reproducible `python-xlib` vendoring into plugin-local `Xlib/`.
  - `make vendor-xlib` shortcut target.
- Added Linux setup guide in `docs/linux-user-setup.md`:
  - X11 setup and validation steps.
  - Wayland portal prerequisites and current backend expectations.
  - troubleshooting flow using EDMC debug logs.
- Added architecture cross-links to the new packaging/setup docs in `docs/requirements-architecture-notes.md`.
- Verification:
  - `source .venv/bin/activate && python -m pytest` passed.
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests` passed.

## Phase 6 — Tests + Verification
- Added Phase 6 smoke tests in `tests/test_phase6_smoke.py`:
  - worker-thread dispatch smoke for `thread_policy="worker"`.
  - backend lifecycle smoke to confirm startup replays enabled bindings and skips disabled bindings.
  - EDMC hook smoke for `journal_entry`/`dashboard_entry` dispatch pumping.
- Added manual QA release checklist in `docs/manual-qa-checklist.md` covering startup, settings UI, bindings persistence, dispatch behavior, backend checks (X11/Wayland/Windows), and shutdown.
- Verification:
  - `source .venv/bin/activate && python -m pytest` passed (`37 passed`).
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests` passed.
  - `make check` failed (`No rule to make target 'check'`).
  - `make test` failed (`No rule to make target 'test'`).

## Phase 7 — Side-Specific Modifiers
- Implemented canonical hotkey model and schema v3:
  - added canonical hotkey helpers in `edmc_hotkeys/hotkey.py`.
  - migrated bindings model to `plugin` + `modifiers` + `key` fields (`edmc_hotkeys/bindings.py`).
  - updated persistence and settings conversion paths for v3 bindings.
- Implemented side-aware settings capture/editor behavior:
  - hotkey field capture now tracks left/right modifier keys from Tk events.
  - prefs display uses pretty hotkey text (for example `LCtrl+RShift+A`) while runtime/storage use canonical tokens.
  - invalid hotkey edits block save and trigger a user-facing error dialog in prefs.
- Implemented canonical parser/runtime/backend routing updates:
  - parser now accepts canonical/pretty side-specific forms and rejects generic tokens (`Ctrl`, `Alt`, `Shift` without side).
  - `hotkey` callback kwarg and `list_bindings(plugin_name)` expose pretty hotkey text.
  - `list_bindings(plugin_name)` filtering now uses persisted binding `plugin` ownership.
- Implemented capability matrix and unsupported handling:
  - added backend capability flags (`supports_side_specific_modifiers`).
  - unsupported side-specific bindings are auto-disabled in active profile, persisted to `bindings.json`, and logged at `INFO` with reason.
- Implemented backend updates:
  - X11 matching now validates side-specific modifier state via keymap checks.
  - X11 side-specific bindings now use keymap polling + press-edge detection instead of relying on passive-grab delivery, eliminating observed modifier-order sensitivity and working for both left and right modifier variants.
  - Wayland reports side-specific as unsupported for capability routing.
  - Windows low-level hook path enabled by default for side-specific modifier matching.
- Added/updated tests and docs:
  - added `tests/test_phase7_side_specific.py`.
  - updated storage/settings/backend/UI tests for v3 schema and side-specific behavior.
  - updated docs: `docs/requirements-architecture-notes.md`, `docs/register-action-with-edmc-hotkeys.md`.
- Verification:
  - `source .venv/bin/activate && python -m pytest` passed (`57 passed`).
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests` passed.

## Cross-Platform Complexity Spec — Phase 1 (Core + X11 Alignment)
- Implemented backend contract validation helper in `edmc_hotkeys/backends/base.py`:
  - `backend_contract_issues(backend)` checks required backend interface shape for diagnostics/tests.
- Added contract coverage in `tests/test_backend_contract.py`:
  - verifies missing-contract violations are detected.
  - verifies built-in adapters satisfy contract shape.
- Centralized capability-gating intent in core policy helper:
  - added `_binding_requires_side_specific_capabilities(...)` in `load.py`.
  - kept auto-disable policy in startup/settings core paths and added summary disable-count logging.
- Standardized startup diagnostics in `edmc_hotkeys/plugin.py`:
  - logs selected backend + availability + `supports_side_specific_modifiers`.
  - registration-failure logs now include backend name.
- Aligned X11 diagnostics/lifecycle behavior in `edmc_hotkeys/backends/x11.py`:
  - consistent start/stop/register/unregister warnings and status logs.
  - X11 client clears in-memory registrations/callback state on stop.
- Expanded tests:
  - added startup/logging assertions in `tests/test_hotkey_plugin.py`.
  - added capability-policy helper coverage in `tests/test_phase7_side_specific.py`.
  - updated fake backend test doubles to satisfy backend capabilities contract.
- Closed current release-check gap:
  - added `scripts/check_no_print.py` and wired it into `make lint`.
  - `make check` now executes lint + typecheck placeholder + tests + compile.
- Verification:
  - `source .venv/bin/activate && python -m pytest -q` passed (`74 passed`).
  - `source .venv/bin/activate && make test` passed (`74 passed`).
  - `source .venv/bin/activate && make check` passed.

## Cross-Platform Complexity Spec — Phase 2 (Current-Scope Operational Guardrails)
- Consolidated runtime feature-flag documentation in a canonical source:
  - added `docs/feature-flags.md`.
- Updated docs to reference canonical flag guidance and avoid duplicated semantics/defaults:
  - `docs/requirements-architecture-notes.md`
  - `docs/linux-user-setup.md`
  - `docs/register-action-with-edmc-hotkeys.md`
- Expanded manual regression guardrails in `docs/manual-qa-checklist.md`:
  - explicit startup/backend-log pass/fail criteria.
  - explicit settings apply/validation pass/fail criteria.
  - dispatch/shutdown pass/fail criteria.
  - manual-only checks section with rationale.
- Added deterministic dispatch-pump lifecycle coverage in `tests/test_phase6_smoke.py`:
  - idempotent scheduler behavior while already scheduled.
  - safe stop behavior when no callback is scheduled.
- Updated phase/status tracking and implementation notes in:
  - `docs/plans/CROSS_PLATFORM_COMPLEXITY_MINIMIZATION_SPEC.md` (Phase 2 status/stages marked `Completed`, added Phase 2 implementation results).
- Verification:
  - `source .venv/bin/activate && python -m pytest -k "feature or backend"` passed (`28 passed, 48 deselected`).
  - `source .venv/bin/activate && python -m pytest tests/test_phase6_smoke.py tests/test_hotkey_plugin.py` passed (`18 passed`).
  - `source .venv/bin/activate && make test` passed (`76 passed`).
  - `source .venv/bin/activate && make check` passed.
  - `source .venv/bin/activate && python -m pytest` passed (`76 passed`).

## Cross-Platform Complexity Spec — Phase 3 (Wayland Backend Work)
- Status: Completed
- Implemented:
  - concrete Wayland portal client integration behind `PortalClient` in `edmc_hotkeys/backends/wayland.py`.
  - `DbusNextPortalService` runtime service for XDG Desktop Portal `GlobalShortcuts`.
  - `PortalGlobalShortcutsClient` delegating lifecycle/register/unregister operations to the service.
  - backend wrapper diagnostics for unavailable/start/register/unregister outcomes.
- Tests added/updated:
  - `tests/test_backends.py`:
    - concrete portal client delegation behavior.
    - unavailable/start-path logging behavior.
    - registration failure logging behavior.
- Tier boundary result:
  - Wayland remains Tier 1 only in this plugin (`supports_side_specific_modifiers=False`).
  - side-specific bindings remain explicitly unsupported and core-gated on Wayland.
- Verification:
  - `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"` passed (`7 passed, 16 deselected`).
  - `source .venv/bin/activate && python -m pytest tests/test_phase6_smoke.py -k "backend or dispatch"` passed (`6 passed, 4 deselected`).
  - `source .venv/bin/activate && make check` passed (`79 passed`).
  - `source .venv/bin/activate && python -m pytest` passed (`79 passed`).
- Source of truth:
  - detailed stage plan + completion summary in `docs/plans/CROSS_PLATFORM_COMPLEXITY_MINIMIZATION_SPEC.md` sections `11.5` and `11.6`.
