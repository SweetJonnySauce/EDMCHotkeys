# GNOME Companion Compatibility Matrix

Status: Phase 5 alpha rollout input updated (2026-02-27)

## Scope
Companion artifact track (`extension -> helper -> plugin bridge`) compatibility targets and current verification state.
This matrix tracks GNOME Wayland bridge coverage only; it does not represent non-GNOME Wayland portal-path validation.

## Legend
- `Validated`: local smoke completed for install + activate + rollback (including interactive runtime checks).
- `Planned`: target environment not yet exercised.
- `Unsupported`: explicitly out of support scope.

## Matrix
| Ubuntu | GNOME Shell | Session | Status | Notes |
| --- | --- | --- | --- | --- |
| 24.04.3 LTS | 46.0 | Wayland | Validated | Scripted + interactive QA matrix complete (`QA-4.3-01` through `QA-4.3-10`), including activation/disable behavior, mode-switch restart validation, and stale runtime/socket recovery. |
| 22.04 LTS | 42.x | Wayland | Planned | Validate API differences for accelerator grab/allowKeybinding behavior. |
| 24.04 LTS | 46.x | X11 | Unsupported | Companion path targets GNOME Wayland only; use X11 backend for Xorg sessions. |
| 24.10 / 25.xx | 47.x+ | Wayland | Planned | Validate metadata shell-version compatibility and extension runtime behavior. |

## Required Smoke Cases Per Environment
1. Install:
   - `./scripts/install_gnome_bridge_companion.sh --enable`
2. Verify artifact and config:
   - `./scripts/verify_gnome_bridge_companion.sh`
3. Export bindings:
   - `./scripts/export_companion_bindings.py --bindings ./bindings.json --output ~/.config/edmc-hotkeys/companion-bindings.json`
4. Activation:
   - Press registered accelerator and confirm EDMC action dispatch in `EDMarketConnector-debug.log`.
5. Rollback:
   - `./scripts/uninstall_gnome_bridge_companion.sh`
   - Confirm plugin remains non-fatal with configured backend fallback.

## Known Limitations
- Companion extension config is file-driven; no dedicated EDMC UI for extension config in current baseline.
- GNOME Shell API behavior can vary by version; compatibility rows marked `Planned` require environment-specific validation.
- Extension/helper failures are isolated from plugin startup by design, but activation path depends on local extension runtime state.

## Rollout Guidance Input (Phase 5)
- Minimum candidate for alpha: Ubuntu 24.04 + GNOME 46 Wayland (validated in Phase 4 matrix evidence).
- Keep `wayland_gnome_bridge` mode opt-in until at least one additional GNOME version row is validated.
- Current Stage 5.2 status: deferred until an additional GNOME Wayland test environment is available.

## Rollout Artifacts
- [GNOME_WAYLAND_BRIDGE_ALPHA_ROLLOUT_CHECKLIST.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/release/GNOME_WAYLAND_BRIDGE_ALPHA_ROLLOUT_CHECKLIST.md)
- [GNOME_WAYLAND_BRIDGE_ISSUE_TRIAGE_TEMPLATE.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/release/GNOME_WAYLAND_BRIDGE_ISSUE_TRIAGE_TEMPLATE.md)
- [GNOME_WAYLAND_BRIDGE_GA_DECISION_RECORD.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/release/GNOME_WAYLAND_BRIDGE_GA_DECISION_RECORD.md)

## Linked QA Evidence
- [GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/qa/GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md)
