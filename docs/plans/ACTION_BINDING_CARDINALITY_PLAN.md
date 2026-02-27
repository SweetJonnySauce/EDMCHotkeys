# Action Binding Cardinality Plan

Status: Completed  
Owner: EDMC-Hotkeys  
Last Updated: 2026-02-27

## Problem Statement
Some actions should only be bound once (for example `on`/`off`), while others should support multiple bindings (for example `color` with different payloads). Current behavior treats actions as effectively single-use in settings filtering.

## Decision
- Implement Option 1: explicit action cardinality metadata.
- Default cardinality is `single`.

## Decisions (Captured 2026-02-27)
- `multi` actions require unique payloads per action (duplicate payloads are not allowed).
- If a `single` action is bound multiple times in existing data, report a validation `warning` (not an error).
- Disabled rows do not reserve `single` actions for dropdown exclusion/uniqueness checks.

## Scope
- Add cardinality metadata to action descriptors.
- Propagate metadata through settings state/UI option models.
- Update action dropdown filtering to allow reuse only for `multi` actions.
- Add validation and tests to prevent regression.

## Non-Goals
- No backend hotkey registration changes.
- No payload schema redesign.
- No changes to binding file format unless explicitly required.

## Expected Behavior
1. Actions default to `single` if cardinality is unspecified.
2. `single` actions:
   - are excluded from other enabled rows once assigned by an enabled row.
   - duplicate uses are surfaced as validation warnings.
3. `multi` actions:
   - remain available in other rows even when already assigned.
   - require payload uniqueness across enabled rows for the same action.
4. Existing plugin actions without new metadata continue working (treated as `single`).
5. Disabled rows:
   - do not reserve actions and are ignored for cardinality exclusion/uniqueness enforcement.

## Touch Points
- `edmc_hotkeys/registry.py`
- `edmc_hotkeys/settings_state.py`
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_ui.py`
- `tests/test_settings_state.py`
- `docs/manual-qa-checklist.md`

## Phase 1 - Requirements & Contract (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Define cardinality enum/field and default semantics | Completed |
| 1.2 | Define settings filtering and validation invariants | Completed |

### Phase 1 Exit Criteria
- `single` vs `multi` behavior is unambiguous.
- Backward-compat default (`single`) is explicit.
- Warning-vs-error policy and disabled-row treatment are explicitly defined.

## Phase 1 Detailed Execution Plan

Execution order:
1. Complete Stage `1.1` contract shape first.
2. Complete Stage `1.2` filtering/validation invariant mapping second.
3. Do not start Phase 2 model edits until both Phase 1 stages are `Completed`.

### Stage 1.1 - Cardinality Contract Definition (Completed)
Objective:
- Define the exact cardinality field semantics and defaulting behavior used by registry/state/UI.

Touch points:
- `docs/plans/ACTION_BINDING_CARDINALITY_PLAN.md`
- `edmc_hotkeys/registry.py` (contract target only; no code edits in this stage)
- `edmc_hotkeys/settings_state.py` (contract target only; no code edits in this stage)

Tasks:
- Define allowed values for action cardinality (`single`, `multi`) and document default `single`.
- Define backward-compat behavior when cardinality is omitted by plugin authors.
- Define canonical wording for plugin author guidance to avoid ambiguous interpretation.
- Define invariants for disabled rows (ignored for reservation/uniqueness enforcement).

Acceptance criteria:
- Cardinality values and defaults are explicit and stable.
- Existing actions without metadata have deterministic behavior (`single`).
- Disabled-row semantics are explicitly documented.

Verification command:
1. `rg -n "Decision|Decisions|Expected Behavior|single|multi|Disabled rows" docs/plans/ACTION_BINDING_CARDINALITY_PLAN.md`

Risk and rollback:
- Risk: field semantics remain ambiguous and produce conflicting implementation choices.
- Rollback: tighten contract language to input/output behavior only, then proceed.

### Stage 1.2 - Filtering + Validation Invariant Mapping (Completed)
Objective:
- Translate final contract into testable invariants for settings filtering and validation behavior.

Touch points:
- `docs/plans/ACTION_BINDING_CARDINALITY_PLAN.md`
- `tests/test_settings_ui.py` (planned assertions)
- `tests/test_settings_state.py` (planned assertions)

Tasks:
- Define filtering invariants:
  - `single`: exclude action from other enabled rows once selected by an enabled row.
  - `multi`: do not exclude action based on assignment count.
  - disabled rows do not reserve either kind.
- Define validation invariants:
  - duplicate enabled `single` action usage -> `warning`.
  - duplicate enabled `multi` with identical payload -> validation issue (warning-level unless changed later).
  - duplicate enabled `multi` with distinct payloads -> allowed.
- Map each invariant to planned test cases and expected assertion targets.

Acceptance criteria:
- Every rule in `Expected Behavior` maps to at least one planned deterministic assertion.
- Warning-level policy is explicit for duplicate `single` usage.
- Phase 2 entry gate is objective and checklist-driven.

Verification command:
1. `rg -n "Expected Behavior|Phase 1 Exit Criteria|Phase 4 Exit Criteria" docs/plans/ACTION_BINDING_CARDINALITY_PLAN.md`

Risk and rollback:
- Risk: invariant mapping misses one disabled-row or payload edge case.
- Rollback: add missing invariant/tests in this stage before model changes begin.

Phase 1 done definition:
- Stages `1.1` and `1.2` are marked `Completed`.
- Phase 1 status is set to `Completed`.
- A `Phase 1 Implementation Results` section is added with:
  - finalized contract and invariant map,
  - planned assertion inventory,
  - verification command outcomes.

## Phase 1 Implementation Results (Completed)

### Stage 1.1 Outputs (Completed)
- Cardinality contract was finalized:
  - Allowed values are `single` and `multi`.
  - Default behavior for omitted cardinality is `single` (backward compatible).
  - Disabled rows are ignored for action reservation and payload-uniqueness enforcement.
- Plugin-author contract wording is now explicit in `Decisions` + `Expected Behavior`.

### Stage 1.2 Outputs (Completed)
- Filtering invariants locked:
  - Enabled `single` assignments exclude the action from other enabled rows.
  - `multi` actions are not excluded based on assignment count.
  - Disabled rows never reserve actions.
- Validation invariants locked:
  - Duplicate enabled `single` usage is a `warning`.
  - Duplicate enabled `multi` usage with identical payload is a `warning`.
  - Duplicate enabled `multi` usage with distinct payloads is allowed.
- Deterministic assertion inventory defined for later phases:
  - model defaults: omitted cardinality resolves to `single`.
  - settings UI exclusion: `single` excluded, `multi` still selectable.
  - disabled-row behavior: does not affect exclusion/uniqueness checks.
  - validation-level behavior: duplicate `single`/duplicate `multi+same payload` -> warnings.

### Phase 1 Verification Command Outcomes
- `rg -n "Decision|Decisions|Expected Behavior|single|multi|Disabled rows" docs/plans/ACTION_BINDING_CARDINALITY_PLAN.md` passed:
  - confirms contract/default/disabled-row semantics are present in plan text.
- `rg -n "Expected Behavior|Phase 1 Exit Criteria|Phase 4 Exit Criteria" docs/plans/ACTION_BINDING_CARDINALITY_PLAN.md` passed:
  - confirms invariants and downstream test-exit expectations are explicitly mapped.

Result:
- Phase 1 exit criteria satisfied.
- Phase 2 can begin.

## Phase 2 - Data Model Plumbing (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Add cardinality field to `Action` model with default `single` | Completed |
| 2.2 | Propagate cardinality into settings action options | Completed |
| 2.3 | Keep compatibility for existing action registrations | Completed |

### Phase 2 Exit Criteria
- Action metadata exposes cardinality end-to-end.
- Existing registrations compile/run unchanged.

## Phase 2 Detailed Execution Plan

Execution order:
1. Complete Stage `2.1` (`Action` model + normalization rules) first.
2. Complete Stage `2.2` (settings option propagation) second.
3. Complete Stage `2.3` compatibility checks before moving to Phase 3 UI/validation behavior.

### Stage 2.1 - Action Model Cardinality Field (Completed)
Objective:
- Add cardinality metadata to `Action` with a safe default and deterministic normalization.

Touch points:
- `edmc_hotkeys/registry.py`

Tasks:
- Add a cardinality field to `Action` with default `single`.
- Define/implement accepted values: `single`, `multi`.
- Normalize invalid/missing cardinality values to `single` with warning logging (compat-first behavior).
- Ensure registry registration/invocation paths remain otherwise unchanged.

Acceptance criteria:
- Actions can be registered with explicit cardinality or omitted cardinality.
- Omitted cardinality resolves to `single`.
- Invalid cardinality does not break registration flow and is surfaced via warning.

Verification command:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_state.py -k "action or settings"`

Risk and rollback:
- Risk: stricter validation accidentally rejects existing third-party action registrations.
- Rollback: keep normalization-to-`single` and warning behavior; avoid hard errors for cardinality in this phase.

### Stage 2.2 - Settings Option Propagation (Completed)
Objective:
- Propagate action cardinality into settings data structures so UI logic can make cardinality-aware decisions.

Touch points:
- `edmc_hotkeys/settings_state.py`

Tasks:
- Extend `ActionOption` to include cardinality metadata.
- Populate `ActionOption` cardinality from registered actions when building settings state.
- Keep defaults aligned so old action registrations still appear as `single`.

Acceptance criteria:
- Settings state contains per-action cardinality for all action options.
- Missing/legacy action metadata in source registrations still yields `single`.

Verification command:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_state.py`

Risk and rollback:
- Risk: added dataclass field causes fixture/construction breakage in tests.
- Rollback: add safe default values at dataclass declaration and incrementally update tests.

### Stage 2.3 - Compatibility Validation (Completed)
Objective:
- Prove model plumbing changes are backward compatible before behavior changes in Phase 3.

Touch points:
- `tests/test_settings_state.py`
- `tests/test_settings_ui.py`
- `edmc_hotkeys/registry.py`
- `edmc_hotkeys/settings_state.py`

Tasks:
- Run targeted non-regression tests for settings state + UI.
- Confirm no required call-site updates for existing `Action(...)` construction paths.
- Capture any warning-level logs expected from invalid cardinality normalization behavior.

Acceptance criteria:
- Existing tests pass without requiring plugin-side cardinality updates.
- Backward compatibility objective remains satisfied.

Verification commands:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_state.py tests/test_settings_ui.py`
2. `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py`

Risk and rollback:
- Risk: hidden constructor call sites fail due to new field ordering/assumptions.
- Rollback: keep new field optional-with-default and avoid positional-argument-only migration in this phase.

Phase 2 done definition:
- Stages `2.1`, `2.2`, and `2.3` are marked `Completed`.
- Phase 2 status is set to `Completed`.
- A `Phase 2 Implementation Results` section is added with:
  - model and state changes summary,
  - compatibility notes,
  - verification command outcomes.

## Phase 2 Implementation Results (Completed)

### Stage 2.1 Outputs (Completed)
- Added explicit action cardinality metadata in [registry.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\edmc_hotkeys\registry.py):
  - `Action.cardinality` field with default `single`.
  - Cardinality constants and validation helpers (`single`/`multi`).
- Added registration-time normalization:
  - invalid cardinality values are warning-logged and normalized to `single`.
  - normalized action is stored with canonical cardinality value.

### Stage 2.2 Outputs (Completed)
- Extended settings option model in [settings_state.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\edmc_hotkeys\settings_state.py):
  - `ActionOption.cardinality` field with default `single`.
  - `SettingsState.from_document(...)` now propagates normalized action cardinality into action options.

### Stage 2.3 Outputs (Completed)
- Added compatibility-focused tests:
  - [test_action_registry.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\tests\test_action_registry.py):
    - default cardinality is `single`,
    - invalid cardinality normalizes to `single` with warning.
  - [test_settings_state.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\tests\test_settings_state.py):
    - action option cardinality defaults to `single`,
    - explicit `multi` propagation,
    - invalid cardinality normalization to `single`.
- Existing action construction call sites remained compatible (no plugin-side updates required).

### Phase 2 Verification Command Outcomes
- `.\.venv\Scripts\python.exe -m pytest tests/test_action_registry.py tests/test_settings_state.py tests/test_settings_ui.py` passed:
  - `63 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py` passed:
  - `6 passed`.
- Existing non-fatal warning remained across runs:
  - pytest cache warning for `.pytest_cache\v\cache` path collision.

Result:
- Phase 2 exit criteria satisfied.
- Phase 3 can begin.

## Phase 3 - UI + Validation Behavior (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Update action filtering logic to only exclude assigned `single` actions | Completed |
| 3.2 | Keep `multi` actions selectable across rows | Completed |
| 3.3 | Add/adjust validation for cardinality-aware expectations | Completed |

### Phase 3 Exit Criteria
- Dropdown behavior matches cardinality policy.
- No regression for existing `single`-default actions.
- `single` exclusion and `multi` payload uniqueness both ignore disabled rows.

## Phase 3 Detailed Execution Plan

Execution order:
1. Complete Stage `3.1` filtering update for `single` actions first.
2. Complete Stage `3.2` `multi` reuse behavior second.
3. Complete Stage `3.3` validation behavior last so final warnings align with UI behavior.

### Stage 3.1 - Single-Action Exclusion Logic (Completed)
Objective:
- Update settings action filtering so only enabled-row assignments of `single` actions are excluded from other rows.

Touch points:
- `edmc_hotkeys/settings_ui.py`

Tasks:
- Update assigned-action exclusion logic to consult action cardinality.
- Exclude only actions whose cardinality is `single`.
- Ignore disabled rows while computing exclusions.
- Preserve existing behavior for plugin filtering, invalid action clear, and payload clear.

Acceptance criteria:
- `single` actions selected on enabled rows are unavailable in other matching-plugin rows.
- Disabled rows do not reserve `single` actions.
- Existing non-cardinality UI behavior remains unchanged.

Verification command:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action_dropdown and single"`

Risk and rollback:
- Risk: filtering path over-excludes by ignoring row enabled state.
- Rollback: isolate exclusion to `enabled_var` + `cardinality == single` checks only.

### Stage 3.2 - Multi-Action Reuse with Payload Context (Completed)
Objective:
- Ensure `multi` actions remain selectable across rows while preparing for payload-uniqueness validation in Stage 3.3.

Touch points:
- `edmc_hotkeys/settings_ui.py`

Tasks:
- Keep `multi` actions available in action dropdowns even when already assigned.
- Ensure row add/remove and plugin/action changes recompute without suppressing `multi` actions.
- Confirm disabled-row handling stays consistent (disabled rows ignored for reservation).

Acceptance criteria:
- Assigned `multi` actions still appear in eligible rows.
- Recompute triggers preserve expected `multi` visibility.

Verification command:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action_dropdown and multi"`

Risk and rollback:
- Risk: partial filtering branch introduces inconsistent dropdown values between rows.
- Rollback: centralize exclusion decision in one helper returning reservable/non-reservable status.

### Stage 3.3 - Cardinality-Aware Validation Rules (Completed)
Objective:
- Add validation warnings aligned with the locked cardinality policy.

Touch points:
- `edmc_hotkeys/settings_state.py`

Tasks:
- Add warning for duplicate enabled `single` action usage across rows.
- Add warning for duplicate enabled `multi` action usage when payloads are identical.
- Allow duplicate enabled `multi` action usage with distinct payloads.
- Ignore disabled rows when evaluating both warning rules.

Acceptance criteria:
- Duplicate `single` usage emits warning-level `ValidationIssue`.
- Duplicate `multi` with same payload emits warning-level `ValidationIssue`.
- Duplicate `multi` with different payload emits no cardinality warning.
- Disabled rows do not trigger cardinality warnings.

Verification commands:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_state.py -k "cardinality or duplicate or payload"`
2. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py`

Risk and rollback:
- Risk: payload comparison treats semantically equivalent JSON differently.
- Rollback: canonicalize payload objects before comparison using stable JSON serialization.

Phase 3 done definition:
- Stages `3.1`, `3.2`, and `3.3` are marked `Completed`.
- Phase 3 status is set to `Completed`.
- A `Phase 3 Implementation Results` section is added with:
  - UI filtering deltas for `single`/`multi`,
  - validation warning behavior summary,
  - verification command outcomes.

## Phase 3 Implementation Results (Completed)

### Stage 3.1 Outputs (Completed)
- Updated action filtering in [settings_ui.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\edmc_hotkeys\settings_ui.py):
  - exclusion now applies only to `single` actions,
  - exclusion source rows must be enabled,
  - disabled rows are ignored for reservation.
- Added normalization usage for option cardinality in filtering decisions.

### Stage 3.2 Outputs (Completed)
- Confirmed `multi` actions remain selectable across rows even when already assigned.
- Preserved existing recompute triggers and invalid-action clear behavior.
- Updated dropdown tests in [test_settings_ui.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\tests\test_settings_ui.py):
  - disabled-row assignments do not reserve actions,
  - `multi` remains available when assigned elsewhere,
  - only `single` actions are excluded.

### Stage 3.3 Outputs (Completed)
- Added cardinality-aware validation warnings in [settings_state.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\edmc_hotkeys\settings_state.py):
  - duplicate enabled `single` action usage -> warning,
  - duplicate enabled `multi` with identical payload -> warning,
  - duplicate enabled `multi` with distinct payload -> allowed,
  - disabled rows ignored for both warning families.
- Added canonical payload-key comparison helper for stable `multi` payload uniqueness checks.
- Added validation coverage in [test_settings_state.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\tests\test_settings_state.py) for duplicate single/multi and disabled-row exceptions.

### Phase 3 Verification Command Outcomes
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action_dropdown and single"` passed:
  - `1 passed`, `34 deselected`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action_dropdown and multi"` passed:
  - `1 passed`, `34 deselected`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_state.py -k "cardinality or duplicate or payload"` passed:
  - `11 passed`, `11 deselected`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_settings_state.py` passed:
  - `57 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_action_registry.py tests/test_phase7_side_specific.py` passed:
  - `19 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_settings_state.py tests/test_phase7_side_specific.py` passed:
  - `63 passed`.
- Existing non-fatal warning remained on all runs:
  - pytest cache warning for `.pytest_cache\v\cache` path collision.

Result:
- Phase 3 exit criteria satisfied.
- Phase 4 can begin.

## Phase 4 - Tests (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Add registry/state tests for default + explicit cardinality | Completed |
| 4.2 | Add settings UI tests for `single` exclusion and `multi` reuse | Completed |
| 4.3 | Run non-regression suites | Completed |

### Phase 4 Exit Criteria
- New cardinality tests pass.
- Existing settings/hotkey tests remain green.
- Tests verify warning-level handling for duplicate `single` bindings.

## Phase 4 Detailed Execution Plan

Execution order:
1. Complete Stage `4.1` test coverage audit and registry/state backfill first.
2. Complete Stage `4.2` settings UI test matrix completion second.
3. Complete Stage `4.3` full non-regression verification last.

### Stage 4.1 - Registry/State Coverage Completion (Completed)
Objective:
- Ensure cardinality model behavior is fully covered at registry and settings-state layers.

Touch points:
- `tests/test_action_registry.py`
- `tests/test_settings_state.py`
- `edmc_hotkeys/registry.py`
- `edmc_hotkeys/settings_state.py`

Tasks:
- Audit existing cardinality tests against Phase 1/3 invariants.
- Add missing tests (if any) for:
  - default `single` cardinality behavior,
  - explicit `multi` propagation,
  - invalid-cardinality normalization + warning,
  - duplicate enabled `single` warning path.
- Confirm warning-level assertions include field + message checks.

Acceptance criteria:
- Registry/state invariants are fully asserted by deterministic tests.
- Warning-level policy for duplicate `single` usage is explicitly tested.

Verification command:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_action_registry.py tests/test_settings_state.py`

Risk and rollback:
- Risk: adding stricter assertions over-couples tests to message text details.
- Rollback: assert stable substrings/fields only, not full literal logs.

### Stage 4.2 - Settings UI Cardinality Test Matrix Completion (Completed)
Objective:
- Ensure dropdown behavior tests fully cover `single` exclusion, `multi` reuse, and disabled-row handling.

Touch points:
- `tests/test_settings_ui.py`
- `edmc_hotkeys/settings_ui.py`

Tasks:
- Audit existing action-dropdown tests against cardinality policy.
- Add/adjust missing tests (if any) for:
  - only `single` actions excluded when assigned by enabled rows,
  - `multi` actions remain selectable when already assigned,
  - disabled rows do not reserve actions,
  - no regressions in immediate action/payload clear behavior.
- Keep tests headless and deterministic through existing dummy widget/var harness.

Acceptance criteria:
- UI test matrix covers all cardinality-based filtering decisions.
- Existing non-cardinality dropdown behaviors remain covered.

Verification command:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action_dropdown or cardinality or payload"`

Risk and rollback:
- Risk: selector-based test command misses some relevant test names.
- Rollback: run full `tests/test_settings_ui.py` suite for Stage 4.2 completion gate.

### Stage 4.3 - Full Non-Regression Verification (Completed)
Objective:
- Validate that cardinality changes do not regress existing plugin behavior.

Touch points:
- `tests/test_settings_ui.py`
- `tests/test_settings_state.py`
- `tests/test_action_registry.py`
- `tests/test_phase7_side_specific.py`

Tasks:
- Run full targeted suites spanning settings UI/state, registry, and side-specific behavior.
- Record pass/fail counts and any non-fatal environment warnings.
- Confirm Phase 4 exit criteria are met with reproducible commands.

Acceptance criteria:
- All targeted suites pass.
- No regressions outside the new cardinality behavior.

Verification commands:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_action_registry.py tests/test_settings_state.py tests/test_settings_ui.py`
2. `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py`
3. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_settings_state.py tests/test_phase7_side_specific.py`

Risk and rollback:
- Risk: environment-specific pytest cache warnings obscure result interpretation.
- Rollback: treat cache warnings as non-blocking unless a behavioral test fails; report them explicitly.

Phase 4 done definition:
- Stages `4.1`, `4.2`, and `4.3` are marked `Completed`.
- Phase 4 status is set to `Completed`.
- A `Phase 4 Implementation Results` section is added with:
  - test coverage deltas,
  - command outcomes,
  - residual non-fatal warnings.

## Phase 4 Implementation Results (Completed)

### Stage 4.1 Outputs (Completed)
- Audited registry/state coverage against the cardinality contract.
- Added coverage backfills:
  - [test_action_registry.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\tests\test_action_registry.py): mixed-case cardinality normalization to `multi`.
  - [test_settings_state.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\tests\test_settings_state.py): mixed-case cardinality normalization to `multi` in `SettingsState.from_document(...)`.
- Confirmed warning-level assertions remain field/message-scoped for duplicate `single` and duplicate `multi` payload paths.

### Stage 4.2 Outputs (Completed)
- Audited settings UI matrix for cardinality filtering and disabled-row behavior.
- Added coverage backfill:
  - [test_settings_ui.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\tests\test_settings_ui.py): mixed-case `multi` cardinality still behaves as `multi` in dropdown filtering.
- Confirmed existing tests cover:
  - only `single` exclusion,
  - `multi` reuse,
  - disabled rows do not reserve,
  - action/payload clear behavior remains intact.

### Stage 4.3 Outputs (Completed)
- Executed full non-regression command set across registry, settings state/UI, and side-specific suites.
- No regressions were observed.

### Phase 4 Verification Command Outcomes
- `.\.venv\Scripts\python.exe -m pytest tests/test_action_registry.py tests/test_settings_state.py` passed:
  - `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action_dropdown or cardinality or payload"` passed:
  - `13 passed`, `23 deselected`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_action_registry.py tests/test_settings_state.py tests/test_settings_ui.py` passed:
  - `73 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py` passed:
  - `6 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_settings_state.py tests/test_phase7_side_specific.py` passed:
  - `65 passed`.
- Existing non-fatal warning remained on all runs:
  - pytest cache warning for `.pytest_cache\v\cache` path collision.

Result:
- Phase 4 exit criteria satisfied.
- Phase 5 can begin.

## Phase 5 - Docs & QA (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 5.1 | Document plugin author guidance for `single` vs `multi` | Completed |
| 5.2 | Update manual QA checklist with cardinality scenarios | Completed |
| 5.3 | Record implementation results and command outcomes | Completed |

### Phase 5 Exit Criteria
- Documentation tells plugin authors how to set cardinality.
- Manual QA includes both `single` and `multi` action scenarios.

## Phase 5 Implementation Results (Completed)

### Stage 5.1 Outputs (Completed)
- Updated plugin author guidance in [register-action-with-edmc-hotkeys.md](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\docs\register-action-with-edmc-hotkeys.md):
  - added `cardinality` to `Action(...)` API shape (`single`/`multi`, default `single`),
  - documented cardinality behavior and invalid-value normalization,
  - updated registration example to show `single` actions (`on/off/toggle`) and `multi` action (`color`),
  - added cardinality-specific examples for binding intent.

### Stage 5.2 Outputs (Completed)
- Updated manual QA scenarios in [manual-qa-checklist.md](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\docs\manual-qa-checklist.md):
  - expanded `Action Dropdown Filtering` section to cover:
    - `single` exclusion,
    - `multi` reuse,
    - disabled rows not reserving actions,
    - action/payload auto-clear behavior,
    - warning expectations for duplicate enabled `single`,
    - warning expectations for duplicate enabled `multi` with identical payload,
    - no warning for distinct `multi` payloads.

### Stage 5.3 Outputs (Completed)
- Recorded command outcomes for planned verification set.
- Marked plan and phase statuses complete for all phases 1-5.

### Phase 5 Verification Command Outcomes
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_state.py` passed:
  - `23 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py` passed:
  - `36 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py` passed:
  - `6 passed`.
- Existing non-fatal warning remained:
  - pytest cache warning for `.pytest_cache\v\cache` path collision.

Result:
- Phase 5 exit criteria satisfied.
- Action binding cardinality workstream is complete.

## Planned Test Commands
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_state.py`
2. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py`
3. `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py`
