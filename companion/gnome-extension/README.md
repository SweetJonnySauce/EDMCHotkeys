# GNOME Shell Companion Extension

This extension is the Stage-3 companion artifact path for GNOME Wayland:

- Captures global accelerators in GNOME Shell.
- Invokes helper sender (`gnome_bridge_companion_send.py`) for each activation.
- Helper emits protocol-v1 authenticated payloads to the plugin bridge socket.

Directory structure:
- `edmc-hotkeys@edcd/metadata.json`
- `edmc-hotkeys@edcd/extension.js`
- `edmc-hotkeys@edcd/helper_bridge.js`
- `edmc-hotkeys@edcd/bindings.sample.json`

Notes:
- Runtime binding config defaults to:
  - `~/.config/edmc-hotkeys/companion-bindings.json`
- This is a companion artifact, not loaded by EDMC directly.
- Install/rollback workflow is managed via scripts in `scripts/`.
