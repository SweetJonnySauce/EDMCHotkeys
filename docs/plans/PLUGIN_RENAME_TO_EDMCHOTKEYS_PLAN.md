# Plugin Rename Plan (`EDMC-Hotkeys` -> `EDMCHotkeys`)

Status: Draft  
Owner: EDMC-Hotkeys  
Last Updated: 2026-02-28

## Problem Statement
Current plugin folder/name `EDMC-Hotkeys` uses a hyphen, which is not a valid Python import identifier for normal `from ... import ...` usage. This conflicts with EDMC guidance that plugin names should be valid for importlib/module import patterns and complicates cross-plugin API imports.

## Goal
Rename the plugin distribution/import surface to `EDMCHotkeys` so other plugins can use standard Python import patterns while preserving runtime behavior.

## Scope
- Rename plugin folder/import package surface from `EDMC-Hotkeys` to `EDMCHotkeys`.
- Change runtime/plugin-facing name (`plugin_name`) to `EDMCHotkeys`.
- Preserve existing runtime behavior (hotkeys, settings, bindings persistence, backend selection).
- Do not provide legacy import compatibility for `EDMC-Hotkeys.load`.
- Do not migrate local user binding data from old folder to new folder; only update repository-controlled files as needed.
- Update docs and migration guidance for dependent plugins.

## Non-Goals
- No hotkey backend behavior changes.
- No schema redesign for `bindings.json`.
- No action registry semantic changes.
- No UI redesign beyond rename-related text/labels.
- No internal package rename (`edmc_hotkeys` stays unchanged).

## Constraints
- Maintain EDMC plugin lifecycle hooks (`plugin_start3`, `plugin_stop`, prefs hooks) unchanged in behavior.
- Avoid introducing duplicate plugin loading in EDMC.
- Keep rollback simple (revert to previous folder/import path if needed).

## Rename Strategy (Hard Change)
1. Introduce `EDMCHotkeys` as the canonical plugin package/folder.
2. Change plugin runtime name/label surface to `EDMCHotkeys`.
3. Keep internal package imports under `edmc_hotkeys` unchanged.
4. Remove any references to legacy import path `EDMC-Hotkeys.load` in project docs/examples.
5. Update docs/examples to use direct `import` syntax with `EDMCHotkeys` (not `importlib.import_module(...)`).
6. Keep runtime API symbols stable (`register_action`, `list_actions`, `list_bindings`, etc.) under `EDMCHotkeys`.
7. Publish migration instructions for downstream plugins.

## Decisions (Captured 2026-02-28)
- This rename is an immediate hard change (no compatibility alias, no deprecation window).
- Legacy `EDMC-Hotkeys.load` import paths will not be supported.
- Documentation should use direct import style with the new name (for example `import EDMCHotkeys as hotkeys`), not `importlib` loading.
- `plugin_name` should be changed to `EDMCHotkeys`.
- Local user bindings migration is out of scope (no old->new folder data migration).
- Internal package/module path remains `edmc_hotkeys`.
- Documentation files that embed old naming should be renamed as part of this work.
- Release notes/docs must explicitly call out the rename as a pre-release breaking integration change.

## Risks
- Existing plugins hardcoded to `importlib.import_module("EDMC-Hotkeys.load")` will fail until updated.
- Packaging/release scripts may still assume old folder name.
- User installations may accidentally keep both old and new folders, causing duplicate/undefined behavior.

## Rollback Plan
- Revert folder/import changes and docs to `EDMC-Hotkeys`.
- Rebuild release artifacts using old plugin path.
- Keep binding/config files unchanged to avoid data migration rollback complexity.

## Touch Points (Expected)
- Plugin root folder name and plugin metadata references.
- `load.py` (`plugin_name` constant) and root `__init__.py` import facade behavior.
- Documentation:
  - `README.md`
  - `docs/register-action-with-edmc-hotkeys.md` (rename planned)
  - any plan/docs referencing `EDMC-Hotkeys.load`.
- CI/release scripts that package plugin folder names.

## Phase 1 - Contract and Migration Design (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Finalize canonical new name and import contract (`EDMCHotkeys`) | Completed |
| 1.2 | Lock hard-change policy (no legacy alias/deprecation window) | Completed |
| 1.3 | Define acceptance criteria and rollback triggers | Completed |

### Phase 1 Exit Criteria
- New canonical import path and plugin display name are explicitly documented.
- Hard-change behavior is explicitly defined (legacy path unsupported).
- Success/failure criteria are testable.

## Phase 1 Detailed Execution Plan

Execution order:
1. Complete Stage `1.1` contract finalization first.
2. Confirm Stage `1.2` decision lock remains unchanged.
3. Complete Stage `1.3` acceptance and rollback criteria mapping.
4. Do not start Phase 2 inventory work until all Phase 1 stages are marked `Completed`.

### Stage 1.1 - Canonical Contract Finalization (Completed)
Objective:
- Lock the canonical runtime/import identity so implementation work cannot drift.

Touch points:
- `docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md`
- `README.md` (contract target; no implementation edits in this stage)
- `docs/register-action-with-edmc-hotkeys.md` (contract target; no implementation edits in this stage)

Tasks:
- Define canonical plugin-facing name as `EDMCHotkeys` (including `plugin_name`).
- Define canonical consumer import style as direct Python import (no `importlib` examples for the new name).
- Define internal package invariants: `edmc_hotkeys` remains unchanged.
- Define hard-break expectation for legacy `EDMC-Hotkeys.load` imports.

Acceptance criteria:
- Contract statements in this plan are explicit and non-ambiguous.
- Import style for docs/examples is explicitly direct import only.
- Internal package boundary (`edmc_hotkeys`) is explicitly preserved.

Verification commands:
1. `rg -n "EDMCHotkeys|plugin_name|direct import|edmc_hotkeys|legacy" docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md`

Risk and rollback:
- Risk: ambiguous naming/import wording leads to partial or conflicting implementation.
- Rollback: tighten wording in this stage before any rename edits begin.

### Stage 1.2 - Hard-Change Decision Lock (Completed)
Objective:
- Preserve the resolved policy: no compatibility alias, no deprecation window.

Touch points:
- `docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md`

Tasks:
- Keep decision language aligned with hard-change scope.
- Ensure no later section reintroduces alias/deprecation behavior.

Acceptance criteria:
- Plan contains no compatibility shim requirement.
- Decision section and phase stages are consistent with hard-change behavior.

Verification commands:
1. `rg -n "compatibility|alias|deprecation|hard change|legacy" docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md`

Risk and rollback:
- Risk: accidental reintroduction of compatibility requirements in later phase text.
- Rollback: normalize all conflicting lines back to the locked decision before Phase 2 begins.

### Stage 1.3 - Acceptance Criteria and Rollback Trigger Definition (Completed)
Objective:
- Convert rename objectives into concrete, testable Phase 2/3 entry gates and rollback triggers.

Touch points:
- `docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md`

Tasks:
- Define measurable acceptance checks for:
  - folder/name rename completion,
  - `plugin_name` rename completion,
  - direct-import doc conversion,
  - internal `edmc_hotkeys` path stability.
- Define concrete rollback triggers (for example: plugin startup failure, import regression, duplicate plugin load behavior).
- Map each rollback trigger to a rollback action in this plan.

Acceptance criteria:
- Each major rename requirement has at least one explicit success check.
- Rollback triggers are concrete and actionable (not vague).
- Phase 2 can begin with no unresolved contract/acceptance ambiguities.

Verification commands:
1. `rg -n "Exit Criteria|Rollback|Validation Plan|Decision Gates" docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md`

Risk and rollback:
- Risk: acceptance criteria remain too high-level to detect regressions quickly.
- Rollback: refine checks to command-verifiable conditions before entering Phase 2.

Phase 1 done definition:
- Stages `1.1`, `1.2`, and `1.3` are marked `Completed`.
- Phase 1 status is set to `Completed`.
- A `Phase 1 Implementation Results` section is added summarizing:
  - finalized contract decisions,
  - acceptance/rollback check matrix,
  - verification command outcomes.

## Phase 1 Implementation Results (Completed)

### Stage 1.1 Outputs (Completed)
- Canonical rename contract was finalized:
  - plugin folder/import surface target is `EDMCHotkeys`,
  - runtime-facing `plugin_name` target is `EDMCHotkeys`,
  - internal package path remains `edmc_hotkeys`,
  - direct import style is required in docs/examples (no `importlib` examples for canonical path).
- Scope/Non-Goals now explicitly encode:
  - no legacy import compatibility path,
  - no local user binding migration.

### Stage 1.2 Outputs (Completed)
- Hard-change policy is locked and consistent across plan sections:
  - no alias,
  - no deprecation window,
  - legacy `EDMC-Hotkeys.load` path unsupported.
- Decision-gate section reflects resolved decisions and no open contract blockers remain.

### Stage 1.3 Outputs (Completed)
- Acceptance criteria were converted into implementation entry checks:

| Requirement | Check |
| --- | --- |
| Canonical identity is consistent | `EDMCHotkeys` appears in Scope/Strategy/Phase criteria and legacy path is marked unsupported |
| Runtime name contract is explicit | Plan explicitly requires `plugin_name` -> `EDMCHotkeys` |
| Import style contract is explicit | Plan requires direct `import` documentation and no canonical `importlib` examples |
| Internal package invariants are explicit | Plan states `edmc_hotkeys` remains unchanged |
| Documentation rename scope is explicit | Phase 4 includes doc filename rename stage |

- Rollback triggers and responses were defined:

| Trigger | Rollback Response |
| --- | --- |
| Rename implementation introduces conflicting contract statements | Normalize plan language back to hard-change baseline before Phase 2 |
| Rename implementation causes startup/import regression in validation | Revert rename changes to prior `EDMC-Hotkeys` path and rerun validation |
| Packaging references unresolved old/new folder assumptions | Revert packaging edits and restore old artifact path while gap is fixed |

### Phase 1 Verification Command Outcomes
- `rg -n "EDMCHotkeys|plugin_name|direct import|edmc_hotkeys|legacy" docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md` passed:
  - confirms canonical naming/import/internal-path requirements are explicitly present.
- `rg -n "compatibility|alias|deprecation|hard change|legacy" docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md` passed:
  - confirms hard-change policy is encoded and no compatibility requirement is present.
- `rg -n "Exit Criteria|Rollback|Validation Plan|Decision Gates" docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md` passed:
  - confirms acceptance/rollback/validation and resolved decisions are all represented.

Result:
- Phase 1 exit criteria satisfied.
- Phase 2 can begin.

## Phase 2 - Repo and Packaging Rename Preparation (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Inventory all references to `EDMC-Hotkeys` in code/docs/scripts | Completed |
| 2.2 | Identify artifact/build pipeline assumptions for folder name | Completed |
| 2.3 | Identify dependent plugin integration points requiring migration | Completed |

### Phase 2 Exit Criteria
- Full impact inventory exists with no unknown rename-critical references.
- Packaging/release impact is documented with concrete edits.

## Phase 2 Detailed Execution Plan

Execution order:
1. Complete Stage `2.1` full-reference inventory first.
2. Complete Stage `2.2` packaging/release assumption inventory second.
3. Complete Stage `2.3` dependent-consumer migration inventory third.
4. Do not start Phase 3 implementation edits until all Phase 2 stages are `Completed`.

### Stage 2.1 - Repository-Wide Rename-Critical Reference Inventory (Completed)
Objective:
- Build a complete inventory of repository references that must be changed for the rename.

Touch points:
- Code (`*.py`)
- Docs (`*.md`)
- Config/workflow files (`*.yml`, `*.yaml`, `*.json`, `*.toml`)
- Scripts (`*.sh`, `*.ps1`)

Tasks:
- Scan for old/new naming tokens and import forms:
  - `EDMC-Hotkeys`
  - `EDMCHotkeys`
  - `EDMC-Hotkeys.load`
  - `importlib.import_module(...)` usage tied to hotkeys API
  - `plugin_name` string literals.
- Classify each hit into:
  - required rename edit,
  - intentionally retained legacy reference (if any),
  - already-canonical reference (no change).
- Create a concrete “edit list” to feed Phase 3 implementation.

Acceptance criteria:
- All rename-critical references are captured in one inventory list.
- Each inventory item has a disposition (`edit`, `keep`, or `already-canonical`).
- No unresolved reference category remains before Stage `2.2`.

Verification commands:
1. `rg -n "EDMC-Hotkeys|EDMCHotkeys|EDMC-Hotkeys\\.load|importlib\\.import_module|plugin_name" -g "*.py" -g "*.md" -g "*.yml" -g "*.yaml" -g "*.json" -g "*.toml" -g "*.sh" -g "*.ps1"`

Risk and rollback:
- Risk: missing one high-impact reference leads to partial rename and runtime breakage.
- Rollback: rerun expanded search patterns and block Phase 3 entry until inventory is complete.

### Stage 2.2 - Packaging/Release Assumption Inventory (Completed)
Objective:
- Identify every packaging/release workflow assumption that depends on the old plugin folder/name.

Touch points:
- `.github/workflows/*`
- `scripts/*` release/package helpers
- release/plan docs describing artifact contents and plugin paths

Tasks:
- Enumerate workflow/job steps that reference plugin path names, zip roots, artifact names, or release labels.
- Record proposed updates for each path/name assumption under the new canonical folder name.
- Identify whether any CI assertions/checks explicitly validate old naming and must be updated.

Acceptance criteria:
- Packaging/release assumptions are explicitly listed with target replacements.
- No unresolved workflow reference to old naming remains in the inventory.
- Phase 3 rename edits can be executed without guessing build/release behavior.

Verification commands:
1. `rg -n "EDMC-Hotkeys|artifact|release|zip|plugins/" .github scripts docs -g "*.yml" -g "*.yaml" -g "*.py" -g "*.sh" -g "*.ps1" -g "*.md"`

Risk and rollback:
- Risk: artifacts build with mixed naming or wrong root folder.
- Rollback: restore previous workflow scripts and rerun packaging validation after inventory correction.

### Stage 2.3 - Dependent Consumer Migration Inventory (Completed)
Objective:
- Identify every downstream-facing integration surface that must be updated for dependent plugins.

Touch points:
- `README.md`
- integration docs (including register-action guide and migration notes)
- example snippets for plugin consumers

Tasks:
- Inventory all consumer-facing import examples and API usage snippets.
- Mark each snippet for direct-import conversion using `EDMCHotkeys`.
- Define migration-note bullets for dependent plugins that currently use `EDMC-Hotkeys.load`.

Acceptance criteria:
- Consumer-facing docs have a complete migration-target list.
- All known import examples have a planned direct-import replacement.
- Migration guidance scope is clear enough to execute in Phase 4 without re-discovery.

Verification commands:
1. `rg -n "EDMC-Hotkeys\\.load|EDMC-Hotkeys|importlib|register_action|list_actions|invoke_action" README.md docs -g "*.md"`

Risk and rollback:
- Risk: docs leave stale import examples and create avoidable integration failures.
- Rollback: hold documentation release until stale examples are fully replaced.

Phase 2 done definition:
- Stages `2.1`, `2.2`, and `2.3` are marked `Completed`.
- Phase 2 status is set to `Completed`.
- A `Phase 2 Implementation Results` section is added summarizing:
  - inventory outputs and classifications,
  - packaging/release assumption map,
  - dependent-consumer migration map,
  - verification command outcomes.

## Phase 2 Implementation Results (Completed)

### Stage 2.1 Outputs (Completed)
- Ran full repo inventory:
  - `rg -l "EDMC-Hotkeys|EDMCHotkeys|EDMC-Hotkeys\\.load|importlib\\.import_module|plugin_name" . -g "*.py" -g "*.md" -g "*.yml" -g "*.yaml" -g "*.json" -g "*.toml" -g "*.sh" -g "*.ps1"`
  - Result: `50` files matched.
- Classification/disposition map created:
  - `edit` (Phase 3/4 execution): runtime/build/test/integration surfaces such as `load.py`, `__init__.py`, `.github/workflows/release.yml`, `scripts/build_release_artifact.py`, `docs/register-action-with-edmc-hotkeys.md`, `docs/linux-user-setup.md`, and release runbook files.
  - `keep (historical context)`: prior completed historical plan docs under `docs/plans/` that mention `EDMC-Hotkeys` as historical state.
  - `already-canonical`: current rename plan sections already using `EDMCHotkeys`.
- Additional scoped inventory counts:
  - Runtime/build/workflow references (`load.py`, `__init__.py`, `edmc_hotkeys`, `scripts`, `.github`): `18` files.
  - Test/companion references (`tests`, `companion`): `6` files.
  - Non-plan docs requiring rename migration focus (`docs` excluding `docs/plans`): `11` files.
  - Historical plan docs with old-name references: `12` files.

### Stage 2.2 Outputs (Completed)
- Packaging/release assumptions inventory completed with explicit replacement targets:
  - `.github/workflows/release.yml`: artifact upload path currently hardcoded to `EDMC-Hotkeys-*` naming.
  - `scripts/build_release_artifact.py`: `TOP_LEVEL_DIR = "EDMC-Hotkeys"` and artifact filename prefix currently hardcoded.
  - `docs/release/GITHUB_RELEASE_WORKFLOW_RUNBOOK.md`: documents old artifact names and `EDMC-Hotkeys/` archive root.
  - `docs/plans/GITHUB_RELEASE_WORKFLOW_REQUIREMENTS.md`: requirements text pins top-level extracted folder to `EDMC-Hotkeys/`.
- Planned replacement target for all rename-critical packaging assumptions: `EDMCHotkeys` artifact prefix and `EDMCHotkeys/` archive root.

### Stage 2.3 Outputs (Completed)
- Dependent consumer migration inventory completed:
  - Primary migration doc: `docs/register-action-with-edmc-hotkeys.md` still contains `importlib` usage and `EDMC-Hotkeys.load` import path examples.
  - Supporting architecture guidance: `docs/requirements-architecture-notes.md` references old plugin path/name.
  - User-facing setup notes: `docs/linux-user-setup.md` references old plugin folder/path strings.
- `README.md` currently has no blocking import snippet that references `EDMC-Hotkeys.load`.
- Migration scope for Phase 4 is now explicit: convert consumer docs to canonical direct import examples using `EDMCHotkeys`.

### Phase 2 Verification Command Outcomes
- `rg -l "EDMC-Hotkeys|EDMCHotkeys|EDMC-Hotkeys\\.load|importlib\\.import_module|plugin_name" . -g "*.py" -g "*.md" -g "*.yml" -g "*.yaml" -g "*.json" -g "*.toml" -g "*.sh" -g "*.ps1"` passed and produced complete repo inventory (`50` files).
- `rg -n "EDMC-Hotkeys|artifact|release|zip|plugins/" .github/workflows scripts/build_release_artifact.py docs/release docs/plans/GITHUB_RELEASE_WORKFLOW_REQUIREMENTS.md -g "*.yml" -g "*.yaml" -g "*.py" -g "*.md"` passed and identified all known rename-critical packaging/release assumptions.
- `rg -n "EDMC-Hotkeys\\.load|EDMC-Hotkeys|importlib|register_action|list_actions|invoke_action" README.md docs/register-action-with-edmc-hotkeys.md docs/requirements-architecture-notes.md docs/linux-user-setup.md -g "*.md"` passed and identified downstream consumer migration touch points.

Result:
- Phase 2 exit criteria satisfied.
- Phase 3 implementation edits can begin without additional discovery.

## Phase 3 - Implementation (Rename) (Status: Completed - folder rename deferred)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Rename plugin folder/import package surface to `EDMCHotkeys` and update `plugin_name` | Completed (folder rename deferred) |
| 3.2 | Keep internal package path as `edmc_hotkeys` and preserve API export parity | Completed |
| 3.3 | Remove/replace legacy import usage across project docs/examples with direct `import` style | Completed |

### Phase 3 Exit Criteria
- New import surface works for standard Python imports.
- Legacy import path is not required and not documented as supported.
- No functional regressions in plugin startup, prefs, and runtime dispatch.

## Phase 3 Detailed Execution Plan

Execution order:
1. Complete Stage `3.1` rename of canonical plugin entry surface first.
2. Complete Stage `3.2` API parity and internal package boundary validation second.
3. Complete Stage `3.3` legacy import cleanup/direct-import conversion third.
4. Do not start Phase 4 until all Phase 3 stages are marked `Completed`.

### Stage 3.1 - Canonical Plugin Entry Surface Rename (Completed - folder rename deferred)
Objective:
- Apply the hard rename at the plugin entry surface so EDMC and downstream imports use `EDMCHotkeys`.

Touch points:
- Plugin root folder name (rename from `EDMC-Hotkeys` to `EDMCHotkeys`)
- `load.py`
- `__init__.py`
- Any runtime-visible plugin label strings tied to startup/error dialogs

Tasks:
- Rename the plugin root directory to `EDMCHotkeys`.
- Update `plugin_name` constant to `EDMCHotkeys`.
- Update root import facade docstring/comments to reflect canonical name.
- Update runtime-facing labels/messages that still reference `EDMC-Hotkeys` where they are user-facing runtime identifiers.

Acceptance criteria:
- Canonical plugin root directory is `EDMCHotkeys`.
- `plugin_start3()` path returns the renamed plugin identity via `plugin_name`.
- Runtime startup still initializes with no hook signature or lifecycle behavior changes.

Verification commands:
1. `rg -n "plugin_name\\s*=\\s*\"EDMCHotkeys\"|EDMC-Hotkeys" load.py __init__.py`
2. `rg -n "plugin_start3|plugin_stop|plugin_prefs|prefs_changed|plugin_app" load.py`

Risk and rollback:
- Risk: EDMC cannot load the plugin if folder name and runtime identity diverge.
- Rollback: revert folder rename + `plugin_name` edits together as one atomic rollback unit.

### Stage 3.2 - Internal Package Boundary and API Export Parity (Completed)
Objective:
- Preserve behavior by keeping `edmc_hotkeys` internal modules unchanged while maintaining root API parity.

Touch points:
- `__init__.py`
- `load.py`
- `edmc_hotkeys/*` imports (no internal package rename)
- Tests covering public API and storage/runtime behavior

Tasks:
- Keep internal module path as `edmc_hotkeys` (no rename drift).
- Ensure root-exported API symbols remain stable (`register_action`, `list_actions`, `get_action`, `list_bindings`, `invoke_action`).
- Update imports/tests that reference old root plugin path so they use canonical `EDMCHotkeys` surface.
- Confirm config key namespace and persistence behavior remain unchanged.

Acceptance criteria:
- Internal imports continue to resolve via `edmc_hotkeys`.
- Public API symbol set and call signatures remain unchanged.
- Existing behavior tests for registry/settings/storage continue to pass.

Verification commands:
1. `rg -n "from edmc_hotkeys|import edmc_hotkeys" load.py __init__.py edmc_hotkeys`
2. `rg -n "register_action|list_actions|get_action|list_bindings|invoke_action" load.py __init__.py`
3. `.\.venv\Scripts\python.exe -m pytest tests/test_action_registry.py tests/test_settings_state.py tests/test_storage.py`

Risk and rollback:
- Risk: API facade drift breaks downstream plugins even if plugin loads.
- Rollback: restore previous root export surface and rerun targeted API tests before reattempt.

### Stage 3.3 - Legacy Import Path Removal and Direct-Import Conversion (Completed)
Objective:
- Remove legacy `EDMC-Hotkeys.load` usage from implementation-facing examples/tests and enforce canonical direct import usage.

Touch points:
- `docs/register-action-with-edmc-hotkeys.md`
- `README.md`
- Tests/scripts/examples that reference `EDMC-Hotkeys.load` or hotkeys-specific `importlib` import path patterns

Tasks:
- Replace `importlib.import_module("EDMC-Hotkeys.load")` examples with direct import snippets (`import EDMCHotkeys as hotkeys`).
- Remove stale old-path references from active (non-historical) docs/tests/scripts.
- Keep historical plan docs unchanged unless they are explicitly part of migration docs.
- Validate that direct-import guidance is copy-paste ready for downstream plugins.

Acceptance criteria:
- No active consumer docs/tests/scripts reference `EDMC-Hotkeys.load`.
- Canonical docs show direct import usage for the hotkeys API.
- Legacy path remains intentionally unsupported (hard change preserved).

Verification commands:
1. `rg -n "EDMC-Hotkeys\\.load|importlib\\.import_module\\(\"EDMC-Hotkeys\\.load\"\\)" README.md docs tests scripts -g "*.md" -g "*.py" -g "*.sh" -g "*.ps1"`
2. `rg -n "import EDMCHotkeys as hotkeys" README.md docs -g "*.md"`

Risk and rollback:
- Risk: stale instructions cause downstream integration failures despite successful runtime rename.
- Rollback: block Phase 4 completion until all active integration docs/snippets are canonical.

Phase 3 done definition:
- Stages `3.1`, `3.2`, and `3.3` are marked `Completed`.
- Phase 3 status is set to `Completed`.
- A `Phase 3 Implementation Results` section is added summarizing:
  - runtime rename edits,
  - API parity confirmation,
  - legacy import cleanup outcomes,
  - verification command/test results.

## Phase 3 Implementation Results (Completed - folder rename deferred)

### Stage 3.1 Outputs (Completed)
- Canonical runtime/plugin identity was updated to `EDMCHotkeys`:
  - `load.py`: `plugin_name = "EDMCHotkeys"`.
  - Runtime-facing dialog/guard text in `load.py` updated from `EDMC-Hotkeys` to `EDMCHotkeys`.
  - Root import facade docstring in `__init__.py` updated to `EDMCHotkeys`.
- Rename-critical packaging implementation surfaces were updated:
  - `scripts/build_release_artifact.py`: `TOP_LEVEL_DIR` now `EDMCHotkeys`.
  - `.github/workflows/release.yml`: artifact path now uses `dist/EDMCHotkeys-...`.
  - `tests/test_release_artifact_builder.py`: expected extracted root updated to `EDMCHotkeys`.
- Hard-change rename behavior is now reflected by runtime identity + artifact layout; internal package path remains unchanged by design (`edmc_hotkeys`).
- Deferred item (by decision):
  - On-disk workspace/plugin folder rename (`EDMC-Hotkeys` -> `EDMCHotkeys`) will be executed later as a separate/manual cutover step.

### Stage 3.2 Outputs (Completed)
- Internal module boundary preserved:
  - `load.py` continues to import from `edmc_hotkeys.*`.
  - No internal package rename was introduced.
- Public API parity preserved at the plugin root facade:
  - `register_action`, `list_actions`, `get_action`, `list_bindings`, `invoke_action`, and `invoke_bound_action` remain exported via `__init__.py`.
- Logger defaults across runtime/backends were updated to canonical plugin naming (`EDMCHotkeys`) without changing behavior.

### Stage 3.3 Outputs (Completed)
- Legacy consumer import path usage removed from active consumer docs:
  - `docs/register-action-with-edmc-hotkeys.md` now uses direct import examples:
    - `import EDMCHotkeys as hotkeys`
    - `import EDMCHotkeys as _hotkeys_api`
  - Legacy `importlib.import_module("EDMC-Hotkeys.load")` examples removed.
- Active migration notes updated for canonical name usage:
  - `docs/requirements-architecture-notes.md` updated to `EDMCHotkeys` naming/path examples.
  - `docs/linux-user-setup.md` updated for `EDMCHotkeys` runtime/path guidance.

### Phase 3 Verification Command/Test Outcomes
- `rg -n 'plugin_name = "EDMCHotkeys"|EDMC-Hotkeys' load.py __init__.py` passed:
  - confirms canonical `plugin_name` and no stale `EDMC-Hotkeys` strings in entrypoint/facade files.
- `rg -n "from edmc_hotkeys|import edmc_hotkeys" load.py __init__.py edmc_hotkeys` passed:
  - confirms internal package boundary remained `edmc_hotkeys`.
- `rg -n "plugin_start3|plugin_stop|plugin_prefs|prefs_changed|plugin_app" load.py` passed:
  - confirms lifecycle hook surface remains present.
- `rg -n -F "EDMC-Hotkeys.load" README.md docs tests scripts -g "*.md" -g "*.py" -g "*.sh" -g "*.ps1" --glob "!docs/plans/**"` passed with no matches:
  - confirms active docs/tests/scripts no longer document the legacy import path.
- `.\.venv\Scripts\python.exe -m pytest --basetemp .\.tmp_pytest tests/test_action_registry.py tests/test_settings_state.py tests/test_storage.py tests/test_release_artifact_builder.py` passed:
  - `45 passed`.
  - executed outside sandbox restrictions due temp-directory permission limits in sandbox mode.

Result:
- Phase 3 code/documentation scope is complete.
- On-disk folder rename is intentionally deferred for later execution.
- Phase 4 documentation/migration consolidation can begin.

## Phase 4 - Documentation and Consumer Migration (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Rename documentation files that embed old plugin naming | Completed |
| 4.2 | Update README and integration docs to canonical `EDMCHotkeys` direct-import usage | Completed |
| 4.3 | Add migration notes for dependent plugins | Completed |
| 4.4 | Document hard-change release note for import rename | Completed |

### Phase 4 Exit Criteria
- All user/developer docs consistently reference canonical direct imports with `EDMCHotkeys` (any `importlib` mention is explicitly marked legacy/unsupported migration context).
- Relevant doc filenames no longer use old plugin naming.
- Migration instructions are copy-paste ready.

## Phase 4 Detailed Execution Plan

Execution order:
1. Complete Stage `4.1` filename and path-surface doc renames first.
2. Complete Stage `4.2` content normalization for README/integration docs second.
3. Complete Stage `4.3` dependent-plugin migration guidance third.
4. Complete Stage `4.4` hard-change release-note documentation last.
5. Do not start Phase 5 validation sign-off until all Phase 4 stages are marked `Completed`.

### Stage 4.1 - Documentation Filename and Path Surface Rename (Completed)
Objective:
- Remove old plugin naming from active documentation filenames and path examples.

Touch points:
- `docs/register-action-with-edmc-hotkeys.md` (rename to canonical filename)
- Any active doc links that reference old filename/path patterns
- Root/readme references to renamed docs

Tasks:
- Rename docs whose filenames embed legacy naming to canonical `EDMCHotkeys` naming.
- Update all inbound links to renamed files.
- Update path examples that still reference legacy plugin directory names where those examples are intended as current guidance.
- Keep historical plan docs unchanged unless they are explicitly part of active migration guidance.

Acceptance criteria:
- No active canonical docs have filenames embedding `EDMC-Hotkeys`.
- No broken links remain after filename changes.
- Current-guidance path examples use `EDMCHotkeys`.

Verification commands:
1. `rg -n "register-action-with-edmc-hotkeys|EDMC-Hotkeys" README.md docs -g "*.md" --glob "!docs/plans/**"`
2. `rg -n "]\([^)]*register-action-with-edmc-hotkeys[^)]*\)" README.md docs -g "*.md"`

Risk and rollback:
- Risk: renamed files break references in README/docs.
- Rollback: restore prior filename and links as one atomic docs rollback, then retry with link map validation first.

### Stage 4.2 - Canonical Documentation Content Normalization (Completed)
Objective:
- Ensure active documentation consistently presents `EDMCHotkeys` as canonical and uses direct-import guidance.

Touch points:
- `README.md`
- integration/setup docs under `docs/` (non-plan)
- release/runbook docs that describe artifact naming and extraction root

Tasks:
- Normalize remaining active docs to canonical plugin name `EDMCHotkeys`.
- Remove any remaining canonical guidance that implies legacy import path support.
- Align artifact naming examples (`dist/EDMCHotkeys-*`) and extraction root (`EDMCHotkeys/`) with implemented scripts/workflow.
- Preserve intentional historical references only inside plan/history documents.

Acceptance criteria:
- Active docs have no stale canonical guidance using `EDMC-Hotkeys`.
- Active docs consistently describe direct import usage for plugin consumers.
- Active release/runbook docs align with current artifact/script behavior.

Verification commands:
1. `rg -n "EDMC-Hotkeys|importlib\.import_module\(\"EDMC-Hotkeys\.load\"\)" README.md docs -g "*.md" --glob "!docs/plans/**"`
2. `rg -n "EDMCHotkeys|dist/EDMCHotkeys|EDMCHotkeys/" README.md docs/release docs -g "*.md" --glob "!docs/plans/**"`

Risk and rollback:
- Risk: mixed naming in docs creates contradictory operator/developer guidance.
- Rollback: revert affected docs and reapply normalization using a reviewed doc inventory checklist.

### Stage 4.3 - Dependent Plugin Migration Guidance Completion (Completed)
Objective:
- Provide explicit, copy-paste migration instructions for downstream plugin maintainers.

Touch points:
- Action registration guide
- README migration section or dedicated migration note doc
- Any troubleshooting sections that mention old import behavior

Tasks:
- Add a focused migration section showing:
  - old import pattern (legacy, unsupported),
  - new canonical direct-import pattern (`import EDMCHotkeys as hotkeys`),
  - expected failure mode if legacy path is still used.
- Provide a short downstream checklist for plugin maintainers:
  - update import line,
  - retest action registration,
  - verify bindings discovery/invocation path.
- Ensure instructions match current public API symbols and signatures.

Acceptance criteria:
- Migration section is present and explicit about hard-change behavior.
- Instructions are copy-paste ready and technically aligned with current API.
- No ambiguity remains about legacy-path support status.

Verification commands:
1. `rg -n "migration|legacy|unsupported|import EDMCHotkeys as hotkeys" README.md docs -g "*.md" --glob "!docs/plans/**"`
2. `rg -n "register_action|list_actions|get_action|list_bindings|invoke_action" docs -g "*.md" --glob "!docs/plans/**"`

Risk and rollback:
- Risk: downstream plugins retain stale import pattern and fail at runtime.
- Rollback: hold Phase 4 completion until migration section is explicit and validated against runtime API surface.

### Stage 4.4 - Hard-Change Release Note Finalization (Completed)
Objective:
- Document the pre-release breaking rename clearly for operators and downstream integrators.

Touch points:
- `RELEASE_NOTES.md`
- release runbook/checklist docs as needed

Tasks:
- Add explicit release-note entry for rename hard change:
  - canonical plugin name/import is `EDMCHotkeys`,
  - legacy `EDMC-Hotkeys.load` import is unsupported,
  - plugin folder rename/cutover expectation is documented.
- Add operator note to avoid mixed old/new folder installs during transition.
- Ensure release notes and runbook language are consistent.

Acceptance criteria:
- Release notes clearly communicate rename scope and migration action.
- Hard-change behavior is unambiguous for integrators.
- Operator warning about mixed-folder installs is present.

Verification commands:
1. `rg -n "EDMCHotkeys|EDMC-Hotkeys.load|breaking|rename|folder" RELEASE_NOTES.md docs/release -g "*.md"`
2. `rg -n "both old and new plugin folders|mixed folder|cutover" RELEASE_NOTES.md docs/release -g "*.md"`

Risk and rollback:
- Risk: release communication gap causes avoidable support incidents.
- Rollback: block release-readiness sign-off until release-note language is explicit and reviewed.

Phase 4 done definition:
- Stages `4.1`, `4.2`, `4.3`, and `4.4` are marked `Completed`.
- Phase 4 status is set to `Completed`.
- A `Phase 4 Implementation Results` section is added summarizing:
  - filename/link migration outcomes,
  - canonical docs normalization outcomes,
  - downstream migration guidance additions,
  - release-note hard-change communication outcomes,
  - verification command results.

## Phase 4 Implementation Results (Completed)

### Stage 4.1 Outputs (Completed)
- Renamed consumer registration guide filename:
  - `docs/register-action-with-edmc-hotkeys.md` -> `docs/register-action-with-edmchotkeys.md`.
- Updated README reference to canonical filename:
  - `README.md` now links to `docs/register-action-with-edmchotkeys.md`.
- Verified no active (non-plan) docs still reference the old filename token.

### Stage 4.2 Outputs (Completed)
- Normalized active documentation naming surface to `EDMCHotkeys`:
  - `README.md`
  - `RELEASE_NOTES.md`
  - `docs/feature-flags.md`
  - `docs/manual-qa-checklist.md`
  - `docs/gnome-wayland-bridge-prototype.md`
  - `docs/gnome-companion-compatibility-matrix.md`
  - `docs/release/GITHUB_RELEASE_WORKFLOW_RUNBOOK.md`
  - `docs/release/GNOME_WAYLAND_BRIDGE_ALPHA_ROLLOUT_CHECKLIST.md`
  - `docs/release/GNOME_WAYLAND_BRIDGE_GA_DECISION_RECORD.md`
  - `docs/release/GNOME_WAYLAND_BRIDGE_ISSUE_TRIAGE_TEMPLATE.md`
- Artifact naming and extraction root docs were aligned with implementation:
  - `dist/EDMCHotkeys-*`
  - `EDMCHotkeys/` extraction root.

### Stage 4.3 Outputs (Completed)
- Added explicit downstream migration guidance:
  - `docs/register-action-with-edmchotkeys.md` now includes a dedicated `Migration From Legacy Imports` section.
  - The section shows unsupported legacy pattern vs supported canonical direct import.
  - README now includes a pre-release breaking rename summary and migration action bullets.
- Confirmed active consumer examples use direct import:
  - `import EDMCHotkeys as hotkeys`.

### Stage 4.4 Outputs (Completed)
- Added hard-change release-note entry:
  - `RELEASE_NOTES.md` includes `2026-02-28 - Rename to EDMCHotkeys (Hard Change)`.
  - Entry states legacy `EDMC-Hotkeys.load` is unsupported and provides migration action.
- Added operator cutover warning:
  - README warns against keeping both old/new folder names simultaneously.
  - `docs/release/GITHUB_RELEASE_WORKFLOW_RUNBOOK.md` includes a `Rename Cutover Guard` section.

### Phase 4 Verification Command Outcomes
- `rg -n "register-action-with-edmc-hotkeys" README.md docs RELEASE_NOTES.md -g "*.md" --glob "!docs/plans/**"` passed with no matches.
- `rg -n "register-action-with-edmchotkeys|import EDMCHotkeys as hotkeys|migration|legacy|unsupported" README.md docs RELEASE_NOTES.md -g "*.md" --glob "!docs/plans/**"` passed and confirmed expected canonical guidance + explicit migration sections.
- `rg -n "dist/EDMCHotkeys|EDMCHotkeys/|EDMC-Hotkeys\\.load|cutover" RELEASE_NOTES.md docs/release -g "*.md"` passed and confirmed release/runbook hard-change communication and artifact naming alignment.
- `rg -n -F "EDMC-Hotkeys" README.md RELEASE_NOTES.md docs -g "*.md" --glob "!docs/plans/**"` now returns only intentional legacy references in migration/cutover warning contexts.

Result:
- Phase 4 exit criteria satisfied.
- Documentation and downstream migration guidance are consistent with the canonical `EDMCHotkeys` import surface.

## Phase 5 - Validation and Release Readiness (Status: Completed - No-Go pending folder cutover)
| Stage | Description | Status |
| --- | --- | --- |
| 5.1 | Run targeted test suites and manual startup/import validation | Completed (automated checks passed; manual EDMC checks pending) |
| 5.2 | Validate dependent plugin integration on current runtime | Completed (No-Go: canonical import blocked until folder rename cutover) |
| 5.3 | Final go/no-go review with rollback readiness checklist | Completed (No-Go decision recorded) |

### Phase 5 Exit Criteria
- Tests pass and manual validation confirms no import/startup regressions.
- Dependent plugins can import and register actions via canonical path.
- Release notes include rename + migration + hard-change details.

## Phase 5 Detailed Execution Plan

Execution order:
1. Complete Stage `5.1` targeted automated/manual validation first.
2. Complete Stage `5.2` downstream integration validation second.
3. Complete Stage `5.3` go/no-go + rollback readiness review last.
4. Phase closes only when all three stages are marked `Completed`.

### Stage 5.1 - Targeted Runtime Validation (Completed - automated checks passed, manual EDMC checks pending)
Objective:
- Prove there are no functional regressions from the rename implementation across startup, settings, bindings, and packaging checks.

Touch points:
- Runtime entry/facade files (`load.py`, `__init__.py`)
- Packaging workflow/script alignment (`.github/workflows/release.yml`, `scripts/build_release_artifact.py`)
- Core tests (`tests/test_action_registry.py`, `tests/test_settings_state.py`, `tests/test_storage.py`, `tests/test_release_artifact_builder.py`)
- Manual runtime checks in EDMC

Tasks:
- Run targeted automated suite for registry/settings/storage/release artifact builder.
- Re-run focused grep checks for canonical runtime name and no stale legacy entry/facade strings.
- Confirm manual EDMC checks:
  - plugin loads without traceback,
  - settings pane opens and saves,
  - bindings still load/dispatch.
- Record environment-specific caveats (for example deferred on-disk folder rename).

Acceptance criteria:
- Targeted tests pass.
- No rename-related startup/import regressions observed.
- Manual smoke confirms key runtime flows still work.

Verification commands:
1. `.\.venv\Scripts\python.exe -m pytest --basetemp .\.tmp_pytest tests/test_action_registry.py tests/test_settings_state.py tests/test_storage.py tests/test_release_artifact_builder.py`
2. `rg -n 'plugin_name = "EDMCHotkeys"|EDMC-Hotkeys' load.py __init__.py`
3. `rg -n "plugin_start3|plugin_stop|plugin_prefs|prefs_changed|plugin_app" load.py`

Risk and rollback:
- Risk: runtime still references old naming at a critical path and fails in EDMC.
- Rollback: revert rename-touching runtime files as a single unit, rerun Stage 5.1 checks, then re-apply incrementally.

### Stage 5.2 - Dependent Plugin Integration Validation (Completed - No-Go pending folder cutover)
Objective:
- Validate that downstream plugins can consume the canonical API surface using direct import.

Touch points:
- `docs/register-action-with-edmchotkeys.md`
- `README.md`
- Representative dependent plugin integration snippet/tests (manual validation context)

Tasks:
- Validate direct-import integration path using canonical snippet:
  - `import EDMCHotkeys as hotkeys`
  - `hotkeys.register_action(...)`
- Confirm dependent plugin can list/invoke actions via exposed API.
- Validate expected failure behavior for legacy import path remains documented and understood.
- Capture any integration caveats tied to deferred on-disk folder rename.

Acceptance criteria:
- Canonical direct-import path works for downstream registration and invocation.
- No active docs instruct unsupported legacy import usage except in explicit migration context.
- Integration evidence is documented for release readiness.

Verification commands:
1. `rg -n "import EDMCHotkeys as hotkeys|register_action|list_actions|get_action|list_bindings|invoke_action" README.md docs -g "*.md" --glob "!docs/plans/**"`
2. `rg -n -F "EDMC-Hotkeys.load" README.md docs -g "*.md" --glob "!docs/plans/**"`

Risk and rollback:
- Risk: downstream plugins still fail due to stale import assumptions or missing API parity.
- Rollback: hold release readiness, update docs/examples and facade exports, then rerun Stage 5.2 checks.

### Stage 5.3 - Go/No-Go and Rollback Readiness Review (Completed - No-Go)
Objective:
- Finalize release readiness decision with explicit rollback path and deferred-item tracking.

Touch points:
- `RELEASE_NOTES.md`
- `docs/release/GITHUB_RELEASE_WORKFLOW_RUNBOOK.md`
- `docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md`

Tasks:
- Confirm release notes include hard-change rename guidance and migration action.
- Confirm runbook includes cutover guard and artifact naming alignment.
- Confirm deferred item is explicitly tracked:
  - on-disk folder rename to `EDMCHotkeys` scheduled later.
- Produce final go/no-go decision statement with rollback trigger checklist.

Acceptance criteria:
- Release communication artifacts are consistent and complete.
- Deferred folder-rename decision is explicit and non-ambiguous.
- Go/no-go outcome and rollback triggers are documented.

Verification commands:
1. `rg -n "Rename to EDMCHotkeys|EDMC-Hotkeys.load|cutover|single plugin folder" RELEASE_NOTES.md docs/release -g "*.md"`
2. `rg -n "Phase 5|Status: Completed|deferred" docs/plans/PLUGIN_RENAME_TO_EDMCHOTKEYS_PLAN.md`

Risk and rollback:
- Risk: incomplete release communication causes integration/operator errors post-merge.
- Rollback: block release sign-off until docs and decision record are complete and consistent.

Phase 5 done definition:
- Stages `5.1`, `5.2`, and `5.3` are marked `Completed`.
- Phase 5 status is set to `Completed`.
- A `Phase 5 Implementation Results` section is added summarizing:
  - test/validation outcomes,
  - dependent integration outcomes,
  - go/no-go decision and rollback readiness,
  - deferred folder-rename status at release decision time.

## Phase 5 Implementation Results (Completed - No-Go pending folder cutover)

### Stage 5.1 Outputs (Completed)
- Automated validation suite passed:
  - `.\.venv\Scripts\python.exe -m pytest --basetemp .\.tmp_pytest tests/test_settings_ui.py tests/test_settings_state.py tests/test_action_registry.py tests/test_storage.py tests/test_release_artifact_builder.py`
  - Result: `85 passed`.
- Runtime rename checks passed:
  - `rg -n 'plugin_name = "EDMCHotkeys"|EDMC-Hotkeys' load.py __init__.py` confirms canonical runtime name in entrypoint/facade files.
  - `rg -n "plugin_start3|plugin_stop|plugin_prefs|prefs_changed|plugin_app" load.py` confirms lifecycle hooks remain present.
- Manual EDMC runtime validation (GUI startup/settings/hotkey live dispatch) was not executable in this environment and remains pending.

### Stage 5.2 Outputs (Completed - No-Go)
- Dependent-plugin integration docs are canonical and consistent:
  - direct-import guidance present (`import EDMCHotkeys as hotkeys`),
  - API usage surface documented (`register_action`, `list_actions`, `get_action`, `list_bindings`, `invoke_action`).
- Legacy import references in active docs are intentionally migration-context warnings only.
- Canonical import readiness blocker captured:
  - `python -c "import importlib.util; importlib.util.find_spec('EDMCHotkeys')"` returned `None` in current workspace because on-disk folder cutover (`EDMC-Hotkeys` -> `EDMCHotkeys`) is deferred.
- Result: downstream canonical import path cannot be runtime-validated end-to-end until folder rename cutover occurs.

### Stage 5.3 Outputs (Completed - No-Go)
- Release communication validation passed:
  - `RELEASE_NOTES.md` contains hard-change rename entry and migration action.
  - `docs/release/GITHUB_RELEASE_WORKFLOW_RUNBOOK.md` contains cutover guard and canonical artifact/root naming.
- Deferred item tracking is explicit:
  - on-disk plugin folder rename is intentionally deferred.
- Final decision:
  - `No-Go` for release-readiness closure until folder cutover is executed and manual EDMC runtime validation is completed on the canonical import surface.

### Phase 5 Verification Command Outcomes
- `.\.venv\Scripts\python.exe -m pytest --basetemp .\.tmp_pytest tests/test_settings_ui.py tests/test_settings_state.py tests/test_action_registry.py tests/test_storage.py tests/test_release_artifact_builder.py` passed (`85 passed`).
- `rg -n 'plugin_name = "EDMCHotkeys"|EDMC-Hotkeys' load.py __init__.py` passed (canonical runtime naming confirmed).
- `rg -n "plugin_start3|plugin_stop|plugin_prefs|prefs_changed|plugin_app" load.py` passed (lifecycle hooks intact).
- `rg -n "import EDMCHotkeys as hotkeys|register_action|list_actions|get_action|list_bindings|invoke_action" README.md docs -g "*.md" --glob "!docs/plans/**"` passed.
- `rg -n -F "EDMC-Hotkeys.load" README.md docs -g "*.md" --glob "!docs/plans/**"` returns intentional migration-context references only.
- `python -c "import importlib.util; print(importlib.util.find_spec('EDMCHotkeys'))"` returned `None` (expected until folder cutover).

Result:
- Phase 5 execution is complete.
- Release readiness decision is `No-Go` pending:
  - on-disk folder cutover to `EDMCHotkeys`,
  - manual EDMC runtime validation on canonical import surface.

## Validation Plan
1. Automated tests:
   - `.\.venv\Scripts\python.exe -m pytest tests/test_settings_ui.py tests/test_settings_state.py tests/test_action_registry.py`
   - Additional targeted tests for API import paths and plugin startup.
2. Manual checks:
   - Open EDMC settings -> Hotkeys tab loads normally.
   - Existing bindings still load and fire.
   - Dependent plugin registers actions via canonical import path.

## Decision Gates (Resolved)
1. Legacy `EDMC-Hotkeys.load` imports are not supported (immediate hard change).
2. No runtime warning path is needed for legacy import usage because no alias path is provided.
3. Release notes should include explicit guidance to avoid having both old and new plugin folders installed.
