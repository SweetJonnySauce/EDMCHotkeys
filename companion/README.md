# EDMC-Hotkeys Companion Artifacts

This directory contains optional GNOME Wayland companion artifacts for the
`linux-wayland-gnome-bridge` backend.

Current layout:
- `gnome-extension/`:
  - GNOME Shell extension skeleton for key capture lifecycle.
- `helper/`:
  - Companion sender helper that emits hardened protocol-v1 activation payloads.

These artifacts are intentionally separate from plugin runtime modules under
`edmc_hotkeys/` so they can be installed/uninstalled independently.
