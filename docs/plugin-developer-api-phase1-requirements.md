# Plugin Developer API Requirements (Phase 1)

## Purpose
This document captures the implemented Phase 1 requirements baseline for plugin developer API documentation.

## Stage 1.1 — Canonical API Contract Source and Ownership

### Public API Surface Inventory
Source of truth:
- Export surface in `__all__`: `__init__.py:26`.
- Runtime implementations: `load.py` and dataclasses in `edmc_hotkeys`.

| Symbol | Canonical signature | Source location | Contract notes |
| --- | --- | --- | --- |
| `Action` | `Action(id, label, plugin, callback, params_schema=None, thread_policy="main", enabled=True, cardinality="single")` | `edmc_hotkeys/registry.py:145` | Dataclass contract for action registration metadata. |
| `Binding` | `Binding(id, hotkey, action_id, payload=None, enabled=True, plugin="")` | `edmc_hotkeys/plugin.py:24` | Dataclass contract for binding data returned/invoked through API. |
| `register_action` | `register_action(action: Action) -> bool` | `load.py:124` | Returns `False` when plugin is not started or registration fails. |
| `list_actions` | `list_actions() -> list[Action]` | `load.py:131` | Returns empty list when plugin is not started. |
| `list_bindings` | `list_bindings(plugin_name: str) -> list[Binding]` | `load.py:138` | Case-insensitive plugin match; returns pretty hotkey text; empty name returns `[]`. |
| `get_action` | `get_action(action_id: str) -> Action \| None` | `load.py:167` | Returns `None` when plugin not started or action missing. |
| `invoke_action` | `invoke_action(action_id: str, payload=None, source="hotkey", hotkey=None) -> bool` | `load.py:174` | Delegates to guarded registry dispatch; returns success/failure. |
| `invoke_bound_action` | `invoke_bound_action(binding: Binding, source="hotkey") -> bool` | `load.py:186` | Invokes a binding target if enabled and resolvable. |

### Ownership and Change Policy
Requirements:
- Any change to exported symbols in `__all__` requires same-PR updates to:
  - API reference docs
  - integration guide examples affected by the change
  - changelog/release notes when behavior is user-visible
- API behavior changes must include or update tests covering new semantics.

### Public API Docstring Standard
Minimum required content for each public callable/dataclass:
- one-sentence intent summary
- argument meanings and defaults
- return value semantics (`True`/`False`/`None` conditions)
- thread/dispatch caveats (main vs worker where relevant)
- known backend capability caveats if behavior depends on backend

Implementation note:
- Exported wrappers in `load.py` currently rely on external docs rather than per-function docstrings; Phase 3 documentation delivery should align code docstrings to this standard.

## Stage 1.2 — Required Docs Set for Plugin Developers

### Required Documentation Set
| Doc | Path | Role |
| --- | --- | --- |
| API reference | `docs/plugin-developer-api-reference.md` | Canonical signature and behavior contract. |
| Integration guide | `docs/register-action-with-edmchotkeys.md` | Quickstart and end-to-end examples. |
| Troubleshooting guide | `docs/plugin-developer-api-troubleshooting.md` | Error symptoms, likely causes, remediation steps. |

### Information Architecture Boundaries
- Reference page:
  - no long tutorials
  - definitive signatures and semantics
- Integration guide:
  - implementation examples and patterns
  - links back to reference for strict contract details
- Troubleshooting:
  - symptom-first lookup
  - log query examples and fixes

### Link Map (Target Flow)
1. README developer section -> integration guide.
2. Integration guide -> API reference for detailed contract checks.
3. Integration guide and API reference -> troubleshooting for failures.

## Stage 1.3 — Behavior and Compatibility Guarantees to Document

### Public API Behavior Contract
| API | Guaranteed behavior |
| --- | --- |
| `register_action` | Rejects duplicate IDs and invalid thread policies; first registration wins. |
| `list_actions` | Preserves registration order. |
| `list_bindings(plugin_name)` | Requires non-empty plugin name; case-insensitive plugin ownership filter. |
| `get_action` | Returns exact registered action or `None`. |
| `invoke_action` | Guarded dispatch; catches callback errors and returns `False` on failure. |
| `invoke_bound_action` | Skips disabled bindings and returns `False` when skipped/failing. |

### Callback and Dispatch Guarantees
- Callback kwargs contract:
  - always: `payload`, `source`
  - conditional: `hotkey` only when callback supports it
- Thread policy:
  - `main`: routed through main-thread dispatch executor
  - `worker`: routed through worker-thread execution path

### Backend Capability Matrix (Developer-Facing)
| Backend path | Side-specific modifiers | Developer guidance |
| --- | --- | --- |
| Windows | Supported | `LCtrl`/`RCtrl` style bindings supported. |
| Linux X11 | Supported | Side-specific and generic modifiers supported. |
| Linux Wayland keyd | Supported | Side-specific and generic modifiers supported. |

### Return/Failure Semantics
- Missing action ID: warning + `False`.
- Disabled action: warning + `False`.
- Callback exception: logged exception + `False`.
- Plugin not started: wrapper calls return `False`, `[]`, or `None` by API type.

## Stage 1.4 — Documentation Verification Requirements

### CI Requirements
- Broken-link check for markdown docs is required.
- Public API drift check is required:
  - validate docs reference symbols/signatures against `__all__` and callable signatures.
- Critical code snippets in integration docs should be parse-checked or smoke-tested.

### Gate Policy
- Broken links: blocking failure.
- API drift: blocking failure.
- Snippet checks: blocking for canonical snippets; warning-only for optional/examples marked non-executable.

### Implementation Targets (Phase 4)
- Add script for API drift check under `scripts/`.
- Add docs-check job(s) in CI workflow(s).
- Add minimal contributor checklist requiring doc updates for API-touching changes.

## Stage 1.5 — Discoverability and Onboarding Requirements

### README Entry-Point Requirements
- README must include a plugin developer section with direct links to:
  - integration guide
  - API reference
  - troubleshooting guide
- README must not contain active-path placeholders such as “instructions TBD” for developer integration paths.

### Onboarding Path Requirements
Target first-run path:
1. Import `EDMCHotkeys`.
2. Register one action.
3. Bind action to one hotkey.
4. Verify callback invocation and logs.
5. Use troubleshooting guide if expected callback does not fire.

### Stale Guidance Policy
- Any renamed path/function must be updated across README + docs in same PR.
- Deprecated guidance must be removed or explicitly marked with replacement path.

## Phase 1 Completion Gate
Phase 1 is complete when:
- API inventory exists and maps to code.
- Ownership policy and docstring standard are documented.
- Docs set boundaries and link map are defined.
- Behavior/capability/failure guarantees are explicitly documented.
- CI verification requirements and onboarding/discoverability requirements are explicit.
