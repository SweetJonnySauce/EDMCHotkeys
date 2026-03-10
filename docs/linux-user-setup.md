# Linux User Setup (X11 and Wayland keyd)

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
- Release builds include `Xlib/` and `six.py` for X11 support.
- Restart EDMC after installing/updating the plugin.

Expected result:
- `EDMCHotkeys` selects backend `linux-x11`.

## Wayland keyd Setup
1. Install and start keyd.
2. Verify keyd is active:
   ```bash
   systemctl is-active keyd
   ```
3. Install EDMCHotkeys keyd integration:
   ```bash
   ./scripts/install_keyd_integration.sh --install
   ```
4. Export/apply generated config:
   ```bash
   ./scripts/install_keyd_integration.sh --apply
   ```
5. Restart EDMC.

Expected result:
- `EDMCHotkeys` selects backend `linux-wayland-keyd`.
- Side-specific modifiers (for example `LCtrl`, `RShift`) are supported.

## Troubleshooting
- Open EDMC debug log and search for `EDMCHotkeys`.
- Check for backend selected/started messages and keyd integration warnings.

Example:

```bash
rg -n "EDMCHotkeys|backend|keyd|plugin_prefs|Failed for Plugin" ~/edmc-logs/EDMarketConnector-debug.log
```

## bindings.json Location
- Bindings are stored in `<EDMC plugin dir>/EDMCHotkeys/bindings.json`.
- If missing, the plugin creates the file with defaults on startup.
