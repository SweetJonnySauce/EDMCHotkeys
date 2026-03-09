# EDMCHotkeys Release Notes

## v0.5.0 - Refactor Wayland Backend

Summary:
- Wayland backend has been refactored to use keyd. Other Wayland backends based on dbus have been removed.

## v0.1.0 - Initial Release
- See README

## v0.0.0 - Rename to EDMCHotkeys (Hard Change)

Summary:
- Canonical plugin/import name is now `EDMCHotkeys`.
- Legacy import path `EDMC-Hotkeys.load` is unsupported.
- Consumer documentation now uses direct import style (`import EDMCHotkeys as hotkeys`).

Operator guidance:
- Use a single plugin folder during cutover.
- Do not keep both `EDMC-Hotkeys` and `EDMCHotkeys` folders installed at once.

Migration action for plugin developers:
- Replace `importlib.import_module("EDMC-Hotkeys.load")` with `import EDMCHotkeys as hotkeys`.

## v0.0.0 - GNOME Wayland Phase 5 Rollout Artifacts

Summary:
- Added Phase 5 rollout/stabilization documentation artifacts for alpha operations and GA policy tracking.
- Phase 5 status is now `In Progress` with Stage 5.1 and Stage 5.3 documented as complete deliverables.

Added artifacts:
- `docs/release/GNOME_WAYLAND_BRIDGE_ALPHA_ROLLOUT_CHECKLIST.md`
- `docs/release/GNOME_WAYLAND_BRIDGE_ISSUE_TRIAGE_TEMPLATE.md`
- `docs/release/GNOME_WAYLAND_BRIDGE_GA_DECISION_RECORD.md`

Policy update:
- GA promotion remains deferred pending broader beta environment evidence.
- Bridge sender path remains opt-in and current `auto` behavior is unchanged.

## v0.0.0 - GNOME Wayland Companion Phase 4 QA Completion

Summary:
- Completed Phase 4 manual/integration QA for the GNOME Wayland companion bridge path.
- `docs/qa/GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md` now records `QA-4.3-01` through `QA-4.3-10` as `Pass`.

Validation highlights:
- Extension active/disabled dispatch behavior verified in live GNOME Wayland session.
- Backend mode switching verified across EDMC restarts (`auto`, `wayland_keyd`, `x11`).
- Stale runtime-dir/socket recovery verified with hardened permission restoration.

## v0.0.0 - Wayland Tier 1 Generic Modifier Support

Summary:
- Tier 1 backends now support non-side-specific modifiers (`Ctrl`, `Alt`, `Shift`, `Win`) for hotkey bindings.
- Side-specific modifiers (`LCtrl`, `RCtrl`, etc.) remain Tier 2-only and are auto-disabled on Tier 1 backends.

Behavior changes:
- Valid on Tier 1:
  - `Ctrl+M`
  - `Ctrl+Shift+F1`
  - `Alt+F5`
- Invalid:
  - mixed same-family tokens such as `Ctrl+LCtrl+M` or `Shift+RShift+F2`

Migration guidance:
- If a Wayland user has side-specific bindings, replace them with generic equivalents:
  - `LCtrl+LShift+F1` -> `Ctrl+Shift+F1`
  - `RCtrl+M` -> `Ctrl+M`

Diagnostics:
- Auto-disable logs should reference only side-specific bindings on Tier 1 backends.
- Generic bindings should no longer be auto-disabled by side-specific capability checks.
