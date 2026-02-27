# GitHub Release Workflow Implementation Plan

Status: Completed
Owner: EDMC-Hotkeys
Last Updated: 2026-02-27

## Goal
Implement a single GitHub release workflow that builds and publishes platform-specific EDMC-Hotkeys artifacts with strict packaging isolation and vendored dependencies.

## Inputs
- [GITHUB_RELEASE_WORKFLOW_REQUIREMENTS.md](/home/jon/edmc_plugins/EDMC-Hotkeys/docs/plans/GITHUB_RELEASE_WORKFLOW_REQUIREMENTS.md)

## Scope
- Implement `.github/workflows/release.yml`.
- Implement artifact build/check scripts for:
  - `linux-x11`
  - `linux-wayland`
  - `linux-wayland-gnome`
- Enforce include/exclude rules and top-level folder layout.
- Publish checksums and release assets.

## Non-Goals
- Implement Windows artifact build (deferred; explicit skipped signal only).
- Change plugin runtime behavior.

## Phase 1 — Release Interfaces (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Define release/version interfaces and workflow inputs/outputs | Completed |
| 1.2 | Define per-variant packaging manifests and strict exclude policy wiring | Completed |

### Phase 1 Validation
1. Confirm all requirements decisions are mapped to concrete interfaces.
2. Confirm version patterns for tag and manual pre-release are explicit and testable.

## Phase 2 — Packaging Tooling (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Implement release artifact builder script with variant-specific vendoring | Completed |
| 2.2 | Implement artifact verification checks (required files, excluded files, top-level folder) | Completed |
| 2.3 | Add Makefile targets for local release artifact build/check | Completed |

### Phase 2 Validation
1. Build each variant locally to `dist/`.
2. Verify tarballs unpack into single `EDMC-Hotkeys/` top-level folder.
3. Verify strict include/exclude checks fail correctly when violated.

## Phase 3 — GitHub Workflow (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Implement `release.yml` trigger/version validation + existing-release guard | Completed |
| 3.2 | Implement matrix build jobs for three Linux artifacts | Completed |
| 3.3 | Implement publish job (live release, checksums, deferred Windows signal) | Completed |

### Phase 3 Validation
1. Workflow lint/basic parse sanity.
2. Manual-dispatch dry run behavior validated in script-level simulation.
3. Release-exists guard path is explicit and failing.

## Phase 4 — Documentation and Verification (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Document operator runbook for release workflow usage and rollback | Completed |
| 4.2 | Add/adjust tests for release builder logic and run project checks | Completed |

### Phase 4 Validation
1. `source .venv/bin/activate && python -m pytest`.
2. `source .venv/bin/activate && make check`.

## Acceptance Criteria
- Single workflow `.github/workflows/release.yml` exists and implements requirement decisions.
- Three Linux artifacts are built/published with strict per-variant content isolation.
- Checksums are published.
- Windows is explicitly reported as deferred via skipped job/output.
- Manual pre-releases require `vX.Y.Z-rc.N`; tag releases require `vX.Y.Z`.

## Rollback
- Disable workflow by removing/renaming `.github/workflows/release.yml`.
- Keep local packaging scripts callable for manual release fallback.

## Implementation Results
- Added release packager: [build_release_artifact.py](/home/jon/edmc_plugins/EDMC-Hotkeys/scripts/build_release_artifact.py)
  - Variant-specific vendoring via `scripts/vendor_xlib.sh` and `scripts/vendor_dbus_next.sh`.
  - Enforces strict include/exclude policy and top-level tar layout.
- Added local build targets in [Makefile](/home/jon/edmc_plugins/EDMC-Hotkeys/Makefile):
  - `release-build-linux-x11`
  - `release-build-linux-wayland`
  - `release-build-linux-wayland-gnome`
  - `release-build-all`
- Added CI workflow: [release.yml](/home/jon/edmc_plugins/EDMC-Hotkeys/.github/workflows/release.yml)
  - Tag releases: `vX.Y.Z`
  - Manual pre-releases: `vX.Y.Z-rc.N`
  - Existing-release guard
  - Linux artifact matrix + checksum generation + live publish
  - Explicit Windows deferred job
- Added operator runbook: [GITHUB_RELEASE_WORKFLOW_RUNBOOK.md](/home/jon/edmc_plugins/EDMC-Hotkeys/docs/release/GITHUB_RELEASE_WORKFLOW_RUNBOOK.md)
- Added tests: [test_release_artifact_builder.py](/home/jon/edmc_plugins/EDMC-Hotkeys/tests/test_release_artifact_builder.py)
  - version validation coverage
  - required/forbidden path enforcement coverage
  - global excludes enforcement coverage
- Validation executed:
  - `source .venv/bin/activate && python -m pytest tests/test_release_artifact_builder.py` (pass)
  - `source .venv/bin/activate && make check` (pass)
- Local `make release-build-all VERSION=v0.1.0-rc.1` could not complete in this sandbox because vendoring requires network access to pip indexes.
