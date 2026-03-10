# Wayland Backend Consolidation Implementation Plan

Status: Draft  
Owner: EDMCHotkeys  
Last Updated: 2026-03-08

Follow persona details in AGENTS.md  
Document implementation results in the Implementation Results section.  
After each stage is complete change status to Completed.  
When all stages are complete change the phase status to Completed.  
If something is not clear, ask clarifying questions.

## Objective
Remove the generic Wayland backend and the Wayland GNOME backend so the project supports exactly three runtime backends:
1. Windows
2. Linux X11
3. Linux Wayland keyd

## Scope
- Remove generic Wayland backend runtime selection/registration paths.
- Remove Wayland GNOME backend runtime selection/registration paths.
- Keep Linux Wayland support only through `wayland_keyd`.
- Keep Windows and X11 behavior unchanged.
- Update runtime/backend mode handling, release artifact generation, and tests accordingly.
- Remove documents and scripts specific to deprecated Wayland backends.

## Non-Goals
- No redesign of hotkey action model, bindings schema, or keyd transport protocol.
- No migration of old backend-specific runtime state beyond safe fallback/normalization.
- No major settings UI redesign outside backend-mode options and required warnings.

## Requirements For Review
1. Supported backend set must be exactly:
   - `windows`
   - `x11`
   - `wayland_keyd`
2. Removed backend modes:
   - `wayland_portal` (generic Wayland backend)
   - `wayland_gnome_bridge`
3. `auto` behavior:
   - On Linux Wayland: select `wayland_keyd` when keyd is healthy.
   - On Linux Wayland with keyd unavailable: backend must remain unavailable with explicit startup warning and settings-pane hint (no implicit fallback to removed Wayland backends).
   - On Linux X11: select X11 backend.
   - On Windows: select Windows backend.
4. Config/runtime mode handling:
   - Deprecated/removed mode values in env/config must not crash startup.
   - Removed mode values must normalize to a safe mode (`auto`) and log a warning.
5. Backend selector and backend registry must no longer import/reference removed Wayland backend implementations.
6. Release artifacts:
   - Stop producing artifacts tied to removed Wayland backends.
   - Linux Wayland artifact must map to keyd backend only.
7. Tests:
   - Selector, mode normalization, and load/runtime tests must explicitly assert no removed Wayland backend paths remain.
8. Deprecation behavior:
   - Removed backend modes are treated as unsupported immediately after this change.
   - No runtime compatibility shim that silently preserves removed backend behavior.
9. Cleanup requirement:
   - Remove deprecated-backend-specific documents and scripts.
   - Keep only docs/scripts relevant to Windows, Linux X11, and Linux Wayland keyd.
10. Deletion policy:
   - Remove deprecated backend source files immediately after verifying no active code path imports/references them.
   - Removal mode is hard delete (no compatibility stubs, no one-release grace retention).

## Acceptance Criteria
1. Runtime codepaths cannot select or instantiate removed Wayland backends.
2. `auto` on Wayland only attempts `wayland_keyd`.
3. Removed mode values from config/env are handled safely and logged.
4. Release artifact builder no longer emits removed Wayland variants.
5. Test suite passes with updated backend matrix expectations.
6. Deprecated-backend docs/scripts are hard deleted (no replacement-only retention).
7. Deprecated backend source files are hard deleted after reference verification, with no remaining imports/usages.

## Phase 1 — Requirements Freeze (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Freeze final supported backend matrix and removed backend list | Completed |
| 1.2 | Freeze `auto` behavior on Wayland when keyd is unavailable (startup warning + settings-pane hint) | Completed |
| 1.3 | Freeze removed-mode normalization and logging contract | Completed |
| 1.4 | Freeze release artifact matrix after consolidation | Completed |
| 1.5 | Freeze hard-delete policy for deprecated backend source/docs/scripts | Completed |

## Phase 2 — Design Updates (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Update backend selector design to three-backend model | Completed |
| 2.2 | Update runtime mode validation list and normalization policy | Completed |
| 2.3 | Update release builder design for consolidated Linux variants | Completed |
| 2.4 | Map test impact and expected assertions by module | Completed |
| 2.5 | Design cleanup/deletion execution order (verify refs, then hard delete) | Completed |

## Phase 3 — Implementation (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Remove generic Wayland backend selection path | Completed |
| 3.2 | Remove Wayland GNOME backend selection path | Completed |
| 3.3 | Verify references then remove imports/wiring for removed backends | Completed |
| 3.4 | Implement removed-mode normalization to `auto` + warnings | Completed |
| 3.5 | Update release artifact builder to drop removed Wayland artifacts | Completed |
| 3.6 | Hard delete docs/scripts tied to deprecated Wayland backends | Completed |
| 3.7 | Hard delete deprecated backend source files after reference verification | Completed |

## Phase 4 — Verification (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Update and run selector/mode unit tests | Completed |
| 4.2 | Update and run load/runtime integration tests | Completed |
| 4.3 | Update and run release artifact builder tests | Completed |
| 4.4 | Validate docs/scripts + source cleanup | Completed |
| 4.5 | Validate no imports/references to removed backend modules remain | Completed |
| 4.6 | Run full pytest suite and record outcomes | Completed |

## Phase 5 — Rollout Readiness (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 5.1 | Confirm logs/messages for removed modes are actionable | Completed |
| 5.2 | Confirm config defaults/templates match consolidated backend set | Completed |
| 5.3 | Final compliance pass vs EDMC plugin/runtime constraints | Completed |

## Phase 1 Detailed Execution Plan
| Stage | Goal | Detailed Work Plan | Required Artifacts | Exit Criteria |
| --- | --- | --- | --- | --- |
| 1.1 | Freeze target backend matrix | Confirm final supported list and explicit removed list in this plan. | Updated Objective/Requirements sections. | No ambiguity about supported/removed backends. |
| 1.2 | Freeze Wayland auto behavior | Define exact behavior for Wayland when keyd unavailable (unavailable + startup warning + settings hint). | Explicit requirement text in this plan. | No conflicting fallback language remains. |
| 1.3 | Freeze mode compatibility policy | Define how removed modes in env/config are normalized and logged. | Normalization requirement text. | Startup behavior is deterministic and non-breaking. |
| 1.4 | Freeze packaging policy | Define Linux artifact variants after removal. | Release artifact requirement text. | Build output matrix is explicit and reviewable. |
| 1.5 | Freeze deletion policy | Lock verify-first then hard-delete policy for deprecated backend source files, docs, and scripts. | Deletion policy requirement text. | No ambiguity remains on immediate deletion behavior and pre-delete verification requirement. |

## Phase 2 Detailed Execution Plan
| Stage | Goal | Detailed Work Plan | Required Artifacts | Exit Criteria |
| --- | --- | --- | --- | --- |
| 2.1 | Selector design alignment | Update selector rules and fallback behavior to three-backend model. | Selector design notes in this plan. | Implementation can proceed without design ambiguity. |
| 2.2 | Runtime mode contract alignment | Update valid mode set and error-handling design for removed modes. | Runtime-mode design notes in this plan. | Deprecated mode handling is fully specified. |
| 2.3 | Packaging design alignment | Update artifact naming/variant strategy to remove obsolete Wayland outputs. | Packaging design notes in this plan. | Release tooling changes are fully scoped. |
| 2.4 | Test impact mapping | Enumerate exact tests to update/add for selector, loader, and release builder. | Test impact list in this plan. | Verification scope is complete and implementable. |
| 2.5 | Cleanup/deletion sequencing design | Define concrete sequence: reference audit, runtime detachment, hard deletion of backend source files/docs/scripts, then verification gates. | Cleanup execution checklist in this plan. | Deletion execution order is explicit and reversible up to deletion point. |

## Phase 3 Detailed Execution Plan
| Stage | Goal | Detailed Work Plan | Required Artifacts | Exit Criteria |
| --- | --- | --- | --- | --- |
| 3.1 | Remove generic Wayland backend path | Remove selection branches and mode plumbing for `wayland_portal`. | Code changes in selector/runtime mode files. | No runtime path can select generic Wayland backend. |
| 3.2 | Remove GNOME Wayland backend path | Remove selection branches and mode plumbing for `wayland_gnome_bridge`. | Code changes in selector/runtime mode files. | No runtime path can select GNOME Wayland backend. |
| 3.3 | Verify and remove backend references/imports | Inventory and verify all imports/usages, then remove obsolete backend registration/import references. | Reference audit output + code cleanup in backend init/selector/load wiring. | Removed backends are not reachable through live runtime wiring and no dead imports remain. |
| 3.4 | Add removed-mode normalization | Normalize removed mode values to `auto` and log clear warnings. | Runtime config/load changes + log assertions. | Removed mode inputs do not crash and are observable. |
| 3.5 | Consolidate release variants | Update release builder to emit only supported backend variants. | Release builder code/tests. | Build outputs match consolidated matrix. |
| 3.6 | Hard delete deprecated-backend docs/scripts | Hard delete scripts/docs specific to removed Wayland backends; keep only relevant consolidated assets. | Docs/scripts deletion commits. | No deprecated-backend-specific docs/scripts remain in active tree. |
| 3.7 | Hard delete deprecated backend source files | Hard delete source modules/files for removed Wayland backends after reference verification is complete. | Source deletion commits + selector/import updates. | Removed backend source modules/files are absent from active tree. |

## Phase 4 Detailed Execution Plan
| Stage | Goal | Detailed Work Plan | Required Artifacts | Exit Criteria |
| --- | --- | --- | --- | --- |
| 4.1 | Validate selector/mode behavior | Update selector + mode tests to new expected matrix. | Updated tests in backend/load test modules. | Selector tests pass and assert removed paths are absent. |
| 4.2 | Validate runtime loading behavior | Verify startup behavior for removed mode values and auto selection cases. | Updated load/runtime tests. | Runtime tests pass with expected warnings/fallback. |
| 4.3 | Validate packaging behavior | Update artifact builder tests for new Linux variant set. | Updated release builder tests. | Artifact tests pass and removed variants are absent. |
| 4.4 | Validate docs/scripts + source cleanup | Verify removed-backend docs/scripts and source files are deleted and remaining files are consistent with three-backend model. | File inventory + targeted grep output in Implementation Results. | No deprecated-backend-specific docs/scripts/source files remain. |
| 4.5 | Validate no stale references remain | Run targeted grep checks across repo to ensure no selector/import/config/test references to removed backend modes/modules remain. | Grep command outputs captured in Implementation Results. | No stale references/imports to removed backends remain. |
| 4.6 | Full regression check | Run full pytest suite and capture outcomes. | Test command output recorded in Implementation Results. | Full suite passes. |

## Phase 5 Detailed Execution Plan
| Stage | Goal | Detailed Work Plan | Required Artifacts | Exit Criteria |
| --- | --- | --- | --- | --- |
| 5.1 | Final warning/log quality pass | Verify log messages for removed modes are concise and actionable. | Log-message review notes. | Warnings are clear and non-noisy. |
| 5.2 | Config consistency pass | Verify defaults/template/config docs expose only supported backend values. | Config file audit notes. | No removed backend values remain in defaults/template. |
| 5.3 | Compliance and release readiness pass | Validate changes remain aligned with EDMC plugin constraints and project conventions. | Compliance checklist notes. | Plan marked ready for implementation sign-off. |

## Phase 1 Task-Level Plan
| Stage | Task-Level Steps | Verification Commands | Done Signal |
| --- | --- | --- | --- |
| 1.1 | Confirm the final backend names used across runtime selector, config, and tests; lock removed list (`wayland_portal`, `wayland_gnome_bridge`). | `rg -n "wayland_portal|wayland_gnome_bridge|wayland_keyd|x11|windows" load.py edmc_hotkeys tests scripts` | Backend matrix text and removed list are stable with no conflicting names. |
| 1.2 | Freeze exact unavailable behavior for Wayland `auto` when keyd is missing: startup warning + settings hint, no fallback to removed backends. | `rg -n "AutoHint|keyd is not active|restart EDMC|auto mode" load.py edmc_hotkeys tests` | Behavior is explicitly documented and test-targetable. |
| 1.3 | Freeze removed-mode normalization to `auto` and warning requirement for env/config values. | `rg -n "backend_mode|_VALID_BACKEND_MODES|falling back to auto|Invalid backend mode" load.py edmc_hotkeys/runtime_config.py` | Normalization policy text has no ambiguity. |
| 1.4 | Freeze release artifact target set after consolidation (only keyd Wayland for Linux Wayland). | `rg -n "linux-wayland|linux-wayland-portal|linux-wayland-gnome-bridge|wayland_keyd" scripts/build_release_artifact.py tests/test_release_artifact_builder.py` | Artifact policy is explicit and consistent with requirements. |
| 1.5 | Freeze verify-first hard-delete policy for source/docs/scripts tied to removed backends. | `rg -n "hard delete|verify references|Removal mode" docs/plans/WAYLAND_BACKEND_CONSOLIDATION_IMPLEMENTATION_PLAN.md` | Deletion policy is documented as immediate hard delete with pre-delete reference audit. |

## Phase 2 Task-Level Plan
| Stage | Task-Level Steps | Verification Commands | Done Signal |
| --- | --- | --- | --- |
| 2.1 | Define selector precedence using only `windows`, `x11`, `wayland_keyd`; remove design reliance on generic/GNOME Wayland backends. | `rg -n "select_backend|detect_linux_session|wayland" edmc_hotkeys/backends/selector.py tests/test_backends.py` | Selector design references only supported backend set. |
| 2.2 | Define runtime mode parsing/validation behavior for removed modes (normalize and warn, never crash). | `rg -n "_VALID_BACKEND_MODES|_resolve_backend_mode|Invalid backend mode" load.py tests/test_load_backend_mode.py` | Runtime mode contract is implementation-ready and test-mapped. |
| 2.3 | Define release-builder variant model that drops deprecated Wayland variants and keeps supported outputs only. | `rg -n "variant|linux-wayland|portal|gnome" scripts/build_release_artifact.py tests/test_release_artifact_builder.py` | Packaging design is fully scoped for implementation. |
| 2.4 | Map all test updates required for selector, loader, and release builder assertions. | `rg -n "wayland_portal|wayland_gnome_bridge|wayland_keyd" tests` | Test impact inventory is complete and includes negative assertions. |
| 2.5 | Define cleanup sequence: audit references -> detach runtime wiring -> hard delete source/docs/scripts -> run cleanup verification gates. | `rg -n "Phase 3|3.3|3.6|3.7|4.4|4.5" docs/plans/WAYLAND_BACKEND_CONSOLIDATION_IMPLEMENTATION_PLAN.md` | Execution order is explicit and safe. |

## Phase 3 Task-Level Plan
| Stage | Task-Level Steps | Verification Commands | Done Signal |
| --- | --- | --- | --- |
| 3.1 | Remove generic Wayland backend mode from selector and mode handling branches. | `rg -n "wayland_portal|portal" load.py edmc_hotkeys/backends/selector.py` | Generic Wayland selection path is removed from runtime logic. |
| 3.2 | Remove GNOME Wayland backend mode from selector and mode handling branches. | `rg -n "wayland_gnome_bridge|gnome_bridge|linux-wayland-gnome-bridge" load.py edmc_hotkeys/backends/selector.py` | GNOME Wayland selection path is removed from runtime logic. |
| 3.3 | Audit imports/usages, then remove backend registry wiring for removed backends. | `rg -n "from .*wayland|import .*wayland|wayland_portal|wayland_gnome_bridge" edmc_hotkeys load.py` | No active imports/usages remain for removed backends before deletion. |
| 3.4 | Implement removed-mode normalization and warning logs in startup/mode resolution path. | `source .venv/bin/activate && python -m pytest tests/test_load_backend_mode.py -q` | Removed mode values normalize safely and warnings are asserted in tests. |
| 3.5 | Update release builder and tests to remove deprecated Wayland artifact outputs. | `source .venv/bin/activate && python -m pytest tests/test_release_artifact_builder.py -q` | Build variants match consolidated backend matrix. |
| 3.6 | Hard delete deprecated-backend docs/scripts and update any remaining references to consolidated paths. | `rg -n "wayland_portal|wayland_gnome_bridge|portal|gnome bridge" docs scripts` | Deprecated-backend docs/scripts are absent and no stale references remain in active docs/scripts. |
| 3.7 | Hard delete deprecated backend source modules/files after reference audit passes. | `rg -n "wayland_portal|wayland_gnome_bridge|gnome_bridge|portal" edmc_hotkeys` | Removed backend source files are deleted and not referenced anywhere. |

## Phase 4 Task-Level Plan
| Stage | Task-Level Steps | Verification Commands | Done Signal |
| --- | --- | --- | --- |
| 4.1 | Update selector tests to assert only three-backend behavior and no removed-backend branches. | `source .venv/bin/activate && python -m pytest tests/test_backends.py tests/test_backend_contract.py -q` | Selector/backend contract tests pass with consolidated matrix assertions. |
| 4.2 | Update load/runtime tests for removed-mode normalization and Wayland `auto` unavailable warning/hint behavior. | `source .venv/bin/activate && python -m pytest tests/test_load_backend_mode.py tests/test_load_keyd_prefs_alerts.py -q` | Runtime behavior is validated end-to-end for normalization and hint/warning paths. |
| 4.3 | Verify release artifact tests for dropped Wayland variants and keyd-only Wayland output. | `source .venv/bin/activate && python -m pytest tests/test_release_artifact_builder.py -q` | Packaging tests confirm removed variants are not produced. |
| 4.4 | Validate cleanup outcomes for docs/scripts/source deletion. | `rg -n "wayland_portal|wayland_gnome_bridge|linux-wayland-portal|linux-wayland-gnome-bridge" .` | No removed backend docs/scripts/source references remain. |
| 4.5 | Run targeted stale-reference grep gates for selectors/imports/config/tests. | `rg -n "wayland_portal|wayland_gnome_bridge" edmc_hotkeys load.py tests scripts docs` | Zero stale references in active tree outside historical plan notes if retained. |
| 4.6 | Run full regression suite after consolidation changes. | `source .venv/bin/activate && python -m pytest -q` | Full suite passes and results are recorded. |

## Phase 5 Task-Level Plan
| Stage | Task-Level Steps | Verification Commands | Done Signal |
| --- | --- | --- | --- |
| 5.1 | Review startup/user-visible logs for removed mode warnings and keyd-unavailable messaging quality. | `rg -n "Invalid backend mode|falling back to auto|keyd is not active|restart EDMC" load.py edmc_hotkeys tests` | Messages are concise, actionable, and aligned with requirements. |
| 5.2 | Audit template/default config surfaces so only supported backend values remain. | `rg -n "wayland_portal|wayland_gnome_bridge|wayland_keyd|mode" config_template.ini config.defaults.ini docs` | Config surfaces show only supported backend values and no deprecated mode options. |
| 5.3 | Run final compliance/readiness pass for EDMC plugin constraints and release safety. | `source .venv/bin/activate && python -m pytest -q` | Compliance checklist complete; plan ready for implementation sign-off. |

## Test Plan
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py tests/test_backend_contract.py`
2. `source .venv/bin/activate && python -m pytest tests/test_load_backend_mode.py tests/test_load_keyd_prefs_alerts.py`
3. `source .venv/bin/activate && python -m pytest tests/test_release_artifact_builder.py`
4. `rg -n "wayland_portal|wayland_gnome_bridge|linux-wayland-portal|linux-wayland-gnome-bridge" .`
5. `source .venv/bin/activate && python -m pytest -q`

## Open Questions
- None currently.

## Implementation Results
- All phases completed with validation evidence captured below.

### Phase 1 Results (Completed)
| Stage | Result Summary | Validation Commands | Outcome |
| --- | --- | --- | --- |
| 1.1 | Confirmed matrix naming is explicit in plan and identified current runtime/build/test surfaces still containing removed backend modes (`wayland_portal`, `wayland_gnome_bridge`) for upcoming implementation stages. | `rg -n "wayland_portal|wayland_gnome_bridge|wayland_keyd|x11|windows" load.py edmc_hotkeys tests scripts` | Completed |
| 1.2 | Verified both required user signals are represented: startup warning path for auto-mode backend mismatch and settings-pane hint text for keyd-not-active in auto mode. | `rg -n "AutoHint|keyd is not active|restart EDMC|auto mode" load.py edmc_hotkeys tests` | Completed |
| 1.3 | Confirmed current invalid-mode handling path and warning strings, establishing baseline for consolidation change (removed modes will move from valid-set to normalize-and-warn behavior). | `rg -n "backend_mode|_VALID_BACKEND_MODES|falling back to auto|Invalid backend mode" load.py edmc_hotkeys/runtime_config.py` | Completed |
| 1.4 | Confirmed current release builder/test matrix still includes deprecated Wayland variants, establishing explicit scope for consolidation to keyd-only Wayland artifact output. | `rg -n "linux-wayland|linux-wayland-portal|linux-wayland-gnome-bridge|wayland_keyd" scripts/build_release_artifact.py tests/test_release_artifact_builder.py` | Completed |
| 1.5 | Confirmed hard-delete and verify-first policy text is present and consistent across requirements, acceptance criteria, and execution stages. | `rg -n "hard delete|verify references|Removal mode" docs/plans/WAYLAND_BACKEND_CONSOLIDATION_IMPLEMENTATION_PLAN.md` | Completed |

### Phase 2 Results (Completed)
| Stage | Result Summary | Validation Commands | Outcome |
| --- | --- | --- | --- |
| 2.1 | Confirmed selector and selector-focused tests still include deprecated Wayland backends; design update target is now explicitly scoped to removing portal/GNOME strategy branches and retaining only keyd for Wayland. | `rg -n "select_backend|detect_linux_session|wayland" edmc_hotkeys/backends/selector.py tests/test_backends.py` | Completed |
| 2.2 | Confirmed mode-validation set and load tests still treat removed modes as valid; design update target is explicitly scoped to normalize removed modes to `auto` with warning assertions. | `rg -n "_VALID_BACKEND_MODES|_resolve_backend_mode|Invalid backend mode" load.py tests/test_load_backend_mode.py` | Completed |
| 2.3 | Confirmed release-builder variant matrix and tests still include portal/GNOME Wayland artifacts and companion scripts; design update target is explicitly scoped to keyd-only Wayland artifact output and variant-test updates. | `rg -n "variant|linux-wayland|portal|gnome" scripts/build_release_artifact.py tests/test_release_artifact_builder.py` | Completed |
| 2.4 | Mapped test modules requiring updates for removed backend modes, selector behavior, config/runtime mode normalization, and release artifacts; identified affected suites (`test_backends`, `test_load_backend_mode`, `test_release_artifact_builder`, `test_runtime_config`). | `rg -n "wayland_portal|wayland_gnome_bridge|wayland_keyd" tests` | Completed |
| 2.5 | Confirmed cleanup sequencing is explicit in the plan: reference audit and runtime detachment precede hard deletion stages, followed by dedicated cleanup verification gates. | `rg -n "Phase 3|3.3|3.6|3.7|4.4|4.5" docs/plans/WAYLAND_BACKEND_CONSOLIDATION_IMPLEMENTATION_PLAN.md` | Completed |

### Phase 3 Results (Completed)
| Stage | Result Summary | Validation Commands | Outcome |
| --- | --- | --- | --- |
| 3.1 | Removed portal backend selection behavior from Wayland `auto` and explicit mode paths; auto now returns unavailable when keyd is missing instead of falling back. | `rg -n "wayland_portal|portal" load.py edmc_hotkeys/backends/selector.py` | Completed |
| 3.2 | Removed GNOME bridge backend selection behavior from Wayland `auto` and explicit mode paths; no runtime selection branch remains. | `rg -n "wayland_gnome_bridge|gnome_bridge|linux-wayland-gnome-bridge" load.py edmc_hotkeys/backends/selector.py` | Completed |
| 3.3 | Removed runtime import/export wiring for removed backends from active selector/package surfaces (`selector.py`, `backends/__init__.py`, `edmc_hotkeys/__init__.py`). | `rg -n "from .*wayland|import .*wayland|wayland_portal|wayland_gnome_bridge" edmc_hotkeys load.py` | Completed |
| 3.4 | Consolidated valid backend modes to `auto`, `wayland_keyd`, `x11`; removed modes now normalize to `auto` with warning logs in load path. | `source .venv/bin/activate && python -m pytest tests/test_load_backend_mode.py -q` | Completed (`8 passed`) |
| 3.5 | Removed deprecated Wayland artifact variants from release builder and switched `linux-wayland` artifact policy to keyd-only. | `source .venv/bin/activate && python -m pytest tests/test_release_artifact_builder.py -q` | Completed (`7 passed`) |
| 3.6 | Hard-deleted deprecated-backend scripts/docs and rewrote mixed docs/scripts to keyd-only guidance where still relevant. | `rg -n "wayland_portal|wayland_gnome_bridge|portal|gnome bridge" docs scripts` | Completed (remaining references limited to historical planning/context docs) |
| 3.7 | Hard-deleted deprecated backend source modules and companion source payloads after runtime detachment. | `rg -n "wayland_portal|wayland_gnome_bridge|gnome_bridge|portal" edmc_hotkeys` | Completed (no matches) |

### Phase 4 Results (Completed)
| Stage | Result Summary | Validation Commands | Outcome |
| --- | --- | --- | --- |
| 4.1 | Replaced backend/contract tests with three-backend matrix coverage and reran selector/mode test targets. | `source .venv/bin/activate && python -m pytest tests/test_backends.py tests/test_backend_contract.py -q` | Completed (`27 passed`) |
| 4.2 | Validated load/runtime mode normalization and keyd prefs alert integration tests against consolidated behavior. | `source .venv/bin/activate && python -m pytest tests/test_load_backend_mode.py tests/test_load_keyd_prefs_alerts.py -q` | Completed (`34 passed`) |
| 4.3 | Revalidated release artifact builder after variant consolidation. | `source .venv/bin/activate && python -m pytest tests/test_release_artifact_builder.py -q` | Completed (`7 passed`) |
| 4.4 | Confirmed no removed backend references remain outside historical planning docs. | `rg -n "wayland_portal|wayland_gnome_bridge|linux-wayland-portal|linux-wayland-gnome-bridge" . --glob '!docs/plans/**'` | Completed (no matches) |
| 4.5 | Confirmed no stale removed-mode references remain in active runtime/tests/scripts/docs surfaces (excluding historical plan docs). | `rg -n "wayland_portal|wayland_gnome_bridge" edmc_hotkeys load.py tests scripts docs --glob '!docs/plans/**'` | Completed (no matches) |
| 4.6 | Ran full regression suite after deletions/refactors and validated all tests pass. | `source .venv/bin/activate && python -m pytest -q` | Completed (`215 passed`) |

### Phase 5 Results (Completed)
| Stage | Result Summary | Validation Commands | Outcome |
| --- | --- | --- | --- |
| 5.1 | Confirmed removed-mode warnings and keyd-unavailable/restart messaging remain explicit and actionable in load/settings paths. | `rg -n "Invalid backend mode|falling back to auto|keyd is not active|restart EDMC" load.py edmc_hotkeys tests` | Completed |
| 5.2 | Confirmed config defaults/template and active docs no longer advertise removed backend modes; only `auto`, `wayland_keyd`, `x11` remain documented. | `rg -n "wayland_portal|wayland_gnome_bridge|wayland_keyd|mode" config_template.ini config.defaults.ini docs --glob '!docs/plans/**'` | Completed |
| 5.3 | Completed readiness/compliance regression checks with project `make check` pipeline (lint/docs/tests/compile). | `source .venv/bin/activate && make check` | Completed (all checks passed; `215 passed`) |
