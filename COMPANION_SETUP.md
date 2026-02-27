# EDMC-Hotkeys Companion Setup (GNOME Wayland)

This guide is shipped with the `linux-wayland-gnome` release artifact.

## Scope
Use this only for GNOME Wayland companion mode.

## Prerequisites
- EDMC-Hotkeys plugin installed.
- EDMC launched with bridge mode enabled:
  - `EDMC_HOTKEYS_BACKEND_MODE=wayland_gnome_bridge`
  - `EDMC_HOTKEYS_GNOME_BRIDGE=1`

## Install Companion
From the plugin folder:

```bash
./scripts/install_gnome_bridge_companion.sh --enable
./scripts/verify_gnome_bridge_companion.sh
```

## Export Bindings

```bash
./scripts/export_companion_bindings.py \
  --bindings ./bindings.json \
  --output ~/.config/edmc-hotkeys/companion-bindings.json
```

## Enable Extension

```bash
gnome-extensions enable edmc-hotkeys@edcd
gnome-extensions info edmc-hotkeys@edcd
```

Expected state:
- `Enabled: Yes`
- `State: ACTIVE`

## Quick Validation
Press a configured hotkey and confirm EDMC log shows:
- `Hotkey pressed ... source=backend:linux-wayland-gnome-bridge`

## Rollback

```bash
gnome-extensions disable edmc-hotkeys@edcd
./scripts/uninstall_gnome_bridge_companion.sh --remove-config
```

To run without bridge mode:

```bash
EDMC_HOTKEYS_BACKEND_MODE=auto EDMC_HOTKEYS_GNOME_BRIDGE=0 edmarketconnector
```
