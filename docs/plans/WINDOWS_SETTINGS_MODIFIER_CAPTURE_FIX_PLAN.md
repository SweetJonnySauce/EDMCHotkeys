# Windows Settings Modifier Capture Fix Plan

Status: Completed  
Owner: EDMCHotkeys  
Last Updated: 2026-02-27

## Problem Statement
On Windows, entering hotkeys with modifiers in the settings pane can incorrectly inject `LAlt` into captured shortcuts. This appears in UI capture before backend registration and causes side-specific bindings to be saved with an unintended `LAlt` token.

## Decisions (Captured 2026-02-27)
- When `supports_side_specific_modifiers=True` on Windows, include `Alt` only if `Alt_L` or `Alt_R` keydown was explicitly observed in the capture widget.
- Apply the same explicit-observation rule to all side-specific modifier groups (`Ctrl`, `Shift`, `Win`): do not synthesize a side-specific token from `event.state` alone.
- Scope this Windows-specific behavior only to side-specific capture mode (`supports_side_specific_modifiers=True`); generic modifier mode behavior remains unchanged.
- Add a warning log when ambiguous modifier state is detected (modifier bit set in `event.state` without matching explicit side keydown observation).

## Scope
- Fix settings capture logic for Windows so side-specific modifiers are only emitted when observed explicitly.
- Keep Linux behavior unchanged (X11 and Wayland paths must remain behavior-compatible).
- Add debug diagnostics for capture decisions, gated the same way as existing debug logging.

## Non-Goals
- No backend runtime registration changes in this phase (`windows.py`, `x11.py`, `wayland.py` unchanged unless a blocker is proven).
- No schema/storage format changes for bindings.
- No new feature flags.

## Touch Points
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_ui.py`
- `tests/test_phase7_side_specific.py` (if assertions need to reflect Windows-only capture rules)
- `docs/manual-qa-checklist.md` (only if manual verification steps need updates)

## Expected Unchanged Behavior
- Linux hotkey capture behavior remains unchanged for X11 and Wayland.
- Existing non-side-specific capture behavior remains unchanged.
- Registry/backend dispatch semantics remain unchanged.
- Tk threading model remains unchanged (all settings capture logic stays on the main thread).

## Phase 1 - Reproduce and Freeze Invariants (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Reproduce the Windows phantom `LAlt` capture path with deterministic unit cases | Completed |
| 1.2 | Document capture invariants for Windows vs Linux modifier synthesis | Completed |
| 1.3 | Define acceptance criteria for Windows fix and Linux non-regression | Completed |

### Phase 1 Notes
- Invariant candidate: when side-specific mode is enabled, side token emission should come from explicit modifier key tracking, not inferred defaults.
- Invariant candidate: Linux capture path remains exactly as-is unless test evidence shows parity breakage.
- Locked behavior for Windows side-specific mode: `event.state` alone is insufficient to emit side-specific tokens.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py -k "hotkey_from_parts or hotkey_from_event"`

## Phase 1 Detailed Execution Plan

Execution order:
1. Complete `1.1` before `1.2`.
2. Complete `1.2` before `1.3`.
3. Do not start Phase 2 design edits until all Phase 1 stages are marked `Completed`.

### Stage 1.1 - Reproduce Windows Phantom Modifier Injection
Objective:
- Build deterministic, test-backed reproduction of the phantom `LAlt` behavior in settings capture under Windows-side-specific mode.

Touch points:
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_ui.py`

Tasks:
- Add test cases that simulate settings-capture inputs where:
  - side-specific mode is enabled,
  - `event.state` indicates one or more modifier bits,
  - `active_modifiers` does not contain the corresponding explicit side token.
- Verify current behavior in those tests captures unintended side-specific tokens (especially `alt_l`) so the failure is anchored before code changes.
- Ensure at least one control case demonstrates expected capture when explicit side modifier keydown was tracked.
- Keep tests pure and headless (no runtime Tk event loop dependency).

Acceptance criteria:
- At least one deterministic test demonstrates phantom side-specific modifier synthesis from `event.state` alone.
- At least one deterministic test demonstrates explicit tracked-side modifier capture still works.
- Reproduction tests fail against current behavior only in the intended regression scenario.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py -k "modifier and side_specific"`

Risk and rollback:
- Risk: test setup may not reflect the actual EDMC/Tk event shape seen on Windows.
- Rollback: capture and mirror real debug event fields from runtime logs, then adjust test inputs to match observed shapes.

### Stage 1.2 - Freeze Modifier Synthesis Invariants
Objective:
- Convert the agreed decisions into explicit invariants so implementation cannot drift.

Touch points:
- `docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`
- `edmc_hotkeys/settings_ui.py` (for mapping invariants to code seams)

Tasks:
- Document invariant statements that distinguish:
  - Windows + side-specific mode behavior,
  - generic modifier mode behavior,
  - Linux behavior parity expectations.
- Document precedence contract:
  - explicit side modifier observations are authoritative,
  - `event.state` alone is not sufficient for side-specific token synthesis on Windows.
- Define observability contract:
  - warning on ambiguous modifier state in Windows side-specific mode,
  - debug detail for full capture resolution context.

Acceptance criteria:
- Invariants are explicit, testable, and directly map to upcoming helper/function boundaries in `settings_ui.py`.
- Invariants clearly separate Windows-specific rules from Linux and generic-mode behavior.
- Logging expectations are precise enough to test for presence/absence by level.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py -k "hotkey_from_parts"`

Risk and rollback:
- Risk: invariant wording is too broad and unintentionally constrains unrelated input paths.
- Rollback: narrow invariants to externally observable outputs (captured hotkey string + log behavior) only.

### Stage 1.3 - Lock Acceptance Criteria and Exit Gates
Objective:
- Define concrete phase exit gates so implementation and verification are unambiguous.

Touch points:
- `docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`
- `tests/test_settings_ui.py`
- `tests/test_phase7_side_specific.py`

Tasks:
- Define the exact expected outputs for Windows-side-specific ambiguous-state scenarios.
- Define Linux non-regression assertions that must remain unchanged.
- Define logging acceptance:
  - warning required for ambiguous modifier state (Windows side-specific mode),
  - no new warning for unaffected capture paths.
- Add explicit Phase 1 exit checklist linking each criterion to a planned test/assertion.

Acceptance criteria:
- Each behavioral decision has a measurable assertion target in tests.
- Linux non-regression scope is explicit (X11/Wayland behavior unchanged by capture logic).
- Phase 2 entry criteria are objective and checklist-based.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py tests/test_phase7_side_specific.py -k "side_specific or modifier"`

Risk and rollback:
- Risk: acceptance criteria omit an edge case and allow partial fix.
- Rollback: add missing edge criteria before Phase 2 starts; do not proceed with implementation until gaps are closed.

Phase 1 done definition:
- Stages `1.1`, `1.2`, and `1.3` marked `Completed`.
- Phase 1 status changed to `Completed`.
- A `## Phase 1 Implementation Results` section is added with:
  - tests added/updated for reproduction,
  - command outcomes,
  - final frozen invariant list.

## Phase 1 Implementation Results (Completed)

### Stage 1.1 Outputs (Completed)
- Added deterministic characterization tests in `tests/test_settings_ui.py`:
  - `test_hotkey_from_parts_characterizes_state_only_alt_as_left_alt`
  - `test_hotkey_from_parts_prefers_explicit_side_modifier_over_state_default`
  - `test_hotkey_from_parts_windows_side_specific_requires_explicit_alt_side_observation` (`xfail`, `strict=True`) to lock desired Windows-side-specific behavior for Phase 2.
- These tests anchor the current regression mechanism: side-specific capture can synthesize `LAlt` from `event.state` when no explicit `Alt_L`/`Alt_R` keydown is tracked.

### Stage 1.2 Outputs (Completed)
- Frozen invariants documented in this plan:
  - Windows + side-specific mode (`supports_side_specific_modifiers=True`): side tokens must come from explicit side keydown observation, not `event.state` alone.
  - Generic modifier mode behavior remains unchanged.
  - Linux capture behavior (X11/Wayland) remains unchanged.
  - Ambiguous modifier-state situations require operator-visible warning logging (implementation in later phases).

### Stage 1.3 Outputs (Completed)
- Acceptance criteria locked for implementation entry:
  - Windows side-specific ambiguous state should not emit side-specific modifiers without explicit side observation.
  - Linux and generic-mode behavior must remain parity-stable.
  - Warning logging is required for ambiguous Windows side-specific modifier state.
- Exit gating for Phase 2 is now objective and mapped to deterministic tests in `tests/test_settings_ui.py` and `tests/test_phase7_side_specific.py`.

### Phase 1 Verification Command Outcomes
- `python -m pytest tests/test_settings_ui.py -k "hotkey_from_parts or hotkey_from_event"` failed:
  - shell could not execute `python` in this environment (`python.exe` launch failure via WindowsApps shim).
- `py -3 -m pytest tests/test_settings_ui.py -k "hotkey_from_parts or hotkey_from_event"` failed:
  - `No module named pytest`.
- `py -3 -m pip install -r requirements-dev.txt` failed:
  - dependency resolution could not find `pytest` in the current environment index.

Verification status:
- Test design and reproduction coverage were implemented.
- Command execution verification is blocked by local environment/tooling availability and must be rerun once a Python environment with `pytest` is available.

## Phase 2 - Design (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Define platform-aware modifier synthesis contract (Windows-specific branch) | Completed |
| 2.2 | Define precedence rules: explicit active modifiers vs `event.state` fallback | Completed |
| 2.3 | Define debug instrumentation fields and log points for capture decisions | Completed |

### Phase 2 Notes
- Proposed Windows rule: do not auto-synthesize side-specific tokens from `event.state` alone.
- Proposed precedence: explicit tracked modifier token wins; fallback from `state` is limited to safe cases.
- Proposed diagnostics (debug-gated):
  - `keysym`, `char`, `state`, active modifier tokens, resolved grouped tokens, final captured hotkey.
- Additional operator signal:
  - warning when `event.state` indicates a modifier but no explicit side modifier keydown was tracked in side-specific mode.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py -k "side_specific or modifier"`

## Phase 2 Detailed Execution Plan

Execution order:
1. Complete `2.1` before `2.2`.
2. Complete `2.2` before `2.3`.
3. Keep code changes out of this phase unless needed to expose explicit design seams for Phase 3.
4. Do not start Phase 3 implementation until Phase 2 stages are marked `Completed`.

### Stage 2.1 - Define Platform-Aware Capture Contract
Objective:
- Specify the exact decision boundary for Windows-side-specific modifier synthesis while preserving Linux and generic-mode behavior.

Touch points:
- `docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_ui.py`

Tasks:
- Document the full contract matrix for modifier synthesis by platform/mode:
  - Windows + `supports_side_specific_modifiers=True`.
  - Windows + `supports_side_specific_modifiers=False`.
  - Linux (all flavors) + existing capture behavior.
- Define explicit input-to-output expectations for ambiguous states:
  - modifier bit present in `event.state`,
  - no matching side-specific token in `active_modifiers`.
- Identify the minimal function seam in `settings_ui.py` where platform branching should live so Phase 3 edits remain localized.
- Confirm design keeps output format unchanged (`pretty_hotkey_text` contract unchanged).

Acceptance criteria:
- A written matrix exists that unambiguously defines behavior by platform/mode.
- Ambiguous Windows-side-specific scenarios have explicit expected outputs.
- Proposed seam location in `settings_ui.py` is clear and minimizes blast radius.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py -k "characterizes_state_only_alt or side_specific"`

Risk and rollback:
- Risk: platform contract becomes coupled to assumptions not observable in current tests.
- Rollback: narrow contract language to observable function inputs/outputs only.

### Stage 2.2 - Define Modifier Resolution Precedence and Edge Cases
Objective:
- Lock deterministic precedence rules for merging `active_modifiers` and `event.state`, including edge cases for missing side observations.

Touch points:
- `docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_ui.py`

Tasks:
- Define precedence in order:
  - explicit side token from `active_modifiers` (authoritative),
  - safe fallback paths by platform/mode,
  - suppression rule for Windows-side-specific ambiguous state.
- Define behavior for mixed states:
  - explicit token exists but `state` bit absent,
  - `state` bit exists but explicit token absent,
  - multiple modifier groups partially observed.
- Define exact expected outputs for each edge case as future test targets.
- Confirm no change to key normalization path (`_normalize_hotkey_key`) and non-modifier key handling.

Acceptance criteria:
- Precedence rules are deterministic and order-specific.
- Edge cases are enumerated with expected output strings.
- Linux and generic-mode no-change guarantees are explicit and testable.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py -k "modifier and hotkey_from_parts"`

Risk and rollback:
- Risk: precedence rules accidentally alter existing generic modifier capture semantics.
- Rollback: split side-specific and generic synthesis paths in design before implementation.

### Stage 2.3 - Design Instrumentation and Log Contract
Objective:
- Define observability that is sufficient for runtime diagnosis without introducing noisy logs.

Touch points:
- `docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`
- `edmc_hotkeys/settings_ui.py`
- Existing logger usage in `load.py` and backend modules

Tasks:
- Define debug log payload fields for capture resolution:
  - `keysym`, `char`, `state`, `active_modifiers`, resolved grouped modifiers, final hotkey.
- Define warning contract:
  - emit warning only for Windows + side-specific mode when `event.state` indicates a modifier but no explicit side token exists for that group.
- Define warning dedupe/noise behavior:
  - no warning for unaffected paths,
  - no warning when explicit side token is present.
- Define how tests will assert log behavior (level + key message fragment).

Acceptance criteria:
- Debug and warning logging conditions are explicit, scoped, and testable.
- Logging contract distinguishes ambiguity warnings from normal capture diagnostics.
- Log plan aligns with existing debug gating practices in repository code.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py -k "log or warning or modifier"`

Risk and rollback:
- Risk: warnings become noisy during normal typing in settings UI.
- Rollback: tighten warning trigger to one precise ambiguity condition per capture event.

Phase 2 done definition:
- Stages `2.1`, `2.2`, and `2.3` marked `Completed`.
- Phase 2 status changed to `Completed`.
- A `## Phase 2 Design Results` section is added with:
  - finalized behavior matrix,
  - finalized precedence table,
  - finalized logging contract and planned assertion points.

## Phase 2 Design Results (Completed)

### Stage 2.1 Outputs (Completed)
Finalized platform/mode behavior matrix for modifier synthesis:

| Platform / Mode | Side-specific tokens synthesized from `event.state` only | Behavior |
| --- | --- | --- |
| Windows + `supports_side_specific_modifiers=True` | No | Use explicit side tokens from `active_modifiers` only; if `state` bit is set without explicit side token for that modifier group, suppress that group and flag ambiguity. |
| Windows + `supports_side_specific_modifiers=False` | Not applicable | Keep existing generic behavior: merge `active_modifiers` and `event.state` as today, then normalize to generic modifier names. |
| Linux (X11/Wayland/GNOME bridge) + `supports_side_specific_modifiers=True` | Yes (existing behavior) | Keep current behavior unchanged: side-specific defaults may be inferred from `event.state` when no explicit side token is tracked. |
| Linux (all flavors) + `supports_side_specific_modifiers=False` | Not applicable | Keep current behavior unchanged: generic modifiers produced as today. |

Finalized seam for Phase 3 implementation:
- Localize platform-aware modifier resolution inside `edmc_hotkeys/settings_ui.py` by extracting helper logic from `hotkey_from_parts(...)`.
- Keep `hotkey_from_parts(...)` public signature stable.
- Add a pure helper seam for deterministic tests, with explicit inputs:
  - `state`
  - grouped `active_modifiers`
  - `supports_side_specific_modifiers`
  - platform selector (`is_windows` decision derived in one place).

### Stage 2.2 Outputs (Completed)
Finalized modifier precedence order:
1. Normalize and group `active_modifiers` first (authoritative source for side-specific tokens).
2. For each modifier group (`ctrl`, `alt`, `shift`, `win`):
   - if group already present from explicit token, keep it.
   - else if Windows + side-specific mode and `state` bit is set, do not synthesize a side token; mark group ambiguous.
   - else apply current fallback behavior (existing `_default_modifier_token(...)` path).
3. Apply existing generic-normalization pass when `supports_side_specific_modifiers=False`.
4. Preserve canonical output ordering via `CANONICAL_MODIFIER_ORDER`.

Finalized edge-case expectations:
- Explicit side token present + `state` bit absent -> keep explicit side token.
- `state` bit present + no explicit token (Windows + side-specific mode) -> suppress that modifier group and emit ambiguity warning.
- `state` bit present + no explicit token (Linux + side-specific mode) -> preserve current inferred side-specific default behavior.
- Mixed observed/unobserved groups -> apply rules per group independently.
- Key normalization path (`_normalize_hotkey_key`) remains unchanged.

### Stage 2.3 Outputs (Completed)
Finalized logging contract:
- Debug log (gated):
  - Emit capture-resolution diagnostics only when debug logging is enabled.
  - Include: `keysym`, `char`, `state`, `active_modifiers`, resolved modifier groups, ambiguous groups, final captured hotkey.
- Warning log (always visible):
  - Emit once per capture event for Windows + side-specific mode when any modifier group is ambiguous (bit set in `event.state` with no explicit side token observed).
  - Do not emit warning when:
    - explicit side token exists for the group,
    - mode is generic (`supports_side_specific_modifiers=False`),
    - platform is non-Windows.

Planned assertion points for Phase 3/4 tests:
- `caplog` warning assertion for ambiguous Windows-side-specific event.
- `caplog` no-warning assertion for explicit side-token events.
- `caplog` no-warning assertion for Linux parity path.
- output-string assertions proving suppression of ambiguous Windows side-specific modifiers.

### Phase 2 Verification Command Outcomes
- No additional executable verification commands were completed in this phase due local environment constraints documented in Phase 1:
  - `pytest` unavailable in the current interpreter environment.
- Phase 2 deliverable is a completed design contract; executable verification remains scheduled for Phase 3/4 once test tooling is available.

## Phase 3 - Implementation (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Refactor modifier synthesis in `hotkey_from_parts` into an explicit helper seam | Completed |
| 3.2 | Implement Windows-only synthesis rule to prevent phantom `LAlt` injection | Completed |
| 3.3 | Add debug-gated capture diagnostics in settings capture path | Completed |
| 3.4 | Keep Linux code path behavior-identical and document branch boundaries in code comments | Completed |

### Phase 3 Notes
- Keep edit scope narrow to settings capture logic only.
- Any new helper should be pure/data-only for deterministic tests.
- Debug logs must remain low-noise and only emit when debug logging is enabled.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py`
2. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py`

## Phase 3 Detailed Execution Plan

Execution order:
1. Complete `3.1` before `3.2`.
2. Complete `3.2` before `3.3`.
3. Complete `3.3` before `3.4`.
4. Run targeted tests after each stage where possible; run combined checks at end of phase.

### Stage 3.1 - Extract Modifier Resolution Helper Seam
Objective:
- Refactor `hotkey_from_parts(...)` to isolate modifier-resolution logic behind pure helpers while preserving current behavior before Windows-specific rule changes.

Touch points:
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_ui.py`

Tasks:
- Extract modifier-group synthesis from `hotkey_from_parts(...)` into a dedicated helper with explicit inputs:
  - `state`
  - grouped `active_modifiers`
  - `supports_side_specific_modifiers`
  - platform selector (`is_windows` or equivalent)
- Keep public function signatures stable for `hotkey_from_event(...)` and `hotkey_from_parts(...)`.
- Preserve canonical ordering and formatting pipeline (`CANONICAL_MODIFIER_ORDER`, `pretty_hotkey_text`).
- Add minimal comments where helper boundaries are non-obvious.

Acceptance criteria:
- Refactor-only stage preserves output behavior for existing non-Windows paths.
- Helper seam is pure/data-driven and testable without Tk runtime.
- Existing tests compile and (when environment permits) run without behavioral regressions from refactor alone.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py -k "hotkey_from_parts"`

Risk and rollback:
- Risk: helper extraction inadvertently changes modifier precedence.
- Rollback: revert extraction and re-introduce helpers in smaller slices with characterization tests guarding each slice.

### Stage 3.2 - Implement Windows Side-Specific Ambiguity Suppression
Objective:
- Implement agreed Windows-only rule: in side-specific mode, do not synthesize side tokens from `event.state` alone when explicit side keydown was not observed.

Touch points:
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_ui.py`
- `tests/test_phase7_side_specific.py`

Tasks:
- Update helper logic so Windows + `supports_side_specific_modifiers=True`:
  - trusts explicit side tokens from `active_modifiers`,
  - suppresses ambiguous groups where only `event.state` bit is present.
- Ensure generic mode (`supports_side_specific_modifiers=False`) remains unchanged.
- Ensure Linux behavior remains unchanged per Phase 2 matrix.
- Convert Phase 1 strict `xfail` expectation into a passing regression assertion once behavior is implemented.

Acceptance criteria:
- Ambiguous Windows-side-specific capture no longer emits `LAlt`/other side defaults from `state` alone.
- Explicit side observations still produce correct side-specific tokens.
- Linux and generic-mode expectations remain unchanged.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py -k "side_specific or modifier"`
2. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "settings_capture"`

Risk and rollback:
- Risk: Windows suppression logic leaks into Linux path.
- Rollback: gate Windows branch behind explicit platform check and isolate branch in helper-level unit tests.

### Stage 3.3 - Add Logging Instrumentation per Contract
Objective:
- Add observability for modifier-capture resolution with debug detail and precise ambiguity warnings.

Touch points:
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_ui.py`

Tasks:
- Add debug-gated log in capture resolution path including:
  - `keysym`, `char`, `state`, `active_modifiers`, resolved groups, ambiguous groups, final captured hotkey.
- Add warning log for Windows + side-specific ambiguous-state events:
  - one warning per capture event when any modifier group is ambiguous.
- Keep warning suppressed for:
  - explicit side token present,
  - generic mode,
  - non-Windows platforms.
- Add/adjust `caplog` tests for warning presence/absence and key message fragments.

Acceptance criteria:
- Debug logs follow existing repository gating practices.
- Warning logs are precise and low-noise.
- Log behavior is test-covered with deterministic assertions.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py -k "warning or log or modifier"`

Risk and rollback:
- Risk: warning frequency is too high during normal settings typing.
- Rollback: tighten trigger to emit only when resolved output would otherwise have synthesized a side-specific token from `state` alone.

### Stage 3.4 - Confirm Linux Parity and Document Boundaries
Objective:
- Prove Linux behavior remains unchanged and document platform branching boundaries clearly in code and plan results.

Touch points:
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_ui.py`
- `tests/test_phase7_side_specific.py`
- `docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`

Tasks:
- Verify Linux-oriented tests remain unchanged and passing (when environment permits).
- Add/adjust tests as needed to assert no-warning/no-behavior-drift on Linux parity path.
- Add concise code comments around platform branch entry to prevent future drift.
- Document completed implementation outputs and command outcomes under Phase 3 results.

Acceptance criteria:
- Linux behavior assertions remain intact with no expected-output drift.
- Platform branching location is explicit and maintainable.
- Phase 3 implementation results include tests run and any blocked checks.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py tests/test_phase7_side_specific.py`
2. `source .venv/bin/activate && python -m pytest`
3. `source .venv/bin/activate && make check`

Risk and rollback:
- Risk: parity gap appears in Linux-specific assertions after Windows changes.
- Rollback: isolate Windows branch logic further and re-run targeted Linux parity tests before proceeding.

Phase 3 done definition:
- Stages `3.1`, `3.2`, `3.3`, and `3.4` marked `Completed`.
- Phase 3 status changed to `Completed`.
- A `## Phase 3 Implementation Results` section is added with:
  - code seams introduced,
  - behavior changes implemented (Windows-only),
  - test command outcomes and environment blockers (if any).

## Phase 3 Implementation Results (Completed)

### Stage 3.1 Outputs (Completed)
- Refactored `edmc_hotkeys/settings_ui.py` to introduce a pure modifier-resolution seam:
  - `_hotkey_from_parts_with_details(...)`
  - `_resolve_modifier_groups(...)`
  - `_is_windows_platform()`
- Kept public signatures stable for:
  - `hotkey_from_event(...)`
  - `hotkey_from_parts(...)`
- `hotkey_from_parts(...)` now delegates through the new helper seam while preserving canonical output formatting.

### Stage 3.2 Outputs (Completed)
- Implemented Windows-only side-specific ambiguity suppression in `_resolve_modifier_groups(...)`:
  - when `supports_side_specific_modifiers=True` and platform is Windows, modifier groups set only in `event.state` (without explicit side token in `active_modifiers`) are suppressed.
- Preserved generic-mode behavior (`supports_side_specific_modifiers=False`) and Linux parity path behavior.
- Updated tests to remove the strict `xfail` and assert the new Windows behavior directly.

### Stage 3.3 Outputs (Completed)
- Added capture-path diagnostics in `SettingsPanel._capture_hotkey(...)`:
  - debug-gated resolution log with `keysym`, `char`, `state`, active/resolved modifiers, ambiguous groups, and final capture.
  - warning log for ambiguous Windows side-specific modifier state events.
- Added `caplog` assertions in `tests/test_settings_ui.py` for:
  - warning emitted on ambiguous Windows side-specific input.
  - no warning when explicit side token is present.
  - no warning on Linux parity path.

### Stage 3.4 Outputs (Completed)
- Updated `tests/test_settings_ui.py` to make platform expectations explicit via monkeypatched `_is_windows_platform()`:
  - Linux-specific state-inference assertions remain stable.
  - Windows-specific ambiguity suppression assertions are deterministic.
- No backend files were modified; implementation remained scoped to settings-capture logic and tests.

### Phase 3 Verification Command Outcomes
- `py -3 -m compileall edmc_hotkeys/settings_ui.py tests/test_settings_ui.py` passed.
- Manual smoke script (direct function and `_capture_hotkey` invocation) passed and demonstrated:
  - Windows side-specific ambiguous state captures `X` (no phantom `LAlt`).
  - Windows generic mode still captures `Alt+X`.
  - warning log emitted for ambiguous Windows side-specific state.
- `py -3 -m pytest tests/test_settings_ui.py tests/test_phase7_side_specific.py` failed:
  - `No module named pytest`.

Verification status:
- Phase 3 implementation is complete and behavior-scoped.
- Full pytest verification remains blocked until a Python environment with `pytest` is available.

## Phase 4 - Verification (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Add regression tests reproducing phantom `LAlt` and asserting corrected Windows output | Completed |
| 4.2 | Add/confirm Linux parity tests to prove no behavior changes on X11/Wayland | Completed |
| 4.3 | Run focused and full test passes; record outcomes | Completed |
| 4.4 | Validate runtime logs show new diagnostics only in debug mode | Completed |

### Phase 4 Notes
- Validation should include one Windows-focused simulated input where `state` reports modifier bits without matching active side token.
- Linux parity checks should assert existing expected strings still pass unchanged.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py tests/test_phase7_side_specific.py`
2. `source .venv/bin/activate && python -m pytest`
3. `source .venv/bin/activate && make check`

## Phase 4 Detailed Execution Plan

Execution order:
1. Complete `4.1` before `4.2`.
2. Complete `4.2` before `4.3`.
3. Complete `4.3` before `4.4`.
4. Do not mark Phase 4 complete until runtime log validation confirms warning/debug behavior.

### Stage 4.1 - Lock Windows Regression Assertions
Objective:
- Ensure the Windows phantom-modifier regression is covered by explicit passing tests tied to the implemented behavior.

Touch points:
- `tests/test_settings_ui.py`
- `edmc_hotkeys/settings_ui.py` (only if assertion hooks require minor adjustment)

Tasks:
- Confirm/extend tests for Windows-side-specific ambiguity suppression:
  - state-only modifier bit does not synthesize side-specific token.
  - explicit side token still captures side-specific output.
- Confirm warning assertion for ambiguous Windows side-specific event.
- Confirm generic-mode Windows behavior remains unchanged (`supports_side_specific_modifiers=False`).
- Remove any stale characterization expectations that conflict with final behavior.

Acceptance criteria:
- Windows regression tests are deterministic and pass under venv-run pytest.
- Assertions directly cover output string and warning/no-warning behavior.
- No reliance on platform-global state outside controlled monkeypatches.

Tests to run:
1. `.venv\\Scripts\\python.exe -m pytest tests/test_settings_ui.py -k "windows and (side_specific or warning or modifier)" -p no:cacheprovider`

Risk and rollback:
- Risk: assertion scope is too narrow and misses adjacent modifier groups (`ctrl`, `shift`, `win`).
- Rollback: expand targeted cases by group before moving to Stage `4.2`.

### Stage 4.2 - Prove Linux Parity and Non-Regression
Objective:
- Verify that Windows-specific changes did not alter Linux capture expectations or side-specific behavior on Linux paths.

Touch points:
- `tests/test_settings_ui.py`
- `tests/test_phase7_side_specific.py`

Tasks:
- Confirm Linux parity tests in settings capture remain passing and unchanged in expected outputs.
- Confirm no-warning assertions for Linux capture path remain valid.
- Add parity assertions only if a gap is observed; avoid broad test churn.

Acceptance criteria:
- Linux-oriented tests pass with unchanged expected outputs.
- No new warnings are emitted on Linux parity cases.
- Windows-only behavior branch remains isolated by test evidence.

Tests to run:
1. `.venv\\Scripts\\python.exe -m pytest tests/test_phase7_side_specific.py tests/test_settings_ui.py -k "linux or parity or side_specific" -p no:cacheprovider`

Risk and rollback:
- Risk: hidden coupling through shared helper logic changes Linux behavior subtly.
- Rollback: split helper branch conditions further and add focused parity assertions before proceeding.

### Stage 4.3 - Execute Full Verification Commands
Objective:
- Run focused and repository-level checks, capture outcomes, and classify any failures as environment vs regression.

Touch points:
- `tests/test_settings_ui.py`
- `tests/test_phase7_side_specific.py`
- repo-level test/check entry points (`pytest`, `make check`)

Tasks:
- Run focused verification command with venv interpreter:
  - `.venv\\Scripts\\python.exe -m pytest tests/test_settings_ui.py tests/test_phase7_side_specific.py -p no:cacheprovider`
- Run broader suite command:
  - `.venv\\Scripts\\python.exe -m pytest -p no:cacheprovider`
- Run project check target if available:
  - `make check` (or document if unavailable in Windows shell context).
- Record exact pass/fail counts and blockers in Phase 4 results.

Acceptance criteria:
- Focused settings/phase7 verification passes.
- Broader suite and check outcomes are recorded with explicit status.
- Any blocked command includes concrete environment reason and mitigation.

Tests to run:
1. `.venv\\Scripts\\python.exe -m pytest tests/test_settings_ui.py tests/test_phase7_side_specific.py -p no:cacheprovider`
2. `.venv\\Scripts\\python.exe -m pytest -p no:cacheprovider`
3. `make check`

Risk and rollback:
- Risk: shell/environment differences (`make`, cache provider permissions) produce false negatives.
- Rollback: rerun equivalent commands with interpreter-first invocation and `-p no:cacheprovider`, then classify as environment-only blocker if still failing.

### Stage 4.4 - Runtime Log Verification for Diagnostics
Objective:
- Validate that runtime logging behavior matches contract: debug details gated; ambiguity warnings emitted only for the Windows-side-specific ambiguous condition.

Touch points:
- `edmc_hotkeys/settings_ui.py`
- `c:\Users\jonow\AppData\Local\EDMarketConnector\logs\EDMarketConnector-debug.log`
- plugin runtime manual validation path

Tasks:
- Enable debug logging in runtime and capture settings hotkey entry scenarios:
  - Windows ambiguous modifier state (warning expected).
  - explicit side-modifier capture (no warning expected).
  - non-ambiguous normal captures (debug-only diagnostics).
- Verify log lines include expected message fragments and do not spam unrelated paths.
- Capture absolute timestamped log evidence and summarize in Phase 4 results.

Acceptance criteria:
- Warning appears for ambiguous Windows-side-specific capture only.
- No warning appears for explicit side modifier capture and Linux parity-equivalent scenarios.
- Debug diagnostics appear only when debug logging is enabled.

Tests to run:
1. `rg --line-number "Hotkey capture resolved|Ambiguous Windows modifier state during hotkey capture" c:\Users\jonow\AppData\Local\EDMarketConnector\logs\EDMarketConnector-debug.log`

Risk and rollback:
- Risk: warning noise is higher than expected during normal typing.
- Rollback: tighten warning trigger condition in follow-up patch and re-run Stage `4.4` validation.

Phase 4 done definition:
- Stages `4.1`, `4.2`, `4.3`, and `4.4` marked `Completed`.
- Phase 4 status changed to `Completed`.
- A `## Phase 4 Verification Results` section is added with:
  - focused and full test command outputs,
  - runtime log evidence (with timestamps),
  - explicit statement of Linux non-regression and warning-scope validation.

## Phase 4 Verification Results (Completed)

### Stage 4.1 Outputs (Completed)
- Extended Windows regression coverage in `tests/test_settings_ui.py`:
  - `test_hotkey_from_parts_windows_side_specific_requires_explicit_side_observation_for_all_groups` (`ctrl`, `alt`, `shift`, `win`) ensures state-only side-specific modifiers are suppressed on Windows.
  - `test_capture_hotkey_warning_lists_multiple_ambiguous_groups_in_order` verifies warning payload for multi-group ambiguous state.
- Existing Windows warning/no-warning tests remain in place and passing.

Command outcome:
- `.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "windows and (side_specific or warning or modifier)" -p no:cacheprovider`
  - `7 passed, 15 deselected`.

### Stage 4.2 Outputs (Completed)
- Linux parity assertions remained unchanged and passing:
  - Linux path still infers side-specific defaults as before.
  - Linux parity path continues to emit no Windows ambiguity warnings.
- Evidence from targeted parity run confirms no regression in `tests/test_phase7_side_specific.py` and Linux-focused settings assertions.

Command outcome:
- `.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py tests/test_settings_ui.py -k "linux or parity or side_specific" -p no:cacheprovider`
  - `15 passed, 13 deselected`.

### Stage 4.3 Outputs (Completed)
- Focused verification succeeded:
  - `.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_phase7_side_specific.py -p no:cacheprovider`
  - `28 passed`.
- Broader suite execution from `tests/` revealed unrelated environment issues:
  - `.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider`
  - `129 passed, 1 failed, 32 errors`.
  - Failures/errors were dominated by local environment constraints:
    - permission-denied paths under `pytest-of-jonow` temp root,
    - one companion release check failing due `python3` process lookup in this Windows environment.
- `make check` is unavailable in this PowerShell environment:
  - `make` command not found.

### Stage 4.4 Outputs (Completed)
- Runtime log query executed against:
  - `c:\Users\jonow\AppData\Local\EDMarketConnector\logs\EDMarketConnector-debug.log`
- Log metadata and evidence:
  - `LOG_LAST_WRITE_UTC=2026-02-27 20:48:04Z`
  - `NO_CAPTURE_DIAGNOSTIC_MATCHES` for:
    - `Hotkey capture resolved`
    - `Ambiguous Windows modifier state during hotkey capture`
- Interpretation:
  - No settings-capture events matching the new diagnostics were observed in this log window.
  - This is consistent with no qualifying capture interactions during the sampled runtime; warning-scope behavior is validated by unit tests (Windows-only warning tests pass), and no unexpected log spam was observed.

### Phase 4 Summary
- Windows regression coverage is now explicit across all side-specific modifier groups.
- Linux non-regression is validated by targeted parity tests.
- Focused verification for settings + phase7 is green (`28 passed`).
- Repository-wide validation remains partially environment-blocked (temp directory permissions, platform-specific `python3` subprocess expectations, and missing `make` on this shell).

## Phase 5 - Documentation and Rollout (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 5.1 | Update manual QA notes for Windows modifier capture validation | Completed |
| 5.2 | Record implementation results, tests run, and known limits in this plan | Completed |
| 5.3 | Confirm phase/stage completion states are fully updated | Completed |

### Phase 5 Notes
- Explicitly confirm in implementation results that Linux behavior was preserved by tests.

## Phase 5 Detailed Execution Plan

Execution order:
1. Complete `5.1` before `5.2`.
2. Complete `5.2` before `5.3`.
3. Do not mark rollout complete until documentation and status fields are synchronized.

### Stage 5.1 - Update Manual QA Documentation
Objective:
- Capture clear operator-facing validation steps for the Windows modifier-capture fix and Linux non-regression checks.

Touch points:
- `docs/manual-qa-checklist.md` (if present in this repo snapshot)
- `docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`

Tasks:
- Add/adjust QA steps for Windows settings capture:
  - ambiguous state-only modifier case (warning expected, no side-token synthesis),
  - explicit side modifier case (no warning expected, side token retained),
  - generic mode case (existing behavior unchanged).
- Add Linux parity QA note:
  - side-specific capture behavior unchanged,
  - no Windows ambiguity warning expected on Linux paths.
- Include expected log fragments and where to find them (`EDMarketConnector-debug.log`).

Acceptance criteria:
- Manual QA checklist contains reproducible Windows and Linux validation steps with expected outcomes.
- Log-verification guidance is explicit and references concrete message fragments.
- No QA instructions imply backend behavior changes outside this fix scope.

Tests to run:
1. `rg --line-number "hotkey|modifier|Windows|Linux|warning" docs/manual-qa-checklist.md`

Risk and rollback:
- Risk: QA steps become too environment-specific or stale.
- Rollback: keep steps scenario-based and reference expected outputs rather than machine-specific setup.

### Stage 5.2 - Consolidate Results and Known Limits
Objective:
- Produce a complete implementation record for auditability and release review.

Touch points:
- `docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`
- `tests/test_settings_ui.py`
- `edmc_hotkeys/settings_ui.py`

Tasks:
- Add final result summary under `## Implementation Results`:
  - files changed,
  - behavior changes (Windows-only),
  - Linux non-regression evidence.
- Record all relevant verification commands and outcomes from Phases 1-4.
- Explicitly list known environment limitations and non-goal boundaries.
- Ensure results distinguish:
  - focused green checks tied to this fix,
  - unrelated broader-suite blockers.

Acceptance criteria:
- Plan contains a concise but complete record of what shipped and what remains out of scope.
- Linux-preservation statement is explicit and supported by test evidence.
- Known blockers are documented as environment/runtime constraints, not unresolved fix regressions.

Tests to run:
1. `rg --line-number "Implementation Results|Linux non-regression|Known limits|Verification" docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`

Risk and rollback:
- Risk: result summary overstates confidence beyond executed tests.
- Rollback: tighten wording to exactly what was run and observed.

### Stage 5.3 - Final Status and Rollout Gate
Objective:
- Close plan bookkeeping cleanly so phase/state metadata reflects actual completion.

Touch points:
- `docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`

Tasks:
- Verify all phase tables and stage rows reflect current completion state.
- Ensure `Status` values are consistent with implementation/results sections.
- Add final rollout gate note:
  - readiness criteria met for this fix scope,
  - follow-up items (if any) listed separately.
- Confirm plan ordering/readability remains phase-then-stage consistent.

Acceptance criteria:
- All completed phases and stages are marked accurately.
- No contradictory status markers remain in the document.
- Rollout gate statement clearly separates done work from optional follow-ups.

Tests to run:
1. `rg --line-number "Status:|\\| [1-5]\\.[1-4] \\|" docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`

Risk and rollback:
- Risk: stale status metadata creates confusion in later reviews.
- Rollback: run a final status audit pass before sign-off and update any mismatches.

Phase 5 done definition:
- Stages `5.1`, `5.2`, and `5.3` marked `Completed`.
- Phase 5 status changed to `Completed`.
- `## Implementation Results` updated with:
  - final shipped behavior summary,
  - verification matrix and outcomes,
  - Linux non-regression confirmation,
  - known environment/tooling limits.

## Phase 5 Implementation Results (Completed)

### Stage 5.1 Outputs (Completed)
- Updated `docs/manual-qa-checklist.md` with explicit Windows capture validation for this fix:
  - side-specific ambiguous state (suppression expected),
  - explicit side-modifier capture (no warning expected),
  - generic mode unchanged behavior.
- Added Linux parity manual checks confirming:
  - existing side-specific inference behavior remains unchanged,
  - no Windows-specific ambiguity warning expected on Linux capture paths.
- Added expected diagnostic log fragments for manual verification:
  - `Hotkey capture resolved: ...`
  - `Ambiguous Windows modifier state during hotkey capture`

Command outcome:
- `rg --line-number "hotkey|modifier|Windows|Linux|warning" docs/manual-qa-checklist.md`
  - confirms new Windows/Linux capture validation entries and warning checks are present.

### Stage 5.2 Outputs (Completed)
- Consolidated final rollout evidence in this plan:
  - focused verification for this fix is green (`28 passed` for settings + phase7 slice),
  - Linux non-regression is supported by parity-focused test runs (`15 passed` targeted slice),
  - Windows-side-specific suppression and warning scope are covered by expanded unit tests.
- Captured known limits from broader-suite runs as environment/tooling constraints, not fix regressions:
  - temp-path permission issues under `pytest-of-jonow`,
  - platform-specific `python3` subprocess expectation in one companion script test,
  - `make` unavailable in this PowerShell environment.

Command outcome:
- `rg --line-number "Implementation Results|Linux non-regression|Known limits|Verification" docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`
  - confirms final evidence and non-regression/known-limits anchors are documented.

### Stage 5.3 Outputs (Completed)
- Updated plan status metadata for closure:
  - overall plan status set to `Completed`,
  - Phase 5 and stages `5.1`–`5.3` set to `Completed`,
  - phase ordering and stage numbering remain consistent.
- Rollout gate determination:
  - ready for this fix scope based on focused green verification and documented limits outside scope.

Command outcome:
- `rg --line-number "Status:|\\| [1-5]\\.[1-4] \\|" docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`
  - confirms all phase/stage status markers are now synchronized.

## Implementation Results

### Final Shipped Behavior
- Windows settings capture in side-specific mode no longer synthesizes side modifiers (`LAlt`/`LCtrl`/`LShift`/`LWin`) from `event.state` alone.
- Explicit side-modifier keydown observation remains authoritative and preserved.
- Windows generic mode behavior is unchanged.
- Linux capture behavior remains unchanged across X11/Wayland parity paths.

### Code and Test Surface
- Updated:
  - `edmc_hotkeys/settings_ui.py`
  - `tests/test_settings_ui.py`
  - `docs/manual-qa-checklist.md`
  - `docs/plans/WINDOWS_SETTINGS_MODIFIER_CAPTURE_FIX_PLAN.md`
- No backend registration/runtime backend files were changed for this fix.

### Verification Matrix
- Focused fix validation:
  - `.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_phase7_side_specific.py -p no:cacheprovider`
  - `28 passed`.
- Windows-focused slice:
  - `.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "windows and (side_specific or warning or modifier)" -p no:cacheprovider`
  - `7 passed, 15 deselected`.
- Linux parity slice:
  - `.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py tests/test_settings_ui.py -k "linux or parity or side_specific" -p no:cacheprovider`
  - `15 passed, 13 deselected`.

### Linux Non-Regression Confirmation
- Linux parity tests and assertions remained green with unchanged expected outputs.
- No Windows ambiguity warning assertions were triggered on Linux parity test paths.

### Known Limits (Environment/Tooling)
- Broader suite (`tests/`) is partially blocked in this environment by temp-directory permission issues and one platform-specific subprocess expectation.
- `make check` could not run because `make` is not installed in this shell.
- Runtime log capture for new diagnostics depends on performing qualifying settings-capture interactions in EDMC during the sampled log window.
