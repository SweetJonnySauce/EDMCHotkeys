# GNOME Companion Extension Lifecycle Notes

Status: Phase 3 implementation note (2026-02-26)

## Objective
Define extension lifecycle behavior so keybinding capture is deterministic and isolated from plugin stability.

## Lifecycle Model
1. `enable`:
   - Construct helper bridge boundary (`helper_bridge.js`).
   - Initialize binding registry.
   - Connect `accelerator-activated` signal on `global.display`.
   - Load configured bindings from `~/.config/edmc-hotkeys/companion-bindings.json`.
   - Register accelerators and map actions -> binding ids.
2. Runtime activation:
   - On accelerator signal, resolve mapped binding id.
   - Invoke helper sender process for protocol-v1 emission.
3. `disable`:
   - Disconnect signal handler.
   - Ungrab all accelerators.
   - Clear in-memory registry state.

## Isolation Rules
- Extension startup errors should log and fail local activation path only.
- EDMC plugin process must remain unaffected if extension/helper is unavailable.
- Helper invocation is process-isolated per activation and does not run on plugin thread.

## Registration Invariants
- Replacing bindings always clears prior accelerator registrations first.
- Disabled/invalid bindings are ignored.
- Unregistration is attempted for all tracked actions during disable.

## Operational Notes
- Config source is file-based in Phase 3 baseline.
- Install script seeds/updates config via `scripts/export_companion_bindings.py`.
- This note supplements:
  - `docs/architecture/gnome_bridge_architecture.md`
  - `docs/plans/GNOME_WAYLAND_BRIDGE_HARDENING_IMPLEMENTATION_PLAN.md`
