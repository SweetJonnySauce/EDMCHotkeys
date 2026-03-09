# GitHub Release Workflow Runbook

## Scope
Use this runbook to publish EDMCHotkeys release artifacts through `.github/workflows/release.yml`.

## Release Variants
- `linux-x11`
- `linux-wayland`
- `windows`

All artifacts unpack to a single top-level `EDMCHotkeys/` folder.

## Rename Cutover Guard
- This plugin is on the `EDMCHotkeys` naming surface.
- Do not run with both `EDMC-Hotkeys/` and `EDMCHotkeys/` plugin folders present in the same EDMC plugins directory.

## Trigger Modes
1. Tag release:
   - Push tag: `v<semver>` (examples: `v0.1.0`, `v0.5.0-alpha-1`, `v0.5.0-beta.1`)
2. Manual pre-release:
   - Run workflow dispatch with version input: `v<semver-prerelease>` (example: `v0.1.0-rc.1`)

## Version Surfaces
- Canonical runtime plugin version is stored in `VERSION` as plain semver (no `v` prefix), for example `0.5.0-alpha-1`.
- Release tag/version surfaces use the same semver value with a `v` prefix, for example `v0.5.0-alpha-1`.
- Artifact filenames use the tag form (`v...`).

## Pre-Flight Local Validation
From repo root:

```bash
source .venv/bin/activate
make check
make release-build-all VERSION=v0.1.0-rc.1
```

Expected output:
- `dist/EDMCHotkeys-linux-x11-v0.1.0-rc.1.tar.gz`
- `dist/EDMCHotkeys-linux-wayland-v0.1.0-rc.1.tar.gz`
- `dist/EDMCHotkeys-windows-v0.1.0-rc.1.zip`

## CI Release Behavior
1. `prepare`:
   - Validates version via canonical semver parser (`scripts/resolve_release_version.py`).
   - For manual dispatch, requires a prerelease version.
2. `quality-gate`:
   - Runs `make check`.
3. `build-artifacts`:
   - Builds each artifact in matrix jobs using `scripts/build_release_artifact.py`.
4. `publish`:
   - Downloads all artifacts.
   - Generates `SHA256SUMS.txt`.
   - Extracts only the matching release-notes section from root `RELEASE_NOTES.md`.
   - Scans a `git archive` source tarball with VirusTotal (requires repo secret `VT_API_KEY`).
   - Writes `dist/vtscan.txt` containing the VirusTotal analysis/report URL(s).
   - Creates or updates the GitHub release for the version tag.

## Rollback
If a release workflow change must be disabled quickly:
1. Revert/rename `.github/workflows/release.yml` in a follow-up commit.
2. Use local fallback packaging:
   - `make release-build-all VERSION=v<semver>`
3. Publish artifacts manually if necessary.
