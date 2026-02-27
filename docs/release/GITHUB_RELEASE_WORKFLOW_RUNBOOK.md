# GitHub Release Workflow Runbook

## Scope
Use this runbook to publish EDMC-Hotkeys release artifacts through `.github/workflows/release.yml`.

## Release Variants
- `linux-x11`
- `linux-wayland`
- `linux-wayland-gnome`
- `windows`

All artifacts unpack to a single top-level `EDMC-Hotkeys/` folder.

## Trigger Modes
1. Tag release:
   - Push tag: `vX.Y.Z` (example: `v0.1.0`)
2. Manual pre-release:
   - Run workflow dispatch with version input: `vX.Y.Z-rc.N` (example: `v0.1.0-rc.1`)

## Pre-Flight Local Validation
From repo root:

```bash
source .venv/bin/activate
make check
make release-build-all VERSION=v0.1.0-rc.1
```

Expected output:
- `dist/EDMC-Hotkeys-linux-x11-v0.1.0-rc.1.tar.gz`
- `dist/EDMC-Hotkeys-linux-wayland-v0.1.0-rc.1.tar.gz`
- `dist/EDMC-Hotkeys-linux-wayland-gnome-v0.1.0-rc.1.tar.gz`
- `dist/EDMC-Hotkeys-windows-v0.1.0-rc.1.zip`

## CI Release Behavior
1. `prepare`:
   - Validates version format.
   - Fails if a release already exists for the target version/tag.
2. `quality-gate`:
   - Runs `make check`.
3. `build-artifacts`:
   - Builds each artifact in matrix jobs using `scripts/build_release_artifact.py`.
4. `publish`:
   - Downloads all artifacts.
   - Generates `SHA256SUMS.txt`.
   - Publishes GitHub release using root `RELEASE_NOTES.md`.

## Rollback
If a release workflow change must be disabled quickly:
1. Revert/rename `.github/workflows/release.yml` in a follow-up commit.
2. Use local fallback packaging:
   - `make release-build-all VERSION=vX.Y.Z-rc.N`
3. Publish artifacts manually if necessary.
