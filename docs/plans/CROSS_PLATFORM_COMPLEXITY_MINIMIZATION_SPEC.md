# Cross-Platform Complexity Minimization Spec

Status: Draft  
Owner: EDMC-Hotkeys  
Last Updated: 2026-02-26

## 1. Problem Statement
Global hotkeys are inherently platform-specific. Linux Wayland is the highest-complexity area because compositor behavior and portal support vary by environment. This spec defines a design that keeps complexity contained, keeps the plugin stable, and prevents platform-specific code from spreading through core logic.

## 2. Goals
- Keep core plugin behavior identical across OSes.
- Isolate OS differences behind one backend contract.
- Prefer graceful degradation over fragile partial support.
- Make unsupported capability states explicit, observable, and reversible.
- Keep rollout incremental with testable, reversible stages.

## 3. Non-Goals
- Supporting compositor-specific Wayland protocols in the baseline design.
- Implementing every possible advanced hotkey feature on every platform.
- Optimizing for feature parity over reliability.

## 4. Design Principles (Normative)
- Core-first architecture: parsing, validation, storage, conflict checks, and dispatch are backend-agnostic.
- Capability-driven behavior: core adapts from backend capabilities; core does not branch by platform name.
- Single Wayland path: use XDG Desktop Portal GlobalShortcuts only.
- Thin adapters: backends translate only registration/event details.
- Explicit downgrade paths: unsupported bindings are auto-disabled with persisted reasons.
- Release safety: experimental backend behavior must be gated by feature flags.

## 5. Runtime Architecture

## 5.1 Stable Core Boundary
Core modules own:
- Binding schema + persistence.
- Action registry + dispatch threading policy.
- Hotkey parsing/canonicalization/pretty rendering.
- Validation and conflict detection.
- Capability policy decisions (what is allowed/disabled).

Backends own:
- OS/session detection details.
- Native registration/unregistration.
- Native listener loop and event delivery.

## 5.2 Backend Contract (Required)
Every backend must implement:
- `availability() -> BackendAvailability`
- `capabilities() -> BackendCapabilities`
- `start(on_hotkey) -> bool`
- `stop() -> None`
- `register_hotkey(binding_id, hotkey) -> bool`
- `unregister_hotkey(binding_id) -> bool`

No backend is allowed to:
- Parse bindings differently than canonical parser behavior.
- Perform action resolution or dispatch policy decisions.
- Mutate binding documents directly.

## 5.3 Capability Tiers
Define feature support as tiers:
- Tier 0: backend unavailable (no global hotkeys).
- Tier 1: global hotkeys without side-specific modifier guarantees.
- Tier 2: side-specific modifiers supported (`ctrl_l`, `ctrl_r`, etc.).

Core policy:
- Bindings requiring Tier 2 are disabled on Tier 0/1.
- Tier 1-compatible bindings remain enabled everywhere Tier 1 exists.
- Disabled bindings are preserved (not deleted) and accompanied by a reason.

## 5.4 Platform Strategy
- Windows:
  - Baseline: `RegisterHotKey` path.
  - Optional Tier 2 path: low-level hook behind feature flag.
- Linux X11:
  - In-process X11 backend (`python-xlib`) with side-aware matching path.
- Linux Wayland:
  - Portal-only baseline (`XDG Desktop Portal GlobalShortcuts`).
  - No compositor-specific code in baseline.
  - If portal client unavailable, report Tier 0 with actionable diagnostics.

## 6. Wayland-Specific Complexity Controls
- Hard rule: no compositor-specific implementation in baseline.
- Treat portal support as a deploy/runtime prerequisite, not a plugin fallback problem.
- If GlobalShortcuts is unavailable:
  - Keep plugin loaded.
  - Keep settings usable.
  - Disable affected bindings and log explicit reasons.
- Do not silently remap side-specific modifiers to generic behavior.

## 7. Binding Semantics Policy
- Canonical schema remains authoritative (`modifiers` + `key`).
- Side-specific tokens are first-class in storage and validation.
- Runtime enablement is capability-gated, not syntax-gated.
- Unsupported bindings must stay visible in settings as disabled with reason text.

## 8. Observability and Diagnostics
Every startup must log:
- Selected backend name.
- Availability result and reason if unavailable.
- Capability map (at minimum side-specific support).
- Count of loaded bindings and count auto-disabled by capability policy.

Every registration failure must log:
- `binding_id`, normalized hotkey, backend name, and failure reason.

## 9. Testing and Verification Strategy
- Backend contract tests: same behavioral tests run against all adapters/fakes.
- Core policy tests: capability gating, disable reason generation, persistence behavior.
- Integration smoke tests:
  - Startup + backend selection.
  - Binding registration replay.
  - Invocation dispatch path.
  - Settings save/validation behavior.
- Release verification:
  - `python -m pytest`
  - `make test`
  - `make check`
  - Targeted manual QA on at least one Windows and one Linux session type.

## 10. Feature Flag Policy
- Experimental backend logic must be opt-in via environment feature flags.
- Flags must be documented in one place and include removal criteria.
- Default behavior must remain stable and conservative.

## 11. Rollout Plan

## Phase 1 — Core + X11 Alignment (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Freeze backend interface and enforce adapter-only responsibilities in code review/tests | Completed |
| 1.2 | Centralize capability gating in core startup/settings paths and remove drift from adapter logic | Completed |
| 1.3 | Align X11 behavior to contract (registration lifecycle, side-specific policy, diagnostics) without changing core API | Completed |
| 1.4 | Expand automated coverage for core policy + X11 contract/integration paths | Completed |
| 1.5 | Close gaps in release checks for current scope (`python -m pytest`, `make test`, `make check`) | Completed |

## Phase 2 — Current-Scope Operational Guardrails (Status: Planned)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Consolidate feature-flag docs and removal criteria for existing toggles | Planned |
| 2.2 | Add regression checklist for startup/shutdown thread safety and dispatch pumping | Planned |
| 2.3 | Add implementation notes tying current behavior to this spec and update docs links | Planned |

## Phase 3 — Wayland Backend Work (Status: Deferred)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Implement/integrate a concrete XDG GlobalShortcuts portal client behind `PortalClient` | Deferred |
| 3.2 | Add unavailable/partial-support diagnostics and integration tests for portal runtime states | Deferred |
| 3.3 | Revisit Wayland Tier 1/Tier 2 support boundaries after portal client validation | Deferred |

## Phase 4 — Windows Backend Work (Status: Deferred)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Refine RegisterHotKey vs low-level-hook routing so non-side-specific modifier chords stay on baseline path | Deferred |
| 4.2 | Harden low-level hook lifecycle/error handling and add targeted contract tests | Deferred |
| 4.3 | Re-evaluate feature-flag default/removal criteria after Windows validation pass | Deferred |

## 11.1 Phase 1 Detailed Execution Plan

Scope:
- Align core plugin + X11 behavior with this spec.
- Do not implement new Wayland or Windows backend behavior in this phase.

Out of scope:
- Any concrete Wayland portal client integration work.
- Any Windows routing/fallback behavior changes.

Execution order:
1. Complete 1.1 before 1.2.
2. Complete 1.2 before 1.3.
3. Complete 1.3 before 1.4.
4. Complete 1.4 before 1.5.

### Stage 1.1 — Freeze Backend Interface and Adapter Responsibilities
Objective:
- Lock down backend contract boundaries and prevent business logic from drifting into adapters.

Touch points:
- `edmc_hotkeys/backends/base.py`
- `edmc_hotkeys/plugin.py`
- `docs/requirements-architecture-notes.md`
- `tests/test_backends.py`

Tasks:
- Document adapter responsibility rules at the backend interface boundary.
- Add/adjust tests that fail if adapters perform non-adapter concerns (action dispatch, persistence mutation, parser divergence).
- Ensure plugin-level orchestration remains the only place where backend + action registry are connected.

Acceptance criteria:
- Backend contract is explicit and unchanged across all adapters.
- Contract tests verify required methods and basic lifecycle behavior.
- No adapter directly invokes registry callbacks beyond emitting binding IDs through the provided callback.

Tests to run:
- `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "select_backend or backend"`
- `source .venv/bin/activate && python -m pytest`

Risk and rollback:
- Risk: over-constraining test assertions may block legitimate adapter internals.
- Rollback: revert only new contract assertions; keep documentation updates.

### Stage 1.2 — Centralize Capability Gating in Core
Objective:
- Ensure capability-based enable/disable policy is enforced only in core startup/settings flows.

Touch points:
- `load.py`
- `edmc_hotkeys/plugin.py`
- `edmc_hotkeys/settings_state.py`
- `tests/test_phase7_side_specific.py`
- `tests/test_phase6_smoke.py`

Tasks:
- Audit and remove duplicated gating behavior from adapter-level code where core policy should own it.
- Keep startup/settings save flows as the single policy authority for capability-driven disable behavior.
- Expand tests for mixed binding sets (supported + unsupported) with persisted disable reasons.

Acceptance criteria:
- Core has one policy path for capability gating.
- Unsupported bindings are auto-disabled, persisted, and logged with reason.
- Supported bindings remain active and register normally.

Tests to run:
- `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py tests/test_phase6_smoke.py`
- `source .venv/bin/activate && python -m pytest`

Risk and rollback:
- Risk: moving gating paths can change startup behavior unexpectedly.
- Rollback: keep prior policy path behind a temporary guarded fallback and revert if regressions appear.

### Stage 1.3 — Align X11 Behavior to Contract
Objective:
- Make X11 implementation behavior match contract expectations without changing public API.

Touch points:
- `edmc_hotkeys/backends/x11.py`
- `edmc_hotkeys/backends/selector.py`
- `docs/linux-user-setup.md`
- `tests/test_backends.py`

Tasks:
- Verify registration lifecycle and callback semantics stay contract-compliant.
- Standardize diagnostics for X11 availability, registration failures, and callback failures.
- Keep side-specific handling in X11 implementation while keeping policy decisions in core.

Acceptance criteria:
- X11 backend reports availability/capabilities consistently.
- Registration/unregistration/start/stop behavior passes contract and smoke tests.
- No public API changes in `load.py` or binding schema.

Tests to run:
- `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "x11"`
- `source .venv/bin/activate && python -m pytest`

Risk and rollback:
- Risk: listener-loop adjustments may introduce missed or duplicated callback edges.
- Rollback: revert X11 loop changes only, keep logging/contract-test improvements.

### Stage 1.4 — Expand Automated Coverage for Core Policy + X11
Objective:
- Raise confidence with focused tests before any deferred backend work starts.

Touch points:
- `tests/test_backends.py`
- `tests/test_hotkey_plugin.py`
- `tests/test_phase6_smoke.py`
- `tests/test_phase7_side_specific.py`
- `tests/test_settings_state.py`

Tasks:
- Add targeted tests for capability gating, disable reason persistence, and X11 contract paths.
- Add regression tests for startup replay and binding replacement behavior with capability constraints.
- Add test naming/markers that map directly to rollout stage intent.

Acceptance criteria:
- Coverage exists for all Phase 1 policy behaviors.
- Tests clearly separate core policy failures from adapter failures.
- No existing tests removed without replacement.

Tests to run:
- `source .venv/bin/activate && python -m pytest`
- `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`

Risk and rollback:
- Risk: brittle tests overfit implementation details.
- Rollback: keep only black-box assertions aligned to contract outputs.

### Stage 1.5 — Close Release-Check Gaps for Current Scope
Objective:
- Make validation commands reliable for core + X11 iteration flow.

Touch points:
- `Makefile`
- `requirements-dev.txt`
- `docs/manual-qa-checklist.md`
- `docs/plans/IMPLEMENTATION_PLAN.md`

Tasks:
- Ensure `make test` and `make check` run meaningful checks in this repo.
- Align documented commands with actual repo behavior.
- Record command results and known skips/failures in implementation notes.

Acceptance criteria:
- `make test` runs and passes on the intended local workflow.
- `make check` runs and includes lint/typecheck/pytest defaults or clearly documented placeholders.
- Documentation and command behavior are consistent.

Tests to run:
- `source .venv/bin/activate && make test`
- `source .venv/bin/activate && make check`
- `source .venv/bin/activate && python -m pytest`

Risk and rollback:
- Risk: check targets can become slow/noisy and reduce iteration speed.
- Rollback: keep a fast default target and move expensive checks to opt-in targets.

Phase 1 done definition:
- Stages `1.1` through `1.5` marked `Completed`.
- Phase 1 status updated to `Completed`.
- Phase 1 implementation summary added to `docs/plans/IMPLEMENTATION_PLAN.md` with executed test commands and outcomes.

## 11.2 Phase 1 Implementation Results
- Added explicit backend contract validation helper (`backend_contract_issues`) and exported it for test/runtime diagnostics.
- Added backend contract coverage in `tests/test_backend_contract.py`.
- Centralized capability-policy intent in core policy helper (`_binding_requires_side_specific_capabilities`) and retained auto-disable policy in `load.py` startup/settings paths.
- Standardized startup diagnostics in `HotkeyPlugin.start()`:
  - selected backend name
  - availability status
  - `supports_side_specific_modifiers` capability flag
- Improved registration failure diagnostics to include backend name.
- Improved X11 wrapper diagnostics for start/stop/register/unregister failures and cleared in-memory X11 client state on stop.
- Added targeted plugin tests for startup capability logging and backend-name registration failure logging.
- Added a meaningful lint check (`scripts/check_no_print.py`) and wired it into `make check`.
- Verification run:
  - `source .venv/bin/activate && python -m pytest -q` (`74 passed`)
  - `source .venv/bin/activate && make test` (`74 passed`)
  - `source .venv/bin/activate && make check` (passed)

## 12. Implementation Notes for This Repository
- Keep `load.py` as the only EDMC entry point.
- Keep backend selection in `edmc_hotkeys/backends/selector.py`; no platform branches outside selector/backends.
- Keep capability gating in core startup/settings flow.
- Keep wayland backend wrapper thin; any future portal client implementation must be injected behind the existing protocol boundary.

## 13. Decision Record
- Accepted: platform differences are adapter-level concerns.
- Accepted: portal-only Wayland baseline for complexity control.
- Accepted: capability-tier gating as the primary compatibility mechanism.
- Deferred: compositor-specific Wayland integrations.
