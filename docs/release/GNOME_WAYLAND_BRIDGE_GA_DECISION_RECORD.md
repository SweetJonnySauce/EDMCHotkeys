# GNOME Wayland Bridge GA Decision Record

Status: Draft decision record
Owner: EDMCHotkeys
Last Updated: 2026-02-27

## Decision Date
2026-02-27

## Decision
- GA promotion is deferred.
- Bridge sender path remains opt-in for now.
- `auto` mode policy remains unchanged from current behavior.

## Rationale
- Phase 4 QA is complete and green on Ubuntu 24.04.3 + GNOME 46 Wayland.
- Additional GNOME/Ubuntu environment coverage is still pending for beta confidence.
- Keeping opt-in minimizes regression risk while rollout evidence broadens.

## Current Policy
- Recommended bridge opt-in launch:
  - `EDMC_HOTKEYS_BACKEND_MODE=wayland_gnome_bridge`
  - `EDMC_HOTKEYS_GNOME_BRIDGE=1`
- Default `auto` behavior remains as currently documented.

## Promotion Criteria to GA
- At least one additional GNOME Wayland matrix row validated.
- No unresolved `S0`/`S1` bridge issues.
- Beta defect trend acceptable for supported rows.
- Stable install/rollback/troubleshoot guidance validated by real-user evidence.

## Rollback Position
- Bridge path remains optional and non-fatal.
- Users can return to non-bridge behavior by disabling bridge mode/env flags.

