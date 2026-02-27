# GNOME Wayland Bridge Alpha Rollout Checklist

Status: Active for Phase 5 Stage 5.1
Owner: EDMC-Hotkeys
Last Updated: 2026-02-27

## Scope
Controlled alpha rollout for GNOME Wayland bridge sender path with explicit opt-in only.

## Entry Criteria
- [ ] Phase 4 QA matrix is fully passing (`QA-4.3-01` through `QA-4.3-10`).
- [ ] Companion install/verify/export/uninstall scripts pass locally.
- [ ] No unresolved critical startup/dispatch regressions in current branch.
- [ ] Rollback instructions validated in docs.

## Rollout Configuration
- [ ] Launch EDMC with bridge opt-in mode:
  - `EDMC_HOTKEYS_BACKEND_MODE=wayland_gnome_bridge`
  - `EDMC_HOTKEYS_GNOME_BRIDGE=1`
- [ ] Confirm extension status `Enabled: Yes` and `State: ACTIVE`.
- [ ] Confirm backend startup line identifies `linux-wayland-gnome-bridge`.

## Evidence Collection
Capture and archive the following for each alpha environment run:
- [ ] Backend selection/startup log lines.
- [ ] At least one positive dispatch line (`Hotkey pressed ... source=backend:linux-wayland-gnome-bridge`).
- [ ] One disable/recovery scenario result (extension disabled or stale runtime artifact recovery).
- [ ] Fallback behavior evidence when bridge path is unavailable/non-selected.

## Failure Taxonomy
Classify issues using `docs/release/GNOME_WAYLAND_BRIDGE_ISSUE_TRIAGE_TEMPLATE.md`:
- Startup safety regression
- Dispatch correctness regression
- Sender sync/runtime incompatibility
- Install/docs/operational UX defect

## Exit Criteria for Stage 5.1
- [ ] Alpha users can complete install/enable/dispatch/rollback via docs alone.
- [ ] No unresolved high-severity startup/dispatch defects remain in alpha scope.
- [ ] Evidence set is sufficient to prioritize Stage 5.2 beta hardening.

## Rollback Commands
- Disable companion extension:
  - `gnome-extensions disable edmc-hotkeys@edcd`
- Stop using bridge mode and relaunch EDMC:
  - `EDMC_HOTKEYS_BACKEND_MODE=auto EDMC_HOTKEYS_GNOME_BRIDGE=0 edmarketconnector`
- Optional companion uninstall:
  - `./scripts/uninstall_gnome_bridge_companion.sh --remove-config`
