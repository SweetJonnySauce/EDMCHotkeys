# Windows Backend Implementation Plan

Follow persona details in `AGENTS.md`.
Document implementation results in the Implementation Results section.
After each stage is complete change status to Completed.
When all stages are complete change the phase status to Completed.
If something is not clear, ask clarifying questions.

## Scope
- Implement the Windows backend for global hotkeys using the existing backend interface and action registry contract.
- No feature changes beyond Windows backend behavior; keep existing registry, settings, and bindings behavior stable.
- Maintain Tk safety: background thread for OS hooks, dispatch to main thread by default.
- Include side-specific modifier support using a low-level hook path.

## Decisions (Captured)
- Side-specific modifiers are required in this implementation (use low-level hook path).
- Low-level hook path is always on for side-specific modifiers (no gating flag).
- Windows backend is greenfield under `edmc_hotkeys/backends/`.
- Run the full `pytest` suite during this phase.

## Phase 1 — Discovery & Constraints (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Reconfirm Windows backend requirements from `docs/requirements-architecture-notes.md` | Completed |
| 1.2 | Inventory current backend interfaces and selection logic touch points | Completed |
| 1.3 | Record invariants for threading, shutdown, and error handling | Completed |

### Phase 1 Notes
- Touch points:
  - `docs/requirements-architecture-notes.md`
  - Backend interface modules under `edmc_hotkeys/backends/`
  - Backend selection logic in plugin startup/shutdown
- Expected unchanged behavior:
  - No changes to action registry API or dispatch semantics.
  - No changes to settings UI or bindings schema.
- Tests to run (preflight sanity):
  - `source .venv/bin/activate && python -m pytest -k backend`

## Phase 2 — Windows Backend Design (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Define Windows backend module surface (init/register/unregister/poll/teardown) | Completed |
| 2.2 | Map canonical hotkey model to Windows registration constraints | Completed |
| 2.3 | Define fallback/unsupported cases and diagnostics | Completed |
| 2.4 | Define low-level hook path for side-specific modifiers (always-on) | Completed |

### Phase 2 Notes
- Touch points:
  - `edmc_hotkeys/backends/windows.py`
  - Canonical hotkey parsing/normalization helpers
- Expected unchanged behavior:
  - Binding validation remains canonical; unsupported bindings are skipped with logs.
- Tests to run (design validation):
  - `source .venv/bin/activate && python -m pytest -k windows_backend`

## Phase 3 — Implementation (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Implement Windows backend using `RegisterHotKey` path for non-side-specific bindings | Completed |
| 3.2 | Wire backend lifecycle into startup/shutdown with safe teardown | Completed |
| 3.3 | Ensure backend runs in a worker thread and marshals dispatch to main thread | Completed |
| 3.4 | Add guarded diagnostics for registration failures and shutdown behavior | Completed |

### Phase 3 Notes
- Touch points:
  - `edmc_hotkeys/backends/` Windows backend module
  - Backend selection and lifecycle wiring
  - Logging utilities
- Expected unchanged behavior:
  - No changes to bindings storage or settings UI flow.
  - No changes to action registry semantics.
- Tests to run:
  - `source .venv/bin/activate && python -m pytest -k windows`
  - `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`

## Phase 4 — Tests & Verification (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Unit tests for Windows backend registration/unregistration paths | Completed |
| 4.2 | Unit tests for backend selection on Windows environments | Completed |
| 4.3 | Integration test for hotkey dispatch pipeline on Windows backend | Completed |

### Phase 4 Notes
- Expected unchanged behavior:
  - Tests should not require UI thread manipulation beyond existing main-thread dispatch harness.
- Tests to run:
  - Add an integration test that wires `HotkeyPlugin` to `WindowsHotkeyBackend` with a fake Windows client and asserts backend callback -> action invocation end-to-end.
  - `source .venv/bin/activate && python -m pytest`
  - `make check` (if available)
  - `make test` (if available)

## Phase 5 — Docs + Compliance (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 5.1 | Update architecture notes with Windows backend details if changed | Completed |
| 5.2 | Update manual QA checklist with Windows-specific steps | Completed |
| 5.3 | Record implementation results and verification outcomes | Completed |

### Phase 5 Notes
- Touch points:
  - `docs/requirements-architecture-notes.md`
  - `docs/manual-qa-checklist.md`
- Tests to run:
  - `source .venv/bin/activate && python -m pytest`

# Implementation Results

## Phase 1 — Discovery & Constraints
- Reviewed Windows backend requirements in `docs/requirements-architecture-notes.md` (RegisterHotKey baseline, side-specific handling via low-level hook).
- Confirmed existing backend interface and selection logic (`edmc_hotkeys/backends/base.py`, `edmc_hotkeys/backends/selector.py`).
- Identified existing Windows backend implementation at `edmc_hotkeys/backends/windows.py` with low-level hook path previously gated by `EDMC_HOTKEYS_ENABLE_WINDOWS_LOW_LEVEL_HOOK` (removed in this implementation).

## Phase 2 — Windows Backend Design
- Replaced the Windows backend surface to mirror X11: backend wrapper + client implementation with explicit start/stop/register/unregister contract.
- Mapped canonical hotkey model to `RegisterHotKey` for non-side-specific bindings and low-level hook handling for side-specific modifiers.
- Defined unsupported/diagnostic behavior: invalid hotkeys reject registration and log warnings; low-level hook failure logs a warning but keeps RegisterHotKey path functional.
- Kept low-level hook path always-on when side-specific bindings are registered (no gating flags).

## Phase 3 — Implementation
- Replaced `edmc_hotkeys/backends/windows.py` with a message-loop client that installs the low-level hook and processes `RegisterHotKey` registrations on the loop thread.
- Implemented side-specific matching with left/right modifier state checks and edge-triggered activation to avoid auto-repeat re-fire.
- Removed the unused Windows low-level hook feature flag and deleted `edmc_hotkeys/feature_flags.py`.

## Phase 4 — Tests & Verification
- Added Windows backend wrapper tests using a fake client and verified canonical key conversion helpers.
- Existing backend selection test for Windows remains in place.
- Added integration test wiring `HotkeyPlugin` to `WindowsHotkeyBackend` with a fake Windows client to validate end-to-end dispatch.
- Verification:
  - `source .venv/bin/activate && python -m pytest` passed (149 passed).

## Phase 5 — Docs + Compliance
- Updated `docs/requirements-architecture-notes.md` to remove the Windows feature-gating mention.
- Updated `docs/manual-qa-checklist.md` with Windows low-level hook and side-specific verification steps.
- Updated feature-flag documentation to remove the Windows low-level hook flag entry.
- Removed stale `edmc_hotkeys/feature_flags.py` references from cross-platform planning docs.
