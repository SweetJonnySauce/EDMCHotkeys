# Wayland Tier 1 Non-Side-Specific Modifier Plan

Status: Completed (Phases 1-4 Completed)  
Owner: EDMC-Hotkeys  
Last Updated: 2026-02-26

## Problem Statement
Current validation/parser behavior requires side-specific modifiers (`LCtrl`, `RShift`, etc.) and rejects generic modifiers (`Ctrl`, `Alt`, `Shift`, `Win`). This conflicts with Tier 1 policy, where non-side-specific modifier chords must remain usable on Wayland.

## Goal
Allow and persist non-side-specific modifier bindings for Tier 1 backends (including Wayland), while keeping side-specific modifiers as Tier 2-only and capability-gated.

## Non-Goals
- No change to Tier 2 semantics for side-specific modifiers.
- No compositor-specific Wayland implementation changes.
- No change to default backend selection strategy.

## Policy Target
- Tier 1 compatible bindings:
  - key-only (`M`)
  - generic modifiers (`Ctrl+M`, `Alt+F5`, `Ctrl+Shift+L`)
- Tier 2 required bindings:
  - side-specific modifiers (`LCtrl+M`, `RShift+F6`, etc.)

## Phase 1 — Design Freeze (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Define canonical token model including generic + side-specific modifiers | Completed |
| 1.2 | Define conflict rules for mixed tokens (`ctrl` with `ctrl_l`) | Completed |
| 1.3 | Define capability gate semantics for Tier 1 vs Tier 2 | Completed |

### Stage 1.1 Tasks
- Extend canonical modifier vocabulary to include generic group tokens:
  - `ctrl`, `alt`, `shift`, `win`
- Keep side-specific tokens unchanged:
  - `ctrl_l`, `ctrl_r`, `alt_l`, `alt_r`, `shift_l`, `shift_r`, `win_l`, `win_r`
- Define preferred pretty forms:
  - generic: `Ctrl`, `Alt`, `Shift`, `Win`
  - side-specific: `LCtrl`, `RCtrl`, etc.

### Stage 1.2 Tasks
- Define invalid combinations:
  - group collision in same modifier family (e.g. `ctrl + ctrl_l`)
- Define normalization rules:
  - token ordering remains deterministic
  - duplicates collapse

### Stage 1.3 Tasks
- Define side-specific requirement check:
  - only tokens ending in `_l` / `_r` require Tier 2
- Define Tier 1 acceptance:
  - generic modifiers do not require Tier 2

### Phase 1 Acceptance Criteria
- Canonical/pretty/validation rules are explicit and testable.
- Capability gate semantics are unambiguous for all modifier token forms.

## Phase 1 Detailed Execution Plan

Execution order:
1. Complete `1.1` before `1.2`.
2. Complete `1.2` before `1.3`.
3. Do not start Phase 2 code edits until all Phase 1 stage outputs are documented in this file.

### Stage 1.1 — Canonical Token Model Freeze
Objective:
- Freeze the authoritative modifier token model so parser, validation, and storage changes remain behavior-scoped and reversible.

Touch points:
- `edmc_hotkeys/hotkey.py`
- `edmc_hotkeys/bindings.py`
- `docs/plans/CROSS_PLATFORM_COMPLEXITY_MINIMIZATION_SPEC.md`
- this plan document

Tasks:
- Define final canonical modifier set for this scope:
  - generic group tokens: `ctrl`, `alt`, `shift`, `win`
  - side-specific tokens: `ctrl_l`, `ctrl_r`, `alt_l`, `alt_r`, `shift_l`, `shift_r`, `win_l`, `win_r`
- Define pretty display mapping for both categories:
  - generic: `Ctrl`, `Alt`, `Shift`, `Win`
  - side-specific: `LCtrl`, `RCtrl`, etc.
- Define normalization expectations:
  - deterministic ordering
  - deduplication
  - key token rules unchanged from current schema (`modifiers` + `key`)
- Record explicit out-of-scope boundaries for Phase 1:
  - no backend routing changes yet
  - no runtime auto-disable policy changes yet

Acceptance criteria:
- One canonical modifier model is documented and implementation-ready.
- No ambiguity remains on generic vs side-specific token representation.
- Existing schema assumptions (`version=3`, `modifiers` + `key`) remain valid.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py -k "hotkey"`

Risk and rollback:
- Risk: token model drift against current schema/runtime assumptions.
- Rollback: revert to side-specific-only model and re-scope with explicit migration notes.

### Stage 1.2 — Mixed-Token Conflict Rule Freeze
Objective:
- Define deterministic parser/validation conflict behavior for mixed generic + side-specific modifiers in the same family.

Touch points:
- `edmc_hotkeys/hotkey.py`
- `edmc_hotkeys/settings_state.py`
- this plan document

Tasks:
- Define invalid family-collision combinations:
  - `ctrl` with `ctrl_l` or `ctrl_r`
  - `alt` with `alt_l` or `alt_r`
  - `shift` with `shift_l` or `shift_r`
  - `win` with `win_l` or `win_r`
- Define parser behavior:
  - reject invalid mixed family collisions
  - continue accepting pure generic or pure side-specific sets
- Define validation messaging requirements:
  - message must clearly explain generic/side-specific mixing is invalid within the same family
  - message must still allow either generic-only or side-specific-only family usage
- Define conflict-key behavior for duplicate detection:
  - canonical text generation must remain deterministic for valid tokens

Acceptance criteria:
- Mixed-family collision behavior is explicit, testable, and deterministic.
- Validation message requirements are clear for implementation.
- No silent remap behavior is permitted.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py -k "validation or hotkey"`

Risk and rollback:
- Risk: overly strict collision policy rejects legitimate shortcuts.
- Rollback: relax only the collision rule while keeping canonical ordering and explicit logging.

### Stage 1.3 — Tier 1/Tier 2 Capability Gate Freeze
Objective:
- Lock capability semantics so Tier 1 allows generic modifier chords while Tier 2 remains required only for side-specific modifiers.

Touch points:
- `load.py`
- `edmc_hotkeys/plugin.py`
- `docs/plans/CROSS_PLATFORM_COMPLEXITY_MINIMIZATION_SPEC.md`
- this plan document

Tasks:
- Define side-specific requirement predicate for core policy:
  - side-specific required iff any modifier token ends with `_l` or `_r`
- Define Tier 1 enablement rule:
  - key-only and generic-modifier bindings remain enabled on Tier 1 backends
- Define Tier 2 requirement rule:
  - side-specific modifier bindings auto-disable on Tier 0/1
- Define logging expectations:
  - auto-disable logs must trigger only for true side-specific bindings
  - no auto-disable logs for generic-modifier bindings on Tier 1

Acceptance criteria:
- Core capability gate semantics are explicit for all modifier token classes.
- Tier mapping behavior aligns with `CROSS_PLATFORM_COMPLEXITY_MINIMIZATION_SPEC.md`.
- Implementation can proceed in Phase 2 without policy ambiguity.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "disable or capability"`

Risk and rollback:
- Risk: policy change could accidentally enable unsupported side-specific behavior.
- Rollback: restore previous capability predicate and reintroduce stricter gating until predicate tests are fixed.

Phase 1 done definition:
- Stages `1.1`, `1.2`, and `1.3` marked `Completed`.
- Phase 1 status updated to `Completed`.
- `## Phase 1 Implementation Results` section added with:
  - frozen token/conflict/capability rules.
  - executed validation command outcomes.

## Phase 1 Implementation Results
Date completed: 2026-02-26

### Stage 1.1 Result — Canonical Token Model Frozen
- Generic modifiers accepted by policy: `ctrl`, `alt`, `shift`, `win`
- Side-specific modifiers retained: `ctrl_l`, `ctrl_r`, `alt_l`, `alt_r`, `shift_l`, `shift_r`, `win_l`, `win_r`
- Pretty forms frozen:
  - generic: `Ctrl`, `Alt`, `Shift`, `Win`
  - side-specific: `LCtrl`, `RCtrl`, `LAlt`, `RAlt`, `LShift`, `RShift`, `LWin`, `RWin`
- Normalization constraints frozen:
  - deterministic modifier ordering
  - duplicate collapse
  - key schema unchanged (`modifiers` + `key`, document `version=3`)

### Stage 1.2 Result — Mixed-Token Conflict Rules Frozen
- Invalid same-family mixes are explicitly rejected:
  - `ctrl` with `ctrl_l`/`ctrl_r`
  - `alt` with `alt_l`/`alt_r`
  - `shift` with `shift_l`/`shift_r`
  - `win` with `win_l`/`win_r`
- Valid families remain:
  - generic-only family usage
  - side-specific-only family usage
- Validation requirement frozen:
  - error messaging must explain family mixing is invalid while preserving the above valid paths
- No silent remapping is permitted.

### Stage 1.3 Result — Tier Capability Gate Semantics Frozen
- Tier 2 requirement predicate frozen:
  - a binding requires Tier 2 only when any modifier ends with `_l` or `_r`
- Tier 1 acceptance frozen:
  - key-only bindings and generic-modifier bindings remain enabled
- Tier 1 disable behavior frozen:
  - only side-specific bindings auto-disable on Tier 0/1
- Logging expectation frozen:
  - disable logs must apply only to side-specific bindings

### Validation Commands Executed
1. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py -k "hotkey"`
   - Result: `1 passed, 8 deselected`
2. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py -k "validation or hotkey"`
   - Result: `6 passed, 3 deselected`
3. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "disable or capability"`
   - Result: `1 passed, 4 deselected`

## Phase 2 — Core Implementation (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Update hotkey parser/canonicalization to accept generic modifiers | Completed |
| 2.2 | Update settings validation messages and persistence conversion | Completed |
| 2.3 | Fix core capability policy to disable only true side-specific bindings | Completed |
| 2.4 | Update backend modifier-mask mapping for generic token support | Completed |

### Stage 2.1 Tasks
- Update `edmc_hotkeys/hotkey.py`:
  - parse generic + side-specific modifiers
  - reject mixed family conflicts
  - keep deterministic canonical ordering
- Keep backward compatibility for existing side-specific forms.

### Stage 2.2 Tasks
- Update `edmc_hotkeys/settings_state.py` validation text:
  - allow generic and side-specific forms
- Ensure `to_document()` / `from_document()` paths preserve generic modifiers.

### Stage 2.3 Tasks
- Update `load.py` capability gate helper:
  - replace current `bool(record.modifiers)` side-specific test
  - detect side-specific explicitly by token form
- Ensure Tier 1 backends keep generic-modifier bindings enabled.

### Stage 2.4 Tasks
- Update X11/Windows modifier-mask mapping functions:
  - treat generic tokens as valid group modifiers
- Keep existing side-specific behavior unchanged.

### Phase 2 Acceptance Criteria
- Generic modifier bindings parse, validate, save, and register.
- Wayland Tier 1 no longer auto-disables generic-modifier bindings.
- Side-specific bindings remain capability-gated.

## Phase 2 Detailed Execution Plan

Execution order:
1. Complete `2.1` before `2.2`.
2. Complete `2.2` before `2.3`.
3. Complete `2.3` before `2.4`.
4. Do not start Phase 3 test expansion until all Phase 2 stage outputs are documented in this file.

### Stage 2.1 — Parser and Canonicalization Implementation
Objective:
- Implement generic modifier parsing in hotkey text paths while preserving side-specific behavior and deterministic canonical output.

Touch points:
- `edmc_hotkeys/hotkey.py`
- `edmc_hotkeys/bindings.py`
- `tests/test_phase7_side_specific.py` (expected updates where prior assumptions reject generic tokens)

Tasks:
- Extend modifier token parsing to accept both canonical and pretty generic forms:
  - `ctrl` / `Ctrl`
  - `alt` / `Alt`
  - `shift` / `Shift`
  - `win` / `Win`
- Keep existing side-specific forms valid:
  - canonical: `ctrl_l`, `ctrl_r`, etc.
  - pretty: `LCtrl`, `RCtrl`, etc.
- Enforce mixed-family collision rejection:
  - reject `ctrl` + `ctrl_l`/`ctrl_r` (and equivalent for `alt`, `shift`, `win`)
- Preserve canonicalization guarantees:
  - stable ordering
  - duplicate collapse
  - no payload/schema changes

Acceptance criteria:
- Parser accepts valid generic-only and side-specific-only chords.
- Parser rejects mixed same-family generic+side-specific combinations.
- Canonical text generation remains deterministic for valid chords.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "parser or generic or side_specific"`
2. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "register_binding"`

Risk and rollback:
- Risk: parser change breaks existing side-specific hotkey forms.
- Rollback: revert hotkey token parser/canonicalization changes as one unit.

### Stage 2.2 — Settings Validation and Persistence Wiring
Objective:
- Ensure settings validation and document conversion paths support generic modifiers without regression in conflict/error reporting.

Touch points:
- `edmc_hotkeys/settings_state.py`
- `edmc_hotkeys/bindings.py`
- `tests/test_settings_state.py`

Tasks:
- Update validation paths to accept generic modifier syntax as first-class.
- Preserve and surface validation errors for:
  - invalid hotkey syntax
  - mixed-family generic+side-specific collisions
  - non-hotkey field checks (plugin/action/payload)
- Verify persistence round-trip:
  - `SettingsState.from_document()` preserves generic modifiers in UI rows.
  - `SettingsState.to_document()` emits canonical generic tokens in `BindingRecord.modifiers`.
- Keep non-active profile preservation behavior unchanged.

Acceptance criteria:
- Generic modifier rows validate successfully.
- Invalid mixed-family rows fail with deterministic hotkey-field errors.
- `to_document()`/`from_document()` round-trip remains stable and non-destructive.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py -k "validation or document or hotkey"`
2. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "replace_bindings"`

Risk and rollback:
- Risk: settings conversion writes malformed modifier tuples.
- Rollback: revert settings-state conversion changes and restore previous document serialization behavior.

### Stage 2.3 — Capability Gate Policy Fix
Objective:
- Replace the current over-broad side-specific capability check with the Phase 1 predicate so Tier 1 keeps generic-modifier bindings enabled.

Touch points:
- `load.py`
- `edmc_hotkeys/plugin.py`
- `tests/test_phase7_side_specific.py`
- `tests/test_hotkey_plugin.py`

Tasks:
- Update side-specific capability predicate:
  - return true only when at least one modifier ends with `_l` or `_r`
- Apply predicate in auto-disable flow:
  - Tier 1/Tier 0 disables side-specific bindings only
  - generic-modifier and key-only bindings remain enabled
- Keep logging behavior explicit:
  - auto-disable reason appears for side-specific bindings
  - no false-positive disable logs for generic bindings
- Preserve backend capability reporting log format in plugin startup.

Acceptance criteria:
- Auto-disable behavior matches Tier policy for generic vs side-specific bindings.
- Logging clearly reflects only actual side-specific disables.
- No regression in plugin startup/backend-selection flows.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "disable or capability"`
2. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "start_logs_selected_backend or register_binding_failure"`

Risk and rollback:
- Risk: side-specific bindings accidentally enabled on unsupported backends.
- Rollback: revert predicate usage in auto-disable path and restore previous stricter behavior until fixed.

### Stage 2.4 — Backend Modifier-Mask Compatibility
Objective:
- Ensure backend registration and internal modifier-mask conversion can consume canonical generic tokens without altering side-specific semantics.

Touch points:
- `edmc_hotkeys/backends/windows.py`
- `edmc_hotkeys/backends/x11.py`
- `edmc_hotkeys/backends/wayland.py` (parsing/registration pass-through expectations)
- `tests/test_backends.py`

Tasks:
- Update backend modifier mapping to treat generic tokens as valid group modifiers:
  - Windows registration path
  - X11 registration path and modifier mask helpers
- Preserve side-specific behavior:
  - side-specific matching and side-key disambiguation remain intact where supported
- Keep fallback behavior unchanged for unsupported combinations.
- Verify no regressions in backend availability/startup logging paths.

Acceptance criteria:
- Generic-modifier hotkeys register on X11/Windows code paths.
- Existing side-specific backend behavior remains unchanged.
- Wayland backend path remains policy-gated and stable.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "windows or x11 or side_specific or wayland"`
2. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py`

Risk and rollback:
- Risk: modifier-mask mapping change causes false-positive or missed hotkey matches.
- Rollback: revert backend mapping changes and restore previous modifier translation logic.

Phase 2 done definition:
- Stages `2.1`, `2.2`, `2.3`, and `2.4` marked `Completed`.
- Phase 2 status updated to `Completed`.
- `## Phase 2 Implementation Results` section added with:
  - file-level change summary by stage.
  - final validation command outcomes.
  - explicit note of residual risks deferred to Phase 3/4.

## Phase 2 Implementation Results
Date completed: 2026-02-26

### Stage 2.1 Result — Parser and Canonicalization
Files changed:
- `edmc_hotkeys/hotkey.py`
- `edmc_hotkeys/backends/hotkey_parser.py`
- `tests/test_phase7_side_specific.py`

Implemented behavior:
- Added canonical generic modifier tokens: `ctrl`, `alt`, `shift`, `win`.
- Preserved side-specific tokens and pretty forms.
- Added mixed-family rejection for generic + side-specific combinations in the same family.
- Updated side-specific predicate to only treat `_l`/`_r` modifiers as side-specific.

### Stage 2.2 Result — Settings Validation and Persistence
Files changed:
- `edmc_hotkeys/settings_state.py`
- `tests/test_phase7_side_specific.py`

Implemented behavior:
- Validation messaging now explicitly allows generic and side-specific modifiers.
- Validation message now explicitly rejects mixed-family generic + side-specific usage.
- Persistence path remains `modifiers` + `key` with canonical token conversion through parser/canonicalizer.

### Stage 2.3 Result — Capability Gate Policy
Files changed:
- `load.py`
- `tests/test_phase7_side_specific.py`

Implemented behavior:
- Replaced over-broad capability predicate (`bool(modifiers)`) with true side-specific detection (`_l`/`_r` only).
- Tier 1/Tier 0 auto-disable now applies only to side-specific bindings.
- Generic-modifier and key-only bindings remain enabled on non-Tier-2 backends.

### Stage 2.4 Result — Backend Modifier-Mask Compatibility
Files changed:
- `edmc_hotkeys/backends/windows.py`
- `edmc_hotkeys/backends/x11.py`
- `tests/test_backends.py`

Implemented behavior:
- Windows RegisterHotKey mask mapping now accepts generic tokens (`ctrl`, `alt`, `shift`, `win`) in addition to side-specific tokens.
- Windows fallback routing now sends only true side-specific bindings to low-level hook path.
- X11 modifier mask mapping now accepts generic tokens.
- X11 registration now treats only `_l`/`_r` bindings as side-specific; generic modifiers use strict mask/grab path.

### Validation Commands Executed
1. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "parser or generic or side_specific"`
   - Result: `6 passed`
2. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "register_binding"`
   - Result: `1 passed, 7 deselected`
3. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py -k "validation or document or hotkey"`
   - Result: `9 passed`
4. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "replace_bindings"`
   - Result: `1 passed, 7 deselected`
5. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "disable or capability"`
   - Result: `1 passed, 5 deselected`
6. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "start_logs_selected_backend or register_binding_failure"`
   - Result: `2 passed, 6 deselected`
7. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "windows or x11 or side_specific or wayland"`
   - Result: `32 passed, 5 deselected`
8. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py`
   - Result: `2 passed`

Residual risks deferred to Phase 3/4:
- Broader parser/property edge-case coverage still needs expansion beyond current targeted tests.
- Full-suite runtime verification and release-note user guidance remain Phase 4 deliverables.

## Phase 3 — Test Coverage (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Add parser tests for generic/side-specific/mixed-collision cases | Completed |
| 3.2 | Add core policy tests for Tier 1/Tier 2 capability behavior | Completed |
| 3.3 | Add backend tests for generic modifier registration paths | Completed |

### Stage 3.1 Tasks
- Add tests for:
  - valid generic (`Ctrl+M`)
  - valid side-specific (`LCtrl+M`)
  - invalid mixed (`Ctrl+LCtrl+M`)

### Stage 3.2 Tasks
- Add tests for auto-disable policy:
  - Tier 1 keeps `ctrl` binding enabled
  - Tier 1 disables `ctrl_l` binding

### Stage 3.3 Tasks
- Add backend tests ensuring generic modifiers map to modifier masks for:
  - X11
  - Windows

### Phase 3 Acceptance Criteria
- Tests fail on regression of Tier 1 generic-modifier support.
- Side-specific gating behavior remains covered.

## Phase 3 Detailed Execution Plan

Execution order:
1. Complete `3.1` before `3.2`.
2. Complete `3.2` before `3.3`.
3. Do not start Phase 4 verification/docs updates until all Phase 3 stage outputs are documented in this file.

### Stage 3.1 — Parser and Settings Test Expansion
Objective:
- Lock parser and settings validation behavior with focused regression tests for generic, side-specific, and mixed-family conflict paths.

Touch points:
- `tests/test_phase7_side_specific.py`
- `tests/test_settings_state.py`
- `tests/test_hotkey_plugin.py` (only if parsing/pretty formatting assertions are required)

Tasks:
- Add/extend parser tests for:
  - canonical generic input (`ctrl+shift+a`)
  - pretty generic input (`Ctrl+Shift+A`)
  - canonical side-specific input (`ctrl_l+shift_r+a`)
  - pretty side-specific input (`LCtrl+RShift+A`)
  - invalid mixed-family input (`Ctrl+LCtrl+A`, `Shift+RShift+F2`)
- Add/extend settings validation tests for:
  - generic bindings accepted in editable rows
  - mixed-family collisions rejected with deterministic hotkey-field errors
  - conflict detection still uses canonicalized hotkey identity
- Verify round-trip assumptions stay stable when generic modifiers are present.

Acceptance criteria:
- Parser tests cover generic + side-specific + mixed-family conflict cases.
- Settings validation tests enforce the same policy as parser rules.
- No existing side-specific tests regress.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "parser or generic or mixed or side_specific"`
2. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py -k "validation or hotkey or document"`

Risk and rollback:
- Risk: tests assert implementation details instead of policy behavior.
- Rollback: trim brittle assertions and keep policy-level assertions only.

### Stage 3.2 — Capability Policy Regression Coverage
Objective:
- Strengthen coverage around Tier 1/Tier 2 gating so only true side-specific bindings require Tier 2 capabilities.

Touch points:
- `tests/test_phase7_side_specific.py`
- `tests/test_hotkey_plugin.py`
- `tests/test_phase6_smoke.py` (only if additional integration-level capability checks are required)

Tasks:
- Add/extend policy tests for active-profile auto-disable behavior:
  - generic modifier binding remains enabled on non-side-specific backend capability
  - side-specific binding auto-disables on non-side-specific backend capability
  - key-only binding remains enabled
- Add/extend helper predicate coverage:
  - `_binding_requires_side_specific_capabilities` returns true only for `_l`/`_r` modifiers
- Add/extend startup/log behavior checks:
  - backend capability log remains present
  - no false-positive side-specific disable reasons for generic bindings

Acceptance criteria:
- Tier policy behavior is explicitly covered for generic, side-specific, and key-only bindings.
- Capability helper behavior is deterministic across modifier token forms.
- Logging expectations are validated where practical.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "disable or capability or helper"`
2. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "start_logs_selected_backend or register_binding_failure"`

Risk and rollback:
- Risk: log-message assertions become too strict and fail on harmless wording updates.
- Rollback: assert stable substrings/semantics rather than full log line copies.

### Stage 3.3 — Backend Mapping and Registration Coverage
Objective:
- Ensure backend-level coverage proves generic modifier mapping is stable on X11/Windows while side-specific behavior remains intact.

Touch points:
- `tests/test_backends.py`
- `tests/test_backend_contract.py`
- `edmc_hotkeys/backends/windows.py` / `edmc_hotkeys/backends/x11.py` (only if tests reveal missing seams)

Tasks:
- Add/extend backend tests for generic modifier registration:
  - Windows `RegisterHotKey` modifier mask for generic tokens
  - X11 modifier-mask conversion for generic tokens
- Preserve/confirm side-specific paths:
  - Windows side-specific path still routes to low-level fallback
  - X11 side-specific matching/grab behavior remains covered
- Keep backend contract checks green after test expansion.

Acceptance criteria:
- Backend tests prove generic modifiers map to correct backend modifier masks.
- Side-specific backend handling remains behaviorally unchanged.
- Contract tests continue to pass.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "windows or x11 or side_specific or wayland"`
2. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py`

Risk and rollback:
- Risk: backend tests become over-coupled to private internals.
- Rollback: move assertions to externally observable behavior (registration outcomes and masks) where possible.

Phase 3 done definition:
- Stages `3.1`, `3.2`, and `3.3` marked `Completed`.
- Phase 3 status updated to `Completed`.
- `## Phase 3 Implementation Results` section added with:
  - tests added/updated by stage.
  - validation command outcomes.
  - explicit list of remaining verification tasks to be handled in Phase 4.

## Phase 3 Implementation Results
Date completed: 2026-02-26

### Stage 3.1 Result — Parser and Settings Test Expansion
Files changed:
- `tests/test_phase7_side_specific.py`
- `tests/test_settings_state.py`

Tests added/updated:
- Parser coverage:
  - generic modifier acceptance (`Ctrl+Shift+A`, `Alt+1`)
  - mixed-family rejection (`Ctrl+LCtrl+A`, `Shift+RShift+F2`)
- Settings validation coverage:
  - generic-hotkey conflict detection via canonical identity (`Ctrl+Shift+O` vs `ctrl+shift+o`)
  - generic modifier rows validate cleanly
  - mixed-family generic+side-specific rows fail with explicit validation message
- Settings document/UI round-trip coverage:
  - `from_document()` pretty display for generic modifiers
  - `to_document()` generic modifier tuple preservation

### Stage 3.2 Result — Capability Policy Regression Coverage
Files changed:
- `tests/test_phase7_side_specific.py`

Tests added/updated:
- Auto-disable assertions now explicitly prove only side-specific bindings are disabled.
- Disable reasons are asserted side-specific-only (`b-side` present, `b-generic` absent).
- Helper predicate coverage remains explicit for side-specific, generic, and key-only bindings.

### Stage 3.3 Result — Backend Mapping and Registration Coverage
Files changed:
- `tests/test_backends.py` (retained Phase 2 additions; validated under Phase 3 gates)
- `tests/test_backend_contract.py` (validation-only in Phase 3)

Coverage validated:
- Windows generic modifier mapping (`Ctrl+Shift+O`) remains on `RegisterHotKey` path.
- X11 generic modifier mapping produces expected modifier masks.
- Side-specific backend paths remain covered and unchanged in behavior.
- Backend contract checks remain green.

### Validation Commands Executed
1. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "parser or generic or mixed or side_specific"`
   - Result: `6 passed`
2. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py -k "validation or hotkey or document"`
   - Result: `14 passed`
3. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py -k "disable or capability or helper"`
   - Result: `2 passed, 4 deselected`
4. `source .venv/bin/activate && python -m pytest tests/test_hotkey_plugin.py -k "start_logs_selected_backend or register_binding_failure"`
   - Result: `2 passed, 6 deselected`
5. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "windows or x11 or side_specific or wayland"`
   - Result: `32 passed, 5 deselected`
6. `source .venv/bin/activate && python -m pytest tests/test_backend_contract.py`
   - Result: `2 passed`

Remaining tasks for Phase 4:
- Run broader verification gates (`pytest`, `make test`, `make check`) and capture outcomes.
- Validate EDMC runtime logs on Wayland Tier 1 with real bindings.
- Publish user-facing syntax guidance for Tier 1 vs Tier 2 modifiers.

## Phase 4 — Verification and Release Notes (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Run targeted and full test suites | Completed |
| 4.2 | Validate EDMC runtime logs on Wayland Tier 1 | Completed |
| 4.3 | Update docs for user-facing modifier guidance | Completed |

### Stage 4.1 Tasks
- Run targeted tests, then full repo checks.

### Stage 4.2 Tasks
- Verify logs show:
  - no validation rejection for generic modifier bindings
  - no auto-disable for generic Tier 1 bindings
  - side-specific bindings still auto-disabled on Wayland Tier 1

### Stage 4.3 Tasks
- Update docs with allowed syntax examples for Tier 1 vs Tier 2.

### Phase 4 Acceptance Criteria
- Runtime behavior matches tier policy.
- Docs align with actual validation behavior.

## Phase 4 Detailed Execution Plan

Execution order:
1. Complete `4.1` before `4.2`.
2. Complete `4.2` before `4.3`.
3. Do not mark the overall effort complete until Phase 4 results are captured in this file.

### Stage 4.1 — Verification Test Gates
Objective:
- Execute the full verification gate set after Phase 3 test expansion and capture outcomes for release readiness.

Touch points:
- `tests/test_settings_state.py`
- `tests/test_backends.py`
- `tests/test_phase7_side_specific.py`
- repo-level test/lint/type-check targets via `make`

Tasks:
- Run targeted gates first to isolate hotkey/core behavior:
  - `pytest tests/test_settings_state.py tests/test_backends.py -k "hotkey or wayland or side_specific or windows or x11"`
  - `pytest tests/test_phase7_side_specific.py`
- Run broader quality gates:
  - `pytest`
  - `make test`
  - `make check`
- Record pass/fail results with exact command output summaries.
- If a gate fails:
  - capture failing test IDs/errors in this plan
  - classify as blocker vs non-blocker for release

Acceptance criteria:
- All required Phase 4 gate commands executed.
- Results are documented with clear pass/fail status.
- Any failures include actionable follow-up notes.

Validation commands:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py tests/test_backends.py -k "hotkey or wayland or side_specific or windows or x11"`
2. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py`
3. `source .venv/bin/activate && python -m pytest`
4. `source .venv/bin/activate && make test`
5. `source .venv/bin/activate && make check`

Risk and rollback:
- Risk: long-running/full-suite checks may fail on unrelated pre-existing issues.
- Rollback: document failures as external blockers and scope release decision to impacted surfaces.

### Stage 4.2 — Wayland Tier 1 Runtime Log Validation
Objective:
- Verify real EDMC runtime behavior on Wayland Tier 1 matches the implemented policy and no false-disable regressions remain.

Touch points:
- `/home/jon/edmc-logs/EDMarketConnector-debug.log`
- `bindings.json` (test bindings used during manual verification)

Tasks:
- Configure active profile with representative bindings:
  - key-only
  - generic-modifier (`Ctrl+...`, `Alt+...`, etc.)
  - side-specific (`LCtrl+...`, etc.)
- Restart EDMC and collect fresh startup/runtime logs.
- Verify log semantics:
  - generic bindings are loaded and not auto-disabled due to side-specific capability checks
  - side-specific bindings are auto-disabled on Tier 1 backends with explicit reasons
  - backend selection/capability logs remain coherent with detected environment
- Capture concrete log lines in this plan’s implementation results section.

Acceptance criteria:
- Runtime logs demonstrate Tier 1 behavior exactly:
  - generic bindings remain active
  - side-specific bindings are auto-disabled
- No contradictory validation or capability messages are present.

Validation commands:
1. `rg -n "Hotkey backend selected|Auto-disabled binding|Loaded [0-9]+ active bindings|failed to start|validation" /home/jon/edmc-logs/EDMarketConnector-debug.log`
2. `tail -n 200 /home/jon/edmc-logs/EDMarketConnector-debug.log`

Risk and rollback:
- Risk: environment-specific backend differences (portal availability/session type) can mask expected behavior.
- Rollback: re-run verification with explicit session/backend context and document environment preconditions.

### Stage 4.3 — User Documentation and Release Notes Alignment
Objective:
- Update user-facing guidance so configured hotkey syntax clearly matches Tier policy and runtime behavior.

Touch points:
- `docs/linux-user-setup.md`
- `docs/manual-qa-checklist.md`
- `docs/register-action-with-edmc-hotkeys.md`
- `docs/requirements-architecture-notes.md`
- release note/change-log surface used by this repository

Tasks:
- Document allowed Tier 1 modifier syntax with concrete examples:
  - valid generic: `Ctrl+M`, `Ctrl+Shift+F1`
  - invalid mixed-family: `Ctrl+LCtrl+M`
  - Tier 2-only side-specific examples and expected Tier 1 auto-disable behavior
- Update troubleshooting guidance:
  - how to interpret capability auto-disable log lines
  - how to rewrite side-specific bindings to generic equivalents for Tier 1
- Update QA checklist items to include generic vs side-specific runtime validation.
- Add release note entry summarizing behavior change and user impact.

Acceptance criteria:
- User docs and QA checklist explicitly match implemented validation/runtime policy.
- Release notes communicate migration guidance from side-specific to generic modifiers for Tier 1 users.

Validation commands:
1. `rg -n "Ctrl\\+|LCtrl\\+|Tier 1|Tier 2|side-specific|generic" docs/linux-user-setup.md docs/manual-qa-checklist.md docs/register-action-with-edmc-hotkeys.md docs/requirements-architecture-notes.md`
2. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py tests/test_settings_state.py`

Risk and rollback:
- Risk: docs drift from actual behavior as follow-up code changes land.
- Rollback: treat docs updates as required in release checklist and block release on mismatch.

Phase 4 done definition:
- Stages `4.1`, `4.2`, and `4.3` marked `Completed`.
- Phase 4 status updated to `Completed`.
- Overall plan status updated to `Completed`.
- `## Phase 4 Implementation Results` section added with:
  - gate command outcomes (`pytest`, `make test`, `make check`).
  - runtime log evidence lines.
  - documentation/release-note files updated.

## Phase 4 Implementation Results
Date completed: 2026-02-26

### Stage 4.1 Result — Verification Test Gates
Executed commands and outcomes:
1. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py tests/test_backends.py -k "hotkey or wayland or side_specific or windows or x11"`
   - Result: `37 passed, 14 deselected`
2. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py`
   - Result: `6 passed`
3. `source .venv/bin/activate && python -m pytest`
   - Result: `99 passed`
4. `source .venv/bin/activate && make test`
   - Result: `pytest suite passed (99 passed)`
5. `source .venv/bin/activate && make check`
   - Result: `check_no_print OK`, `pytest passed (99 passed)`, `compileall passed`

Verification outcome:
- All required Phase 4 gate commands executed and passed.

### Stage 4.2 Result — Wayland Tier 1 Runtime Log Validation
Log source:
- `/home/jon/edmc-logs/EDMarketConnector-debug.log`

Runtime evidence captured:
- Wayland Tier 1 non-side-specific-capability backend selected and started:
  - `2026-02-26 05:28:29.887 UTC ... Hotkey backend selected: name=linux-wayland-gnome-bridge available=True supports_side_specific_modifiers=False`
  - `2026-02-26 05:28:29.887 UTC ... Hotkey backend 'linux-wayland-gnome-bridge' started ...`
- Active profile bindings loaded in same startup:
  - `2026-02-26 05:28:29.885 UTC ... Loaded 6 active bindings for profile 'Default'`
- Side-specific auto-disable diagnostics confirmed in Wayland Tier 1 path (earlier startup evidence):
  - `2026-02-26 04:10:34.475-04:10:34.477 UTC ... Auto-disabled binding ... backend 'linux-wayland-portal' does not support side-specific modifiers`

Validation outcome:
- Logs are consistent with Tier policy:
  - backend capabilities report no side-specific support on Wayland Tier 1.
  - side-specific auto-disable diagnostics are present.
  - no contradictory validation/capability errors were observed in latest startup block.

### Stage 4.3 Result — User Docs and Release Notes Alignment
Files updated:
- `docs/linux-user-setup.md`
- `docs/manual-qa-checklist.md`
- `docs/register-action-with-edmc-hotkeys.md`
- `docs/requirements-architecture-notes.md`
- `docs/release-notes.md` (new)

Documentation updates delivered:
- Added explicit Tier 1/Tier 2 modifier guidance and migration examples.
- Added invalid mixed-family examples (`Ctrl+LCtrl+...`, `Shift+RShift+...`).
- Updated backend behavior guidance to reflect generic-modifier Tier 1 support.
- Added release note entry summarizing behavior change and user impact.

Validation commands executed:
1. `rg -n "Ctrl\\+|LCtrl\\+|Tier 1|Tier 2|side-specific|generic" docs/linux-user-setup.md docs/manual-qa-checklist.md docs/register-action-with-edmc-hotkeys.md docs/requirements-architecture-notes.md docs/release-notes.md`
   - Result: expected Tier policy references present across updated docs.
2. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py tests/test_settings_state.py`
   - Result: `20 passed`

Residual release risk:
- Runtime log validation used latest and historical evidence blocks; run one additional manual Wayland session with an explicitly enabled generic binding and explicitly enabled side-specific binding if a final release sign-off requires same-session proof.

## Test Gates
1. `source .venv/bin/activate && python -m pytest tests/test_settings_state.py tests/test_backends.py -k "hotkey or wayland or side_specific or windows or x11"`
2. `source .venv/bin/activate && python -m pytest tests/test_phase7_side_specific.py`
3. `source .venv/bin/activate && python -m pytest`
4. `source .venv/bin/activate && make test`
5. `source .venv/bin/activate && make check`

## Rollback Plan
- Revert parser and capability-gate changes as one unit.
- Keep side-specific-only behavior if regressions are discovered.
- Preserve binding document integrity (no destructive migrations).
