# Linux User Setup (X11 and Wayland)

## Detect Your Session Type
Run:

```bash
echo "XDG_SESSION_TYPE=$XDG_SESSION_TYPE"
echo "DISPLAY=$DISPLAY"
echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
```

- X11 is typically `XDG_SESSION_TYPE=x11` with `DISPLAY` set.
- Wayland is typically `XDG_SESSION_TYPE=wayland` with `WAYLAND_DISPLAY` set.

## X11 Setup
1. Vendor `Xlib/` into plugin root:
   - `./scripts/vendor_xlib.sh`
2. Optionally force EDMC runtime interpreter:
   - `EDMC_PYTHON="$HOME/apps/EDMarketConnector/venv/bin/python3" ./scripts/vendor_xlib.sh`
3. Restart EDMC.

Expected result:
- `EDMC-Hotkeys` should select and start backend `linux-x11`.

## Wayland Setup
1. Ensure `xdg-desktop-portal` is running in the user session.
2. Ensure your desktop-specific portal backend is installed/running (GNOME/KDE/etc.).
3. Restart EDMC after portal service changes.

Useful checks:

```bash
systemctl --user status xdg-desktop-portal
```

Expected result with current implementation:
- `EDMC-Hotkeys` selects the Wayland backend wrapper.
- If no concrete GlobalShortcuts portal client is configured, hotkeys remain disabled and a warning is logged.

## Troubleshooting
- Open EDMC debug log and search for `EDMC-Hotkeys`.
- Check for:
  - backend selected/started messages.
  - backend unavailable reason.
  - settings frame/type errors in plugin preferences.

Example:

```bash
rg -n "EDMC-Hotkeys|backend|plugin_prefs|Failed for Plugin" ~/edmc-logs/EDMarketConnector-debug.log
```

## bindings.json Location
- Bindings are stored in:
  - `<EDMC plugin dir>/EDMC-Hotkeys/bindings.json`
- If missing, the plugin creates the file with defaults on startup.
