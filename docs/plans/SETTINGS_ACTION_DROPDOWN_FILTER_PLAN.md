# Settings Action Dropdown Filter Plan

Status: Completed  
Owner: EDMC-Hotkeys  
Last Updated: 2026-02-27

## Problem Statement
In the settings bindings table, each row's `Action` dropdown currently lists all actions across all plugins. This creates incorrect and noisy choices. Desired behavior:
- If no plugin is selected in a row, the `Action` dropdown should be empty.
- If a plugin is selected, show only that plugin's actions.
- Within that plugin-scoped list, hide actions already assigned by other rows.

## Scope
- Update settings UI dropdown behavior in `edmc_hotkeys/settings_ui.py`.
- Keep persistence and validation contracts unchanged unless needed to preserve selected values safely.
- Add/extend tests to lock filtering behavior and prevent regressions.

## Non-Goals
- No backend registration/dispatch changes.
- No action registry format changes.
- No binding schema changes in `bindings.json`.

## Current Baseline
- `SettingsPanel` builds one global `_action_values` list from `state.action_options`.
- Each row action combobox uses the same static list; plugin selection does not filter actions.
- UI does not currently reserve actions per plugin based on existing row usage.

## Design Goals
- Deterministic row-local action options derived from current table state.
- No hidden side effects when plugin selection changes.
- Preserve Linux/Windows runtime behavior outside settings UI.

## Decisions (Captured 2026-02-27)
- Include disabled actions in the dropdown; do not hide based on `option.enabled`.
- Match plugin names case-insensitively.
- If a row's selected action no longer qualifies after filtering, clear it immediately.
- Apply "already assigned" filtering using active-profile rows only.
- Disabled binding rows still count as assigned when filtering available actions.
- When an invalid `action_id` is cleared by filtering, clear `payload_text` in the same row.

## Proposed Behavior Contract (Final)
1. Row with empty plugin:
   - Action dropdown values are `[]`.
2. Row with plugin `P`:
   - Candidate actions are all `action_options` where `option.plugin` matches `P` case-insensitively.
3. Assigned filtering:
   - Exclude actions already selected by other rows.
   - Assignment scope is active-profile rows only.
   - Disabled rows still reserve their selected action IDs.
4. Disabled actions:
   - Keep disabled actions visible in filtered dropdown values.
5. Invalid selection handling:
   - If current `action_id` is not in the row's newly filtered action list, clear it immediately.
   - When clearing `action_id` this way, also clear `payload_text`.
6. Recompute triggers:
   - When any row's plugin changes.
   - When any row's action changes.
   - When row is added/removed.

## Touch Points
- `edmc_hotkeys/settings_ui.py`
- `tests/test_settings_ui.py`
- `docs/manual-qa-checklist.md` (if manual verification steps need updates)

## Phase 1 - Requirements Lock (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Confirm behavior decisions from open questions | Completed |
| 1.2 | Freeze acceptance criteria and invariants | Completed |

### Phase 1 Exit Criteria
- Behavior contract remains stable and final.
- Acceptance criteria mapped to concrete test assertions.

### Phase 1 Notes
- Open-question decisions are resolved and recorded in the `Decisions` section.
- Remaining Phase 1 work is to map each final behavior rule to explicit tests/assertions.

## Phase 1 Detailed Execution Plan

Execution order:
1. Keep Stage `1.1` as completed baseline.
2. Complete Stage `1.2` acceptance mapping before starting any Phase 2 UI edits.

### Stage 1.1 - Decision Lock (Completed)
Objective:
- Freeze product decisions so implementation cannot drift.

Tasks:
- Record final behavior decisions for plugin matching, disabled-action visibility, assignment scope, and immediate clearing behavior.
- Remove unresolved decision points from this plan.

Acceptance criteria:
- Decisions are explicitly listed in one section.
- No open decision questions remain for this feature.

Verification command:
1. `rg -n "Decisions|Open Questions" docs/plans/SETTINGS_ACTION_DROPDOWN_FILTER_PLAN.md`

### Stage 1.2 - Acceptance Criteria and Invariant Mapping (Completed)
Objective:
- Translate the final behavior contract into concrete, testable assertions before implementation.

Touch points:
- `docs/plans/SETTINGS_ACTION_DROPDOWN_FILTER_PLAN.md`
- `tests/test_settings_ui.py`

Tasks:
- Define assertion targets for each behavior rule:
  - empty plugin -> empty action dropdown.
  - selected plugin -> only case-insensitive plugin matches.
  - assigned-action exclusion across active-profile rows (including disabled rows).
  - immediate clearing of invalid `action_id` and `payload_text`.
  - recompute triggers for plugin/action edits and row add/remove.
- Define expected behavior for existing rows on first panel render so tests can lock initial-state filtering.
- List the exact test names or `-k` selectors to be used in Phase 3.

Acceptance criteria:
- Each rule in `Proposed Behavior Contract (Final)` maps to at least one deterministic test assertion.
- Phase 2 entry gate is explicit: no UI code edits before mapping is complete.

Verification commands:
1. `py -3 -m pytest tests/test_settings_ui.py -k "settings or action or plugin"`
2. `py -3 -m pytest tests/test_settings_state.py`

Risk and rollback:
- Risk: acceptance mapping misses a recompute edge case and allows partial behavior.
- Rollback: add missing assertion targets in this phase before any Phase 2 implementation starts.

Phase 1 done definition:
- Stages `1.1` and `1.2` are marked `Completed`.
- Phase 1 status is set to `Completed`.
- A `Phase 1 Implementation Results` subsection is added with assertion map and command outcomes.

## Phase 1 Implementation Results (Completed)

### Stage 1.1 Outputs (Completed)
- Product decisions were finalized and documented under `Decisions (Captured 2026-02-27)`.
- No unresolved behavior questions remain for this feature.

### Stage 1.2 Outputs (Completed)
- Acceptance criteria were mapped to deterministic assertion targets for Phase 3 tests:

| Final Rule | Assertion Target | Planned Test Target |
| --- | --- | --- |
| Empty plugin shows no actions | For row plugin=`""`, action combobox `values=()` | `test_action_dropdown_empty_when_plugin_unset` |
| Plugin filter is case-insensitive | Plugin `Alpha` row can select actions from option plugin `alpha` and vice versa | `test_action_dropdown_filters_case_insensitive_plugin_match` |
| Exclude assigned actions from other rows | Row B cannot choose action selected by Row A when both resolve to same plugin | `test_action_dropdown_excludes_actions_assigned_in_other_rows` |
| Disabled rows still reserve actions | Action selected in a disabled row is still excluded in other rows | `test_action_dropdown_excludes_actions_assigned_by_disabled_rows` |
| Disabled actions remain visible | Filtered candidate list includes `option.enabled=False` entries (unless excluded by assignment rule) | `test_action_dropdown_includes_disabled_actions` |
| Invalid action clears immediately | If plugin/action change makes current action ineligible, row action is set to empty immediately | `test_action_clears_immediately_when_becomes_ineligible` |
| Payload clears with invalid action clear | When invalid action is cleared, `payload_text` is also cleared immediately | `test_payload_clears_when_action_is_auto_cleared` |
| Recompute on plugin/action/add/remove | Combobox values refresh on each trigger path | `test_action_dropdown_recomputes_on_plugin_change`, `test_action_dropdown_recomputes_on_action_change`, `test_action_dropdown_recomputes_on_row_add_remove` |
| Initial render filtered | Preloaded rows render with already-filtered action values (not global list) | `test_action_dropdown_initial_render_applies_filtering` |

- Coverage gap documented: current `tests/test_settings_ui.py` has hotkey-capture coverage but no action-dropdown filtering tests yet; these planned tests will be added in Phase 3.

### Phase 1 Verification Command Outcomes
- `py -3 -m pytest tests/test_settings_ui.py -k "settings or action or plugin"` failed:
  - `No module named pytest` in the global `py -3` interpreter.
- `py -3 -m pytest tests/test_settings_state.py` failed:
  - `No module named pytest` in the global `py -3` interpreter.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "settings or action or plugin"` passed:
  - `22 passed` (plus one pytest cache warning: existing `.pytest_cache/v/cache` path collision).
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_state.py` passed:
  - `14 passed` (same pytest cache warning).

Result:
- Phase 1 exit criteria satisfied.
- Phase 2 can start.

## Phase 2 - UI Refactor (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Introduce per-row plugin/action widget references needed for refresh | Completed |
| 2.2 | Implement row-scoped action option computation | Completed |
| 2.3 | Wire recompute on plugin/action edits and row add/remove | Completed |

### Phase 2 Exit Criteria
- Action dropdown is empty when plugin is empty.
- Plugin selection limits action values to that plugin.
- Already-assigned actions are excluded using active-profile rows.
- Disabled rows still count toward assigned-action exclusion.
- Invalid row action selections are cleared immediately when they become ineligible.
- Clearing invalid row action selections also clears payload text.

## Phase 2 Detailed Execution Plan

Execution order:
1. Complete Stage `2.1` before introducing filtering logic in `2.2`.
2. Complete Stage `2.2` before wiring all refresh triggers in `2.3`.
3. Keep behavior changes confined to settings UI; do not change persistence/validation schema.

### Stage 2.1 - Establish Row Widget Seams (Completed)
Objective:
- Create explicit per-row access to plugin/action/payload combobox/entry widgets so option refresh and field clearing are deterministic.

Touch points:
- `edmc_hotkeys/settings_ui.py`

Tasks:
- Extend row widget bookkeeping to store direct references for:
  - plugin combobox,
  - action combobox,
  - payload entry (or payload variable if sufficient).
- Add internal helper seam for row-level action option refresh (no filtering behavior change yet).
- Ensure changes are backward-compatible with existing row add/remove and `get_rows()`.

Acceptance criteria:
- Row bookkeeping includes required widget references without breaking current UI rendering.
- Existing behavior remains unchanged before Stage `2.2` filter logic is activated.

Verification command:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py`

Risk and rollback:
- Risk: row widget tuple/index coupling causes regressions in remove/reposition logic.
- Rollback: preserve existing tuple ordering and add named references alongside it.

### Stage 2.2 - Implement Filtered Action Option Resolution (Completed)
Objective:
- Implement deterministic computation of each row's action dropdown values from plugin selection and row assignments.

Touch points:
- `edmc_hotkeys/settings_ui.py`

Tasks:
- Add helper(s) to compute filtered action IDs for a target row using final contract rules:
  - empty plugin -> empty list,
  - case-insensitive plugin match,
  - disabled actions included,
  - exclude action IDs selected by other active-profile rows,
  - include disabled rows in assignment exclusion.
- Add helper to apply computed values to a row's action combobox.
- Implement immediate invalid-selection cleanup:
  - clear `action_id` if not in filtered values,
  - clear `payload_text` in the same row when action is auto-cleared.

Acceptance criteria:
- Computed dropdown values match all contract rules for plugin filter and assignment exclusion.
- Ineligible row action selections are cleared immediately with payload text.

Verification command:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action or plugin"`

Risk and rollback:
- Risk: filtering may over-exclude due to stale state reads during in-progress edits.
- Rollback: recompute from current `StringVar` values each refresh, avoid cached assignment sets.

### Stage 2.3 - Wire Recompute Triggers and Lifecycle Hooks (Completed)
Objective:
- Ensure filtered dropdown state stays correct after all row lifecycle events.

Touch points:
- `edmc_hotkeys/settings_ui.py`

Tasks:
- Trigger full/targeted action option refresh when:
  - plugin value changes,
  - action value changes,
  - row is added,
  - row is removed.
- Apply initial refresh after panel row construction so preloaded rows are filtered on first render.
- Ensure refresh path does not interfere with hotkey capture logic or validation display.

Acceptance criteria:
- Recompute triggers fire on all defined paths.
- Initial render uses filtered options (no transient global action list exposure).

Verification commands:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action or plugin or settings"`
2. `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py`

Risk and rollback:
- Risk: variable trace callbacks can recurse or trigger redundant refresh loops.
- Rollback: add reentrancy guard scoped to dropdown-refresh path.

Phase 2 done definition:
- Stages `2.1`, `2.2`, and `2.3` are marked `Completed`.
- Phase 2 status is set to `Completed`.
- A `Phase 2 Implementation Results` subsection is added with:
  - code touch summary,
  - trigger coverage summary,
  - command outcomes.

## Phase 2 Implementation Results (Completed)

### Stage 2.1 Outputs (Completed)
- Extended `_RowWidgets` to keep direct references to:
  - `plugin_combo`,
  - `action_combo`,
  - `payload_entry`.
- Added `SettingsPanel` reentrancy guard state for action-option refresh flow:
  - `_refreshing_action_options`.

### Stage 2.2 Outputs (Completed)
- Implemented row-scoped action filtering helpers in `settings_ui.py`:
  - `_filtered_action_values(...)`,
  - `_assigned_actions_from_other_rows(...)`,
  - `_set_combobox_values(...)`,
  - `_refresh_row_action_options(...)`.
- Implemented final filter rules:
  - empty plugin -> empty action list,
  - case-insensitive plugin match,
  - include disabled actions (no enabled-state filtering),
  - exclude actions assigned in other active-profile rows (including disabled rows).
- Implemented immediate invalid selection cleanup:
  - clear `action_id` when it becomes ineligible,
  - clear `payload_text` at the same time.

### Stage 2.3 Outputs (Completed)
- Wired action-option recompute to all required lifecycle/interaction triggers:
  - plugin `StringVar` write trace,
  - action `StringVar` write trace,
  - row add,
  - row remove.
- Added `_refresh_all_action_options(...)` guard to prevent recursive refresh loops during auto-clear.
- Initial row render now refreshes filtered action values immediately after each row is added.

### Phase 2 Verification Command Outcomes
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_settings_state.py` passed:
  - `36 passed` (with existing non-fatal pytest cache warning for `.pytest_cache\v\cache` path collision).
- `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py` passed:
  - `6 passed` (same non-fatal pytest cache warning).

Result:
- Phase 2 exit criteria satisfied.
- Phase 3 (tests specific to action-dropdown filtering behavior) is ready to begin.

## Phase 3 - Tests (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Add deterministic unit tests for option filtering logic | Completed |
| 3.2 | Add panel-level tests for refresh triggers (plugin/action change, add/remove) | Completed |
| 3.3 | Verify no regression in existing hotkey capture tests | Completed |

### Phase 3 Exit Criteria
- New tests pass for all accepted behavior rules.
- Existing settings/hotkey tests continue to pass.

## Phase 3 Detailed Execution Plan

Execution order:
1. Implement Stage `3.1` deterministic filtering tests first.
2. Implement Stage `3.2` trigger/lifecycle tests second.
3. Run Stage `3.3` regression verification after new tests are in place.

### Stage 3.1 - Deterministic Filtering Tests (Completed)
Objective:
- Add focused tests that prove action-value filtering behavior independent of platform/backend runtime paths.

Touch points:
- `tests/test_settings_ui.py`

Tasks:
- Add tests for rule coverage mapped in Phase 1:
  - empty plugin -> empty action list,
  - case-insensitive plugin filtering,
  - assigned-action exclusion from other rows,
  - disabled-row assignment exclusion,
  - disabled actions remain visible when otherwise eligible.
- Keep tests deterministic and headless by using panel helpers/row variables rather than real Tk event loops where possible.

Proposed test additions:
- `test_action_dropdown_empty_when_plugin_unset`
- `test_action_dropdown_filters_case_insensitive_plugin_match`
- `test_action_dropdown_excludes_actions_assigned_in_other_rows`
- `test_action_dropdown_excludes_actions_assigned_by_disabled_rows`
- `test_action_dropdown_includes_disabled_actions`

Acceptance criteria:
- Each filtering rule has at least one passing test.
- No test depends on backend-specific hotkey infrastructure.

Verification command:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action_dropdown and (empty or case_insensitive or excludes or disabled)"`

Risk and rollback:
- Risk: tests become brittle due to direct widget implementation assumptions.
- Rollback: assert against row variables and combobox `values` contracts only.

### Stage 3.2 - Trigger and Auto-Clear Tests (Completed)
Objective:
- Prove filtered action values recompute on all expected lifecycle paths and invalid selections clear immediately with payload text.

Touch points:
- `tests/test_settings_ui.py`

Tasks:
- Add panel-level tests for trigger paths:
  - plugin change triggers recompute,
  - action change in one row updates eligible actions in other rows,
  - add/remove row triggers recompute.
- Add tests for immediate invalid-clear behavior:
  - action clears when ineligible,
  - payload text clears together with action.
- Add initial-render test proving preloaded rows are filtered on construction.

Proposed test additions:
- `test_action_dropdown_recomputes_on_plugin_change`
- `test_action_dropdown_recomputes_on_action_change`
- `test_action_dropdown_recomputes_on_row_add_remove`
- `test_action_clears_immediately_when_becomes_ineligible`
- `test_payload_clears_when_action_is_auto_cleared`
- `test_action_dropdown_initial_render_applies_filtering`

Acceptance criteria:
- All trigger paths produce the expected updated combobox values.
- Auto-clear behavior is deterministic and immediate.

Verification command:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action_dropdown and (recompute or clears or initial_render)"`

Risk and rollback:
- Risk: trace callback timing differences make tests flaky.
- Rollback: call refresh helpers directly after variable updates in tests to avoid timing sensitivity.

### Stage 3.3 - Non-Regression Verification (Completed)
Objective:
- Confirm existing settings/hotkey behavior remains intact after new test additions.

Touch points:
- `tests/test_settings_ui.py`
- `tests/test_settings_state.py`
- `tests/test_phase7_side_specific.py`

Tasks:
- Run full targeted suites used in prior phases.
- Confirm no regressions in hotkey capture and side-specific behavior tests.
- Record any non-fatal environment warnings separately from pass/fail results.

Acceptance criteria:
- All targeted suites pass.
- No new failures introduced outside action-dropdown coverage.

Verification commands:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_settings_state.py`
2. `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py`

Risk and rollback:
- Risk: unrelated existing environment warnings obscure outcomes.
- Rollback: keep reporting explicit pass/fail counts and note warnings as non-blocking unless behavior-impacting.

Phase 3 done definition:
- Stages `3.1`, `3.2`, and `3.3` are marked `Completed`.
- Phase 3 status is set to `Completed`.
- A `Phase 3 Implementation Results` subsection is added with:
  - tests added/updated,
  - assertion coverage summary,
  - command outcomes.

## Phase 3 Implementation Results (Completed)

### Stage 3.1 Outputs (Completed)
- Added deterministic filtering tests in [test_settings_ui.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\tests\test_settings_ui.py):
  - `test_action_dropdown_empty_when_plugin_unset`
  - `test_action_dropdown_filters_case_insensitive_plugin_match`
  - `test_action_dropdown_excludes_actions_assigned_in_other_rows`
  - `test_action_dropdown_excludes_actions_assigned_by_disabled_rows`
  - `test_action_dropdown_includes_disabled_actions`
- Added test-only harness helpers for headless dropdown assertions:
  - `_DummyStringVar`, `_DummyCombo`, `_action_option`, `_row_for_dropdown`, `_build_dropdown_panel`.

### Stage 3.2 Outputs (Completed)
- Added trigger and auto-clear tests in [test_settings_ui.py](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\tests\test_settings_ui.py):
  - `test_action_clears_immediately_when_becomes_ineligible`
  - `test_payload_clears_when_action_is_auto_cleared`
  - `test_action_dropdown_recomputes_on_plugin_change`
  - `test_action_dropdown_recomputes_on_action_change`
  - `test_action_dropdown_recomputes_on_row_add_remove`
  - `test_action_dropdown_initial_render_applies_filtering`

### Stage 3.3 Outputs (Completed)
- Re-ran existing settings/hotkey and side-specific suites after adding dropdown tests.
- Confirmed no regressions outside the new action-dropdown coverage.

### Phase 3 Verification Command Outcomes
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action_dropdown and (empty or case_insensitive or excludes or disabled)"` passed:
  - `5 passed`, `28 deselected`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py -k "action_dropdown and (recompute or clears or initial_render)"` passed:
  - `4 passed`, `29 deselected`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_settings_state.py` passed:
  - `47 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py` passed:
  - `6 passed`.
- All runs showed the existing non-fatal pytest cache warning for `.pytest_cache\v\cache` path collision.

Result:
- Phase 3 exit criteria satisfied.
- Phase 4 can begin.

## Phase 4 - Manual QA + Documentation (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Add manual checklist steps for action dropdown filtering | Completed |
| 4.2 | Record implementation results and command outcomes | Completed |

### Phase 4 Exit Criteria
- `docs/manual-qa-checklist.md` includes verification steps for plugin-scoped action dropdown behavior.
- Plan doc includes implementation results with test command outcomes.

## Phase 4 Detailed Execution Plan

Execution order:
1. Complete Stage `4.1` checklist updates first.
2. Complete Stage `4.2` documentation/results capture second.
3. Keep this phase documentation-only unless manual QA finds a regression.

### Stage 4.1 - Manual QA Checklist Update (Completed)
Objective:
- Add clear operator-facing manual checks for the new action-dropdown behavior in settings UI.

Touch points:
- `docs/manual-qa-checklist.md`

Tasks:
- Add Windows/Linux-neutral checklist steps under settings/manual verification to confirm:
  - empty plugin shows no actions,
  - selected plugin shows only matching plugin actions (case-insensitive),
  - actions already assigned in other rows are excluded (including disabled rows),
  - changing plugin/action triggers immediate dropdown recompute,
  - ineligible action auto-clears and payload clears with it.
- Add pass/fail criteria lines for these checks.
- Keep checklist wording specific to observed UI behavior and avoid implementation details.

Acceptance criteria:
- Checklist covers every rule from `Proposed Behavior Contract (Final)`.
- Checklist steps are executable by a tester without reading source code.

Verification command:
1. `rg -n "action dropdown|plugin|assigned|payload" docs/manual-qa-checklist.md`

Risk and rollback:
- Risk: checklist misses one contract rule and leaves a manual gap.
- Rollback: map checklist bullets line-by-line to contract rules before marking complete.

### Stage 4.2 - Final Documentation and Closure (Completed)
Objective:
- Capture final implementation status, command outcomes, and closure notes for the feature.

Touch points:
- `docs/plans/SETTINGS_ACTION_DROPDOWN_FILTER_PLAN.md`

Tasks:
- Mark Phase 4 stages and phase status as `Completed` when done.
- Add `Phase 4 Implementation Results` section with:
  - checklist updates summary,
  - test command outcomes from Phase 3 verification set,
  - residual environment warnings (if any) explicitly marked non-fatal.
- Add final rollout note indicating feature readiness for manual QA signoff.

Acceptance criteria:
- Plan file contains complete closure record for all phases 1-4.
- Command outcomes are explicit and reproducible.

Verification commands:
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_settings_state.py tests/test_phase7_side_specific.py`
2. `rg -n "Phase 4 Implementation Results|Status: Completed" docs/plans/SETTINGS_ACTION_DROPDOWN_FILTER_PLAN.md`

Risk and rollback:
- Risk: documentation summary drifts from actual executed commands.
- Rollback: copy command outputs directly from terminal history into result bullets.

Phase 4 done definition:
- Stages `4.1` and `4.2` are marked `Completed`.
- Phase 4 status is set to `Completed`.
- Plan contains `Phase 4 Implementation Results` with checklist delta and verification outcomes.

## Phase 4 Implementation Results (Completed)

### Stage 4.1 Outputs (Completed)
- Updated [manual-qa-checklist.md](c:\Users\jonow\AppData\Local\EDMarketConnector\plugins\EDMC-Hotkeys\docs\manual-qa-checklist.md) with a new `Action Dropdown Filtering` subsection.
- Added explicit manual checks for:
  - empty-plugin rows showing empty action lists,
  - case-insensitive plugin filtering,
  - assigned-action exclusion (including disabled rows),
  - recompute behavior on plugin/action/row changes,
  - immediate action + payload clearing when action becomes ineligible.
- Added pass/fail criteria for this subsection.

### Stage 4.2 Outputs (Completed)
- Closed Phase 4 stage/phase status markers.
- Recorded verification command outcomes and residual environment warnings.
- Finalized rollout note for manual QA signoff readiness.

### Phase 4 Verification Command Outcomes
- `rg -n "action dropdown|plugin|assigned|payload" docs/manual-qa-checklist.md` passed:
  - matched new action-dropdown checklist lines and pass/fail criteria entries.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_settings_state.py tests/test_phase7_side_specific.py` passed:
  - `53 passed`.
  - existing non-fatal pytest cache warning remained for `.pytest_cache\v\cache` path collision.

Result:
- Phase 4 exit criteria satisfied.
- Plan is fully complete across Phases 1-4 and ready for manual QA signoff.

## Planned Test Commands
1. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py`
2. `.\.venv\Scripts\python.exe -m pytest tests/test_settings_state.py`
3. `.\.venv\Scripts\python.exe -m pytest tests/test_phase7_side_specific.py`
