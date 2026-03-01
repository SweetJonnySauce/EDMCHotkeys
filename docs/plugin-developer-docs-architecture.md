# Plugin Developer Documentation Architecture

## Purpose
Define the documentation information architecture for plugin developers integrating with `EDMCHotkeys`.

## Canonical Document Set
| Document | Path | Primary audience | Owner | Status |
| --- | --- | --- | --- | --- |
| API reference | `docs/plugin-developer-api-reference.md` | Plugin developers and maintainers | Maintainers | Existing |
| Integration guide | `docs/register-action-with-edmchotkeys.md` | Plugin developers | Maintainers | Existing |
| Troubleshooting | `docs/plugin-developer-api-troubleshooting.md` | Plugin developers and support | Maintainers | Existing |
| Requirements baseline | `docs/plugin-developer-api-phase1-requirements.md` | Maintainers | Maintainers | Existing |
| Execution plan | `docs/plans/PLUGIN_DEVELOPER_API_DOCUMENTATION_PLAN.md` | Maintainers | Maintainers | Existing |

## Information Architecture Boundaries

### API Reference
Owns:
- exported symbols and signatures
- parameter/return semantics
- threading and dispatch contract statements
- backend capability contract notes

Does not own:
- long-form tutorials
- onboarding narrative
- symptom-first troubleshooting flow

### Integration Guide
Owns:
- quickstart setup and import pattern
- practical registration examples
- payload/cardinality usage patterns

Does not own:
- canonical signature source of truth
- exhaustive error matrix

### Troubleshooting Guide
Owns:
- symptom -> cause -> remediation lookup
- common log queries and interpretation
- escalation pointers

Does not own:
- normative API signature definitions
- onboarding tutorial content

## Section Templates

### API Reference Template
1. Scope and compatibility notes
2. Public symbol table (name, signature, source)
3. Per-symbol behavior details
4. Threading/dispatch guarantees
5. Backend capability notes
6. Return/failure semantics matrix
7. Related examples/troubleshooting links

### Integration Guide Template
1. Prerequisites
2. Minimal registration quickstart
3. Callback contract examples
4. Binding and payload examples
5. Backend-specific caveats
6. Verification steps
7. Troubleshooting entry points

### Troubleshooting Template
1. Symptom index
2. Symptom cards:
- observable behavior
- likely cause
- diagnostic checks
- remediation steps
3. Log query patterns
4. When to escalate
5. Related contract references

## Content Ownership Matrix
| Topic | Canonical owner | Secondary links |
| --- | --- | --- |
| Public signatures | API reference | Integration guide |
| Callback semantics | API reference | Integration guide, troubleshooting |
| Quickstart example | Integration guide | API reference |
| Binding JSON examples | Integration guide | API reference |
| Backend caveats | API reference | Integration guide, troubleshooting |
| Failure symptoms and fixes | Troubleshooting | API reference, integration guide |

## Cross-Link Contract
- Reference docs link to guide for runnable examples and to troubleshooting for failure modes.
- Integration guide links to reference for every normative signature/semantic claim.
- Troubleshooting links to reference for expected behavior and to guide for canonical setup patterns.
- No normative statement should exist in two places without one being explicitly marked as a summary.

## Navigation Entry Points
Target navigation:
1. `README.md` -> integration guide (`docs/register-action-with-edmchotkeys.md`)
2. integration guide -> API reference for strict contract details
3. integration guide/reference -> troubleshooting for failures

Required one-hop links:
- README developer section -> integration guide, API reference, troubleshooting
- Integration guide header -> API reference + troubleshooting
- API reference header -> integration guide + troubleshooting

## Validation Results (Phase 2)
- Role boundaries are explicitly non-overlapping.
- Canonical owner exists for each core developer question category.
- Navigation flow is defined and implementable without additional architecture decisions.
