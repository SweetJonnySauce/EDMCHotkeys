# Developer Notes

## Setting The Next Version

Use this flow for each release/prerelease.

1. Update `VERSION` (no `v` prefix), for example:
   - `0.5.0-alpha-2`
   - `0.5.0-beta-1`
   - `0.5.0`

2. Add a matching section header in `RELEASE_NOTES.md`:
   - Preferred exact header: `## v0.5.0-alpha-2`
   - For prereleases, base-version fallback is supported (for example `## v0.5.0`), but exact match is recommended.

3. Run local validation:
   ```bash
   source .venv/bin/activate
   make check
   make release-build-all
   ```
   `make release-build-all` automatically uses `VERSION` and builds artifacts with a `v`-prefixed tag version.

4. Commit and tag:
   ```bash
   git add VERSION RELEASE_NOTES.md
   git commit -m "Release v0.5.0-alpha-2"
   git tag v0.5.0-alpha-2
   git push origin main --tags
   ```

## Version Surface Rules

- Runtime/plugin version source of truth: `VERSION` (`X.Y.Z...`, no `v`)
- Release tag/version surface: `vX.Y.Z...` (with `v`)
- Artifact filenames use tag form (`v...`)

