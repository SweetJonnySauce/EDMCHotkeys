# Plugin Developer API Documentation Plan

## Objective
Document a stable, discoverable integration contract for plugin developers using `EDMCHotkeys`.

## Scope
- Python module API used by plugin developers (`import EDMCHotkeys`).
- Action/binding integration contract, callback semantics, and backend capability notes.
- Documentation quality gates to prevent drift.

## Out of Scope
- Swagger/OpenAPI generation (this project API is Python module-based, not HTTP-based).

## Phase 1 — Requirements Baseline (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Define canonical API contract source and ownership | Completed |
| 1.2 | Define required docs set for plugin developers | Completed |
| 1.3 | Define behavior/compatibility guarantees to document | Completed |
| 1.4 | Define documentation verification requirements | Completed |
| 1.5 | Define discoverability and onboarding requirements | Completed |

### Phase 1 Artifacts
- Requirements baseline document: `docs/plugin-developer-api-phase1-requirements.md`

### Phase 1 Detailed Execution Plan

#### Stage 1.1 — Canonical API Contract Source and Ownership
Scope:
- Identify every public integration symbol exported by `EDMCHotkeys`.
- Establish code-level source of truth for signature and semantics.

Detailed tasks:
1.1.1 Create a public API symbol inventory from `__init__.py` exports and linked runtime types (`Action`, `Binding`).
1.1.2 Map each symbol to implementation location and canonical signature.
1.1.3 Define ownership rule: API signature changes require synchronized docs update in the same PR.
1.1.4 Define docstring minimum standard for public API symbols (purpose, params, return value, behavior caveats).

Deliverables:
- API inventory table (symbol, signature, source file, stability notes).
- Documented ownership/update rule for API surface.
- Docstring standard section for public symbols.

Validation:
- Manual cross-check of docs inventory against `__all__`.
- Manual cross-check that each public callable has a usable docstring.

Exit criteria:
- All exported symbols are documented with location/signature.
- Ownership/update rule and docstring standard are written and reviewable.

#### Stage 1.2 — Required Docs Set for Plugin Developers
Scope:
- Define the minimum doc set and boundaries so each page has one job.

Detailed tasks:
1.2.1 Define canonical API reference page scope (contract-only, low narrative).
1.2.2 Define integration guide scope (quickstart, examples, common patterns).
1.2.3 Define troubleshooting scope (symptoms, likely causes, fixes, log patterns).
1.2.4 Define cross-link map between reference, guide, and troubleshooting docs.

Deliverables:
- Documentation information architecture (IA) with page-level ownership.
- Section outline for each page.
- Link map for developer reading flow.

Validation:
- Dry-run newcomer flow from README to first successful action registration path.

Exit criteria:
- The 3-page doc set is scoped and non-overlapping.
- Navigation path is explicit and one-click from README.

#### Stage 1.3 — Behavior and Compatibility Guarantees
Scope:
- Record runtime behavior developers must rely on without reading source.

Detailed tasks:
1.3.1 Document callback contract (`payload`, `source`, optional `hotkey`) and dispatch semantics.
1.3.2 Document thread policy guarantees (`main` vs `worker`) and UI safety requirements.
1.3.3 Document backend capability differences and non-goals (for example Wayland side-specific limitations).
1.3.4 Document public API return-value semantics (`True`/`False` cases, warnings vs hard failures).
1.3.5 Document cardinality/payload validation expectations and common warning scenarios.

Deliverables:
- Behavior contract tables per API call.
- Capability matrix for backend-relevant integration expectations.
- Error/return semantics reference.

Validation:
- Cross-check behavior statements against existing tests in `tests/` and runtime code.

Exit criteria:
- Developers can infer expected behavior and failure modes from docs alone.
- Compatibility caveats are explicit and actionable.

#### Stage 1.4 — Documentation Verification Requirements
Scope:
- Define enforceable checks that catch docs drift early.

Detailed tasks:
1.4.1 Define link-checking requirement for markdown docs.
1.4.2 Define API drift check requirement (public symbols/signatures vs reference page).
1.4.3 Define snippet verification strategy for critical examples.
1.4.4 Define CI gate policy for docs failures (blocking vs warning).

Deliverables:
- CI requirements list for docs verification checks.
- Pass/fail policy for docs checks in PR workflows.

Validation:
- Confirm requirements are implementable with repo tooling and CI workflow style.

Exit criteria:
- Verification requirements are specific enough to implement in Phase 4 without reinterpretation.

#### Stage 1.5 — Discoverability and Onboarding Requirements
Scope:
- Ensure plugin developers can find the right docs quickly.

Detailed tasks:
1.5.1 Define required README entry points for plugin developers.
1.5.2 Define onboarding path for first integration (time-to-first-action flow).
1.5.3 Define stale-content policy for placeholders and deprecated instructions.
1.5.4 Define minimum “getting unstuck” path (where to go when examples fail).

Deliverables:
- README linking requirements.
- First-run onboarding flow specification.
- Stale-content and deprecation handling requirements.

Validation:
- Run a docs-only navigation check from README to troubleshooting.

Exit criteria:
- Developer navigation path is linear, short, and explicit.
- Legacy/TBD language is explicitly disallowed for active integration paths.

### Phase 1 Sequencing and Milestone Gate
Execution order:
1. 1.1 API source/ownership
2. 1.2 docs set boundaries
3. 1.3 behavior guarantees
4. 1.4 verification requirements
5. 1.5 discoverability/onboarding

Milestone gate to close Phase 1:
- All Stage 1.x deliverables are documented.
- Requirements are concrete enough for implementation without further requirement debates.
- Phase 2 can start with no unresolved Phase 1 blockers.

### 1.1 Canonical API Contract Source
Requirement:
- Treat the Python public module API as the contract (`EDMCHotkeys` export surface), not an HTTP schema.
- Keep signatures, types, and semantics anchored to code (`__all__`, type hints, docstrings, public dataclasses).

Acceptance criteria:
- A reference doc maps every public symbol to code location and signature.
- Any public API change requires docs update in the same change.

### 1.2 Required Docs Set
Requirement:
- Maintain one canonical API reference page (signature-level contract).
- Maintain one practical integration guide (quickstart + real examples).
- Keep troubleshooting focused on integration failures plugin developers hit first.

Acceptance criteria:
- Plugin developers can register at least one action from docs alone.
- Docs cover callback args, threading policy, binding ownership/filtering, and invocation helpers.

### 1.3 Behavior + Compatibility Guarantees
Requirement:
- Explicitly document runtime guarantees and caveats:
  - main-thread vs worker-thread callback execution behavior
  - backend capability differences (for example Wayland tier limitations)
  - return-value/error semantics for public APIs
  - cardinality/payload validation expectations

Acceptance criteria:
- A developer can predict behavior without reading implementation code.
- Capability limitations are documented with actionable alternatives.

### 1.4 Documentation Verification Requirements
Requirement:
- Add lightweight CI checks to reduce docs drift:
  - broken link checks
  - fenced example/snippet verification where practical
  - guardrails that docs and public API signatures stay aligned

Acceptance criteria:
- CI fails on broken docs links.
- CI catches at least basic signature drift for documented public API symbols.

### 1.5 Discoverability + Onboarding
Requirement:
- README must link directly to plugin developer docs (reference + guide).
- Avoid stale placeholders or “instructions TBD” where integration docs exist.

Acceptance criteria:
- New developers can find integration docs from README in one click.
- README setup paths and linked docs remain consistent.

## Phase 2 — Documentation Architecture (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Finalize docs IA (reference vs guide vs troubleshooting split) | Completed |
| 2.2 | Choose generation approach for API reference (manual vs automated from code) | Completed |
| 2.3 | Define versioning/changelog policy for API docs | Completed |

### Phase 2 Artifacts
- Documentation IA map and ownership/templates: `docs/plugin-developer-docs-architecture.md`
- API reference strategy decision: `docs/architecture/plugin_developer_api_reference_strategy.md`
- API versioning and changelog policy: `docs/plugin-developer-api-versioning-policy.md`

### Phase 2 Detailed Execution Plan

#### Stage 2.1 — Finalize Documentation IA
Scope:
- Convert Phase 1 doc-set requirements into a concrete architecture with stable boundaries and ownership.

Detailed tasks:
2.1.1 Define canonical file paths for API reference, integration guide, troubleshooting, and supporting index pages.
2.1.2 Define section templates per doc type (reference table format, guide tutorial flow, troubleshooting symptom layout).
2.1.3 Define content ownership matrix (which doc owns signatures, examples, compatibility caveats, and remediation steps).
2.1.4 Define cross-link contract between docs to avoid duplicated normative statements.
2.1.5 Define navigation entry points from README and in-doc "next step" links.

Deliverables:
- Documentation IA map (doc -> purpose -> owner -> required sections).
- Section templates for each doc type.
- Cross-link ownership matrix to prevent drift/duplication.

Validation:
- Dry-run reading flow for a new plugin developer and a maintainer performing API updates.
- Confirm each major question has a single canonical answer location.

Exit criteria:
- No unresolved overlap between reference, guide, and troubleshooting docs.
- A developer can reach all required integration info in <= 3 clicks from README.

#### Stage 2.2 — API Reference Generation Strategy
Scope:
- Decide how the API reference is produced and maintained (manual, generated, or hybrid).

Detailed tasks:
2.2.1 Evaluate manual-only approach against current API size and change frequency.
2.2.2 Evaluate generated approach from `__all__`, signatures, and docstrings.
2.2.3 Define hybrid approach options (generated symbol/signature table + manually curated semantics/examples).
2.2.4 Choose toolchain and implementation target (script location, output path, CI invocation).
2.2.5 Define failure behavior when docs and API drift (blocking check expectations).

Decision criteria:
- Accuracy: minimizes signature drift risk.
- Maintainability: low overhead for routine API changes.
- Readability: output remains usable for plugin developers.
- EDMC compatibility: no heavy dependency burden for local contributor workflows.

Deliverables:
- Written architecture decision with chosen strategy and rejected alternatives.
- Initial implementation contract for generation script/checks (inputs, outputs, invariants).

Validation:
- Run a paper test on one synthetic API change to confirm chosen approach would detect/update drift correctly.

Exit criteria:
- Generation strategy is unambiguous and implementable in Phase 3/4 without further design debate.
- Decision record includes rollback path if the chosen strategy proves too costly.

#### Stage 2.3 — API Documentation Versioning and Changelog Policy
Scope:
- Define how API documentation tracks compatibility and release history.

Detailed tasks:
2.3.1 Define API compatibility labels (`stable`, `experimental`, `deprecated`) and where they appear.
2.3.2 Define semantic change classes for docs updates (`breaking`, `behavioral`, `additive`, `clarification`).
2.3.3 Define changelog entry requirements for API-affecting changes.
2.3.4 Define deprecation policy (notice format, replacement guidance, removal timeline expectations).
2.3.5 Define release checklist integration so API doc/version updates are not optional.

Deliverables:
- API docs versioning policy section.
- Changelog policy and template for API-related entries.
- Deprecation and removal guidance standard.

Validation:
- Apply policy to 2-3 historical changes and verify classification is consistent.

Exit criteria:
- Maintainers have a deterministic rule set for documenting and classifying API changes.
- Release process has explicit API docs/version checkpoints.

### Phase 2 Sequencing and Milestone Gate
Execution order:
1. 2.1 IA finalization
2. 2.2 generation strategy decision
3. 2.3 versioning/changelog policy

Milestone gate to close Phase 2:
- IA map and templates are documented and approved.
- API reference generation strategy decision is recorded.
- Versioning/changelog policy is documented and usable by maintainers.
- Phase 3 can start with no open architecture questions for docs delivery.

### Phase 2 Implementation Results
#### Stage 2.1 Results
- Defined canonical document set paths and ownership boundaries for reference, guide, and troubleshooting docs.
- Added section templates for each doc type to standardize future authoring.
- Added cross-link contract and navigation entry-point map to enforce one canonical answer per topic.

#### Stage 2.2 Results
- Recorded architecture decision to use a hybrid reference model (generated signatures + curated semantics).
- Documented alternatives considered (manual-only, fully generated) and explicit tradeoffs.
- Defined implementation contract for generation/check tooling and CI drift behavior.

#### Stage 2.3 Results
- Defined compatibility labels (`stable`, `experimental`, `deprecated`) for API docs.
- Defined semantic change classes (`breaking`, `behavioral`, `additive`, `clarification`).
- Defined changelog and deprecation requirements plus release-checklist integration points.

## Phase 3 — Initial Delivery (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Publish canonical API reference page | Completed |
| 3.2 | Update/standardize integration guide examples | Completed |
| 3.3 | Add README cross-links and onboarding path | Completed |

### Phase 3 Artifacts
- API reference: `docs/plugin-developer-api-reference.md`
- Troubleshooting guide: `docs/plugin-developer-api-troubleshooting.md`
- Updated integration guide: `docs/register-action-with-edmchotkeys.md`
- Updated onboarding/links in project root: `README.md`

### Phase 3 Detailed Execution Plan

#### Stage 3.1 — Publish Canonical API Reference Page
Scope:
- Deliver the first canonical plugin developer API reference based on Phase 1 requirements and Phase 2 architecture decisions.

Detailed tasks:
3.1.1 Create `docs/plugin-developer-api-reference.md` with the Phase 2 reference template structure.
3.1.2 Populate exported symbol/signature table from current public API surface (`__all__`, `Action`, `Binding`).
3.1.3 Add per-symbol behavior notes including return/failure semantics and callback argument contract.
3.1.4 Add thread/dispatch guarantees and backend capability caveats in dedicated sections.
3.1.5 Add compatibility labels for public symbols per versioning policy.
3.1.6 Add forward links to integration guide and troubleshooting docs.

Deliverables:
- `docs/plugin-developer-api-reference.md` (initial published version).
- Public symbol coverage matrix showing all exported symbols are documented.

Validation:
- Manual symbol parity check against `__init__.__all__`.
- Manual signature parity check against `load.py` wrappers and dataclass definitions.
- Editorial review for clarity and non-duplication with integration guide.

Exit criteria:
- Every public API symbol has a documented signature and behavior summary.
- Reference page is designated canonical for signatures and semantics.

#### Stage 3.2 — Update and Standardize Integration Guide Examples
Scope:
- Bring the integration guide into alignment with canonical reference semantics and Phase 2 IA boundaries.

Detailed tasks:
3.2.1 Update guide header to explicitly position it as practical usage content, not normative signature source.
3.2.2 Normalize quickstart example to current public API and callback contract.
3.2.3 Standardize examples for thread policy, payload usage, cardinality, and Wayland capability caveats.
3.2.4 Add explicit "Reference" and "Troubleshooting" links at top and bottom of guide.
3.2.5 Remove or rewrite any wording that duplicates normative API contract statements better owned by reference docs.

Deliverables:
- Updated `docs/register-action-with-edmchotkeys.md`.
- Example consistency pass notes (what was changed and why).

Validation:
- Manual walkthrough: follow guide from import to first successful action registration.
- Verify all code snippets match reference signatures/defaults.

Exit criteria:
- Guide examples are executable in principle and aligned with current API semantics.
- Guide stays practical and defers normative claims to API reference.

#### Stage 3.3 — Add README Cross-Links and Onboarding Path
Scope:
- Make developer documentation discoverable from project entry points in one hop.

Detailed tasks:
3.3.1 Add a "Plugin Developer API" section in `README.md`.
3.3.2 Link README directly to API reference, integration guide, troubleshooting guide, and plan docs where appropriate.
3.3.3 Remove/replace stale placeholder language that conflicts with current developer doc availability.
3.3.4 Add concise onboarding sequence in README (where to start, what to read next).
3.3.5 Verify README links are relative-path stable and consistent with repository layout.

Deliverables:
- Updated `README.md` with developer docs navigation block.
- README onboarding path mapping to Phase 1/2 architecture.

Validation:
- Manual click-through test from README to all required developer docs.
- Link sanity check with local markdown preview and repository path review.

Exit criteria:
- Developers can reach integration docs from README in a single click.
- No active-path "instructions TBD" remains for plugin developer API onboarding.

### Phase 3 Sequencing and Milestone Gate
Execution order:
1. 3.1 publish API reference
2. 3.2 align integration guide
3. 3.3 wire README onboarding links

Milestone gate to close Phase 3:
- API reference, integration guide updates, and README onboarding links are published.
- Symbol/signature parity is manually verified and documented.
- Developer docs navigation is complete and consistent with IA contracts.
- Phase 4 can start with delivery artifacts in place for automated verification.

### Phase 3 Implementation Results
#### Stage 3.1 Results
- Published canonical API reference with:
  - exported symbol/signature table
  - `Action` and `Binding` dataclass contracts
  - per-API behavior details
  - callback, threading/dispatch, backend capability, and failure semantics sections
- Added explicit links from reference docs to practical guide and troubleshooting docs.

#### Stage 3.2 Results
- Updated integration guide to prioritize practical onboarding and examples.
- Reduced normative signature duplication by pointing canonical behavior/signature definitions to API reference.
- Kept end-to-end registration and binding examples aligned to current API semantics.

#### Stage 3.3 Results
- Added a dedicated "Plugin Developer API" section in `README.md` with one-hop links to:
  - integration guide
  - API reference
  - troubleshooting
  - documentation plan/status
- Replaced stale GNOME Wayland "instructions TBD" language with direct setup doc links.

## Phase 4 — Verification + Maintenance (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Add CI docs checks (links/signature drift/snippets) | Completed |
| 4.2 | Define “docs update required” checklist for API-touching changes | Completed |
| 4.3 | Run first maintenance pass to reconcile stale guidance | Completed |

### Phase 4 Artifacts
- Link checker script: `scripts/check_docs_links.py`
- API parity checker script: `scripts/check_plugin_api_docs.py`
- Snippet checker script: `scripts/check_doc_snippets.py`
- Build wiring for docs checks: `Makefile` (`docs-check`, included in `check`)
- PR checklist template: `.github/pull_request_template.md`
- Review checklist rubric: `docs/plugin-developer-api-review-checklist.md`
- Maintenance pass notes: `docs/plugin-developer-docs-maintenance-pass-phase4.md`

### Phase 4 Detailed Execution Plan

#### Stage 4.1 — Add CI Documentation Checks
Scope:
- Implement automated checks that enforce docs integrity and API-doc parity.

Detailed tasks:
4.1.1 Add markdown link-check command to CI workflow for `docs/` and `README.md`.
4.1.2 Add API drift check script to validate exported symbols/signatures vs API reference content.
4.1.3 Add snippet validation for canonical examples (syntax parse and basic import/signature sanity where practical).
4.1.4 Define blocking vs non-blocking check classes in CI job output.
4.1.5 Document local developer commands to run all docs checks before PR submission.

Deliverables:
- CI workflow updates for docs checks.
- API drift check script under `scripts/`.
- Contributor-facing command list in docs or README.

Validation:
- Introduce controlled failure cases (broken link, stale symbol signature) and confirm CI fails as expected.
- Confirm pass path on current docs baseline.

Exit criteria:
- CI enforces link and API parity checks for developer docs.
- Maintainers can reproduce checks locally with documented commands.

#### Stage 4.2 — Define and Integrate Docs-Update Checklist
Scope:
- Add explicit review gates so API-touching PRs cannot merge without required docs updates.

Detailed tasks:
4.2.1 Create PR checklist section for API-affecting changes (reference, guide, troubleshooting, release notes).
4.2.2 Define applicability rules for checklist (what counts as API-affecting).
4.2.3 Add checklist location and ownership (PR template and/or contributing docs).
4.2.4 Add reviewer rubric for validating compatibility labels and change classification.
4.2.5 Cross-link checklist to versioning/changelog policy.

Deliverables:
- Docs-update checklist artifact in repository workflow docs/templates.
- Reviewer rubric for API documentation completeness checks.

Validation:
- Apply checklist to one recent API-related PR or simulated diff and verify deterministic outcomes.

Exit criteria:
- API-touching changes have a documented, enforced docs-review path.
- Reviewers have clear yes/no criteria for documentation completeness.

#### Stage 4.3 — First Maintenance Reconciliation Pass
Scope:
- Run a full docs consistency pass after delivery and verification wiring.

Detailed tasks:
4.3.1 Re-scan all plugin developer docs for duplicate/conflicting normative statements.
4.3.2 Reconcile terminology across reference, guide, troubleshooting, README, and plan artifacts.
4.3.3 Remove stale or transitional wording that no longer applies after Phase 3 delivery.
4.3.4 Validate all intra-doc links and path references remain accurate.
4.3.5 Record maintenance findings and follow-up items for next planning cycle.

Deliverables:
- Reconciled docs set with resolved inconsistencies.
- Maintenance pass notes (issues found, fixes applied, deferred items).

Validation:
- Manual end-to-end read path from README -> guide -> reference -> troubleshooting.
- CI docs checks pass after reconciliation updates.

Exit criteria:
- No known conflicting normative statements across developer docs.
- Docs set is internally consistent and verification-backed.

### Phase 4 Sequencing and Milestone Gate
Execution order:
1. 4.1 CI docs checks
2. 4.2 docs-update checklist integration
3. 4.3 maintenance reconciliation pass

Milestone gate to close Phase 4:
- CI checks for links/API drift/snippets are active and enforced.
- Docs-update checklist is integrated into review workflow.
- First maintenance pass has been completed and documented.
- Plugin developer docs process is in steady-state maintenance mode.

### Phase 4 Implementation Results
#### Stage 4.1 Results
- Implemented blocking documentation checks:
  - local markdown link validation (`check_docs_links.py`)
  - API reference parity against exported symbols/signatures (`check_plugin_api_docs.py`)
  - fenced snippet syntax checks for canonical docs (`check_doc_snippets.py`)
- Wired checks into `make docs-check` and included `docs-check` in `make check` so CI enforces them via existing workflow.
- Added contributor-visible local command list in `README.md`.

#### Stage 4.2 Results
- Added repository PR template with plugin developer API docs checklist at `.github/pull_request_template.md`.
- Added reusable reviewer rubric/checklist at `docs/plugin-developer-api-review-checklist.md`.
- Cross-linked checklist with versioning/changelog policy in `docs/plugin-developer-api-versioning-policy.md`.

#### Stage 4.3 Results
- Completed first maintenance reconciliation pass and recorded findings/fixes/deferred items in:
  - `docs/plugin-developer-docs-maintenance-pass-phase4.md`
- Reconciled onboarding/validation discoverability by adding docs-check commands in `README.md`.
- Validation commands executed successfully:
  - `python3 scripts/check_docs_links.py`
  - `python3 scripts/check_plugin_api_docs.py`
  - `python3 scripts/check_doc_snippets.py`
  - `make docs-check`

## Tests To Run For This Planning Milestone
- `source .venv/bin/activate && python -m pytest -k "docs or register-action or hotkey_plugin"` (optional; unchanged behavior expected).
- Manual doc review for internal consistency and link targets.
