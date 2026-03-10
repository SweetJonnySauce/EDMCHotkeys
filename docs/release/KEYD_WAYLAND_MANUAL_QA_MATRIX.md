# keyd Wayland Manual QA Matrix

Status: Active for Phase 5 Stage 5.1  
Last Updated: 2026-03-07

## Purpose
- Track manual-only QA coverage for `wayland_keyd` behavior on real EDMC Wayland sessions.
- Separate local automated evidence from real-environment validation gates.

## Environment Matrix
| Env ID | Session | Init System | keyd Status | Coverage State | Notes |
| --- | --- | --- | --- | --- | --- |
| E1 | Wayland | systemd | active | Pending manual run | Required for systemd apply command and reload flow. |
| E2 | Wayland | non-systemd | active | Pending manual run | Required for fallback restart guidance validation. |

## Scenario Matrix
| Scenario ID | Scenario | Expected Result | Evidence Source | Status |
| --- | --- | --- | --- | --- |
| Q1 | Startup in `auto` with healthy keyd | Backend selected is `wayland_keyd` with reason log | `tests/test_backends.py::test_select_backend_auto_logs_selection_reason_for_keyd` | Automated pass |
| Q2 | Startup in `auto` with unhealthy keyd | Fallback backend selected without crash | `tests/test_backends.py::test_select_backend_wayland_strategy` | Automated pass |
| Q3 | Export on startup/settings save with unchanged bindings | No rewrite and no reload-required re-prompt | `tests/test_keyd_export.py::test_export_keyd_bindings_skips_rewrite_when_hash_unchanged` | Automated pass |
| Q4 | Export with duplicate chord rows | First-wins conflict warning emitted | `tests/test_keyd_export.py::test_export_keyd_bindings_conflict_is_first_wins` | Automated pass |
| Q5 | Export state with major schema mismatch | Warning emitted and state rebuilt | `tests/test_keyd_export.py::test_export_keyd_bindings_rebuilds_state_on_major_schema_mismatch` | Automated pass |
| Q6 | Manual apply command in systemd environment | Command uses plugin-local generated file and `/etc/keyd/edmchotkeys.conf` target | Pending manual log capture in EDMC runtime | Pending manual run |
| Q7 | Manual fallback guidance in non-systemd environment | Generic restart one-liner is logged when init command cannot be determined | Pending manual log capture in EDMC runtime | Pending manual run |
| Q8 | Side-specific binding dispatch in live EDMC Wayland session | Bound action triggers successfully from keyd-generated mapping | Pending manual EDMC runtime validation | Pending manual run |
| Q9 | Invalid binding row handling in real bindings data | Invalid rows skipped and standardized warning template appears in EDMC log | Pending manual log capture in EDMC runtime | Pending manual run |

## Manual Execution Notes
- Manual scenarios `Q6`-`Q9` are release gates and are intentionally not marked complete from this workspace.
- Automated scenarios were validated by repository test runs on 2026-03-07.
