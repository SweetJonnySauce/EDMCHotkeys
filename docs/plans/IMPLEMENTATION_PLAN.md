# Implementation Plan

Follow persona details in AGENTS.md
Document implementation results in the Implementation Results section.
After each stage is complete change status to Completed
When all stages are complete change the phase status to Completed
if something is not clear, ask clarifying questions

## Phase 1 — Architecture Decisions (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Finalize action registry API (fields, threading contract) | Completed |
| 1.2 | Decide backend selection strategy (Windows/X11/Wayland) | Completed |
| 1.3 | Define config storage format + migration story | Completed |

## Phase 2 — Core Plugin Skeleton (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Package plugin for action registry | Pending |
| 2.2 | Hotkey plugin scaffolding + logging | Pending |
| 2.3 | Dispatch pipeline (main-thread default) | Pending |
| 2.4 | Unit tests for registry + dispatch added alongside implementation | Pending |

## Phase 3 — Backends (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Windows backend (RegisterHotKey + fallback) | Pending |
| 3.2 | X11 backend (python-xlib) | Pending |
| 3.3 | Wayland backend (XDG portal) | Pending |
| 3.4 | Unit tests for backend adapters added alongside implementation | Pending |

## Phase 4 — Settings UI (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Binding table UI (hotkey / plugin / action) | Pending |
| 4.2 | Validation + conflict feedback | Pending |
| 4.3 | Persist & reload bindings | Pending |
| 4.4 | Unit tests for UI state + config serialization added alongside implementation | Pending |

## Phase 5 — Packaging + Docs (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 5.1 | Dependency bundling plan (packaged EDMC) | Pending |
| 5.2 | User setup docs (Wayland portal, X11) | Pending |

## Phase 6 — Tests + Verification (Status: Pending)
| Stage | Description | Status |
| --- | --- | --- |
| 6.1 | Unit tests for registry + dispatch | Pending |
| 6.2 | Backend smoke tests | Pending |
| 6.3 | Manual QA checklist | Pending |

# Implementation Results

## Phase 1 — Architecture Decisions
- Documented Action Registry API (normative), threading contract, and error handling in `docs/requirements-architecture-notes.md`.
- Documented backend selection strategy for Windows/X11/Wayland and session detection rules.
- Documented config storage schema, profile handling, and migration rules for v1 bindings.
