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
| 2.1 | Internal action registry module in EDMC-Hotkeys | Completed |
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

## Phase 7 — Side-Specific Modifiers (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 7.1 | Define canonical hotkey tokens for left/right modifiers (`CtrlL`, `CtrlR`, `AltL`, `AltR`, `ShiftL`, `ShiftR`) and compatibility rules with existing generic tokens | Pending |
| 7.2 | Update settings capture/editor to record and display side-specific modifiers while preserving existing generic hotkeys | Pending |
| 7.3 | Extend parser + binding model to represent side-specific modifiers without breaking existing `bindings.json` values | Pending |
| 7.4 | Implement backend capability matrix and behavior: enforce side-specific modifiers only where backend supports it; fail fast with explicit warning where unsupported | Pending |
| 7.5 | Add optional low-level backend paths required for true side-specific matching (Windows/X11), with safe fallback to current behavior when unavailable | Pending |
| 7.6 | Add tests: parser, settings capture, backend registration/matching, and unsupported-capability warnings | Pending |

### Phase 7 Execution Plan (This Iteration)
- Touch points:
  - `edmc_hotkeys/settings_ui.py` for side-aware capture tokens and field editing.
  - `edmc_hotkeys/backends/hotkey_parser.py` for canonical parsing of left/right modifiers.
  - Backend adapters under `edmc_hotkeys/backends/` for capability reporting and side-specific matching paths.
  - `docs/requirements-architecture-notes.md` for normative token/capability documentation.
- Key constraints discovered:
  - Current Windows path (`RegisterHotKey`) does not differentiate left/right modifiers.
  - Current X11 path (modifier masks only) does not differentiate left/right modifiers.
  - Wayland portal path currently has no side-specific contract in this plugin.
  - Therefore, true side-specific behavior requires low-level event hooks or backend-specific alternative APIs.
- Expected unchanged behavior during staged rollout:
  - Existing generic hotkeys (for example `Ctrl+Shift+1`) remain valid and unchanged.
  - No breaking schema migration in `bindings.json`; side-specific tokens are additive.
  - Unsupported side-specific hotkeys must not crash plugin startup; they should be rejected with clear log messages.
- Tests to run:
  - `source .venv/bin/activate && python -m pytest`
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`
  - Targeted backend tests for capability warnings and side-specific matching behavior

# Implementation Results

## Phase 1 — Architecture Decisions
- Documented Action Registry API (normative), threading contract, and error handling in `docs/requirements-architecture-notes.md`.
- Documented backend selection strategy for Windows/X11/Wayland and session detection rules.
- Documented `bindings.json` storage schema and profile handling for v1 bindings.

## Phase 2 — Core Plugin Skeleton
- Added a single EDMC plugin entrypoint at `load.py` for `EDMC-Hotkeys`, with logger wiring and lifecycle hooks.
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
