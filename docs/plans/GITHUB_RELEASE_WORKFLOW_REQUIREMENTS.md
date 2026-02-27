# GitHub Release Workflow Requirements

Status: Implemented
Owner: EDMC-Hotkeys
Last Updated: 2026-02-27

## Goal
Define requirements for a GitHub release workflow that produces platform-specific plugin artifacts.

## Scope
- Release workflow for EDMC-Hotkeys plugin artifacts.
- Platform-specific packaging with vendored runtime dependencies.
- Automated release checks before publishing artifacts.

## Non-Goals
- Changing backend behavior or runtime architecture.
- Replacing existing local/manual packaging scripts beyond what is required for CI release automation.

## Artifact Strategy
Target artifacts (long-term):
1. Windows artifact.
2. Linux X11 artifact.
3. Linux Wayland artifact (`wayland`, no companion).
4. Linux Wayland GNOME artifact (`wayland_gnome`, with companion).

Current iteration:
- Implement Linux X11 + Linux Wayland + Linux Wayland GNOME artifacts.
- Implement Windows artifact packaging.

## Phase and Stage Requirements
| Phase | Stage | Requirement | Status |
| --- | --- | --- | --- |
| R1 | 1.1 | Define artifact naming/versioning convention | Completed |
| R1 | 1.2 | Define release trigger policy (`tag`, manual dispatch, or both) | Completed |
| R2 | 2.1 | Linux X11 artifact must vendor dependencies via `scripts/vendor_xlib.sh` | Completed |
| R2 | 2.2 | Linux Wayland artifact (`wayland`) must vendor dependencies via `scripts/vendor_dbus_next.sh` and exclude companion | Completed |
| R2 | 2.3 | Linux Wayland GNOME artifact (`wayland_gnome`) must vendor `dbus_next` and include companion payloads/scripts | Completed |
| R2 | 2.4 | Windows artifact packaging included in workflow | Completed |
| R3 | 3.1 | Workflow must run release gate checks before packaging (`make check`) | Completed |
| R3 | 3.2 | Workflow must fail if required vendored modules are missing | Completed |
| R3 | 3.3 | Workflow must produce checksums for each artifact | Completed |
| R4 | 4.1 | Workflow must publish artifacts to a live GitHub Release (no draft gate) | Completed |
| R4 | 4.2 | Workflow must capture release notes source from root `RELEASE_NOTES.md` | Completed |
| R5 | 5.1 | Add operator documentation for release procedure and rollback | Completed |

## Functional Requirements

### FR-1: Workflow Triggers
- Must support release execution from a controlled trigger (tag and/or manual dispatch).
- Must be runnable from default branch for dry-run validation.
- Tag trigger must use strict semantic tag format: `vX.Y.Z` (initial target: `v0.1.0`).
- Manual dispatch without a git tag must create a GitHub pre-release using an explicit input version.

### FR-2: Linux X11 Artifact
- Packaging step must invoke `scripts/vendor_xlib.sh`.
- Artifact must contain vendored runtime modules required by X11 path:
  - `Xlib/`
  - `six.py`
- Release check must validate those files exist in the packaged artifact.

### FR-3: Linux Wayland Artifact (`wayland`)
- Packaging step must invoke `scripts/vendor_dbus_next.sh`.
- Artifact must contain vendored runtime module required by Wayland portal path:
  - `dbus_next/`
- Release check must validate vendored module exists in the packaged artifact.
- Artifact must exclude companion payloads/scripts.

### FR-3b: Linux Wayland GNOME Artifact (`wayland_gnome`)
- Packaging step must invoke `scripts/vendor_dbus_next.sh`.
- Artifact must contain vendored runtime module:
  - `dbus_next/`
- Artifact must include companion extension/helper payloads.
- Artifact must include required GNOME bridge runtime/install scripts.
- Release check must validate companion payload and script presence.

### FR-4: Artifact Isolation
- Linux X11 and Linux Wayland artifacts must be built in isolated work dirs to avoid dependency bleed-through.
- Each artifact must include only expected vendored dependency set for its platform target.

### FR-5: Quality Gates
- Must pass `make check` before packaging/publishing.
- Must fail release if packaging checks or vendoring checks fail.

### FR-6: Publish Outputs
- Must publish platform-specific artifacts to GitHub Release:
  - Linux artifacts: `tar.gz`
  - Windows artifact: `zip`
- Must publish checksum file(s) for all artifacts.
- Workflow must fail if a release already exists for the target tag.

### FR-7: Packaging Include/Exclude Policy
- Packaging must use explicit include/exclude rules (not repo-root blanket copy).
- Required global excludes for plugin artifacts:
  - `docs/`
  - `tests/`
  - `AGENTS.md`
  - `.git/`
  - `.github/`
  - `.venv/`
  - `.pytest_cache/`
  - `__pycache__/`
  - `dist/`
  - `requirements-dev.txt`
  - `Makefile`
  - `bindings.json`
- Recommended additional excludes:
  - `*.pyc`
  - `.mypy_cache/`
  - `.ruff_cache/`
  - development/packaging-only scripts under `scripts/` (except required runtime/install scripts listed below)
- Packaging checks must fail if excluded files are present in any final artifact.

### FR-8: Platform-Specific Artifact Content Rules
- Linux X11 artifact:
  - Must include X11 vendored runtime dependencies (`Xlib/`, `six.py`).
  - Must exclude bridge/Wayland payloads:
    - `dbus_next/`
    - `companion/`
    - `scripts/gnome_bridge_send.py`
    - `scripts/install_gnome_bridge_companion.sh`
    - `scripts/uninstall_gnome_bridge_companion.sh`
    - `scripts/verify_gnome_bridge_companion.sh`
    - `scripts/export_companion_bindings.py`
- Linux Wayland artifact (`wayland`, no companion):
  - Must include Wayland vendored runtime dependency (`dbus_next/`).
  - Must exclude companion extension/helper payloads and GNOME bridge install scripts:
    - `companion/`
    - `scripts/gnome_bridge_send.py`
    - `scripts/install_gnome_bridge_companion.sh`
    - `scripts/uninstall_gnome_bridge_companion.sh`
    - `scripts/verify_gnome_bridge_companion.sh`
    - `scripts/export_companion_bindings.py`
  - Must exclude X11 vendored dependencies:
    - `Xlib/`
    - `six.py`
- Linux Wayland GNOME artifact (`wayland_gnome`, with companion):
  - Must include Wayland vendored runtime dependency (`dbus_next/`).
  - Must include companion extension/helper payloads:
    - `companion/`
  - Must exclude X11 vendored dependencies:
    - `Xlib/`
    - `six.py`
  - Must include required GNOME bridge runtime/install scripts:
    - `scripts/gnome_bridge_send.py`
    - `scripts/install_gnome_bridge_companion.sh`
    - `scripts/uninstall_gnome_bridge_companion.sh`
    - `scripts/verify_gnome_bridge_companion.sh`
    - `scripts/export_companion_bindings.py`
  - Must include a single companion user doc in artifact root:
    - `COMPANION_SETUP.md`

### FR-9: Artifact Layout
- Each released plugin artifact must unpack into a single top-level folder:
  - `EDMC-Hotkeys/`

### FR-10: Pre-release Versioning (Manual Dispatch)
- Manual dispatch without tag must create a pre-release.
- Pre-release version string must use semantic pre-release suffix form:
  - `vX.Y.Z-rc.N` (for example `v0.1.0-rc.1`).
- Workflow must reject manual pre-release version inputs that do not match `vX.Y.Z-rc.N`.

### FR-11: Workflow Topology
- Use a single workflow file:
  - `.github/workflows/release.yml`
- The single workflow must handle all current artifact variants (`linux-x11`, `linux-wayland`, `linux-wayland-gnome`, `windows`).

## Artifact Naming (Proposed)
- `EDMC-Hotkeys-linux-x11-v<version>.tar.gz`
- `EDMC-Hotkeys-linux-wayland-v<version>.tar.gz`
- `EDMC-Hotkeys-linux-wayland-gnome-v<version>.tar.gz`
- `EDMC-Hotkeys-windows-v<version>.zip`
- `SHA256SUMS.txt`

## Acceptance Criteria
- Linux X11 artifact includes vendored `python-xlib` dependencies and passes release checks.
- Linux Wayland artifact (`wayland`) includes vendored `dbus-next` dependency, excludes companion payloads/scripts, and passes release checks.
- Linux Wayland GNOME artifact (`wayland_gnome`) includes vendored `dbus-next` dependency plus companion payloads/scripts and passes release checks.
- Workflow publishes the three Linux artifacts + checksums to a GitHub release.
- Workflow publishes the Windows artifact + checksums to a GitHub release.

## Risks and Constraints
- Dependency vendoring scripts depend on interpreter availability and pip resolution.
- Artifact correctness depends on strict packaging isolation per platform target.
- Environment mismatch (session/backend assumptions) can cause false positives if checks are too runtime-dependent.

## Resolved Decisions (Initial Q&A)
1. Trigger policy: both tag push and manual dispatch.
2. Release publish mode: create live release immediately (no draft gate).
3. Source policy: any branch/tag.
4. Artifact format: Linux `tar.gz`; Windows `zip`.
5. Wayland variants:
   - `wayland`: no companion payload.
   - `wayland_gnome`: includes companion extension/helper payload.
   - Companion payload is required only for GNOME Wayland bridge path.
6. Dependency isolation: strict (X11 excludes `dbus_next`; Wayland excludes `Xlib/six.py`).
7. Version authority: git tag.
8. Integrity output: checksums only (no signing for now).
9. Release notes source: use release notes file; target location should be root-level `RELEASE_NOTES.md`.
10. Windows artifact included in workflow output.
11. Linux X11 packaging excludes bridge artifacts/scripts.
12. `bindings.json` is excluded from release artifacts (generated/managed at runtime).
13. Release notes migration to root `RELEASE_NOTES.md` is in-scope now.
14. Tag format is strict semver tag `vX.Y.Z` (starting with `v0.1.0`).
15. Manual-dispatch run without tag creates pre-release using input version.
16. Release job fails if target tag release already exists.
17. Each artifact must unpack to single top-level `EDMC-Hotkeys/` folder.
18. Linux X11 artifact exclusion policy is strict and must fail if bridge payload files are present.
19. Manual-dispatch pre-release versions use `-rc.N` suffix form (for example `v0.1.0-rc.1`).
20. Linux Wayland GNOME artifact ships exactly one companion user doc (`COMPANION_SETUP.md`).
21. Release automation uses one workflow file: `.github/workflows/release.yml`.

## Remaining Clarifications
- None.

## Next Step
- Convert this requirements doc into an implementation plan for `.github/workflows/release.yml` and supporting scripts.
