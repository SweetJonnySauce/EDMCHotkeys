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
3. Vendor `dbus-next` into plugin root:
   - `./scripts/vendor_dbus_next.sh`
4. Optionally force EDMC runtime interpreter:
   - `EDMC_PYTHON="$HOME/apps/EDMarketConnector/venv/bin/python3" ./scripts/vendor_dbus_next.sh`
5. Restart EDMC after portal service changes.

Useful checks:

```bash
systemctl --user status xdg-desktop-portal
python -c "import dbus_next; print('dbus-next OK')"
```

Expected result with current implementation:
- `EDMC-Hotkeys` selects backend `linux-wayland-portal`.
- If portal/runtime prerequisites are available, backend starts and Wayland registrations can succeed.
- If prerequisites are missing, backend remains non-fatal and logs explicit unavailability reasons (for example missing `WAYLAND_DISPLAY` or `dbus-next`).

### GNOME Wayland Bridge Setup (Portal Fallback Path)
Use this when GNOME Wayland does not expose `org.freedesktop.portal.GlobalShortcuts`.

1. Start EDMC with bridge mode enabled:
   - `EDMC_HOTKEYS_GNOME_BRIDGE=1 EDMarketConnector`
2. Optional socket override:
   - `EDMC_HOTKEYS_GNOME_BRIDGE_SOCKET=/tmp/edmc_hotkeys_gnome_bridge.sock`
3. Keep sender auto-sync enabled (default):
   - `EDMC_HOTKEYS_GNOME_BRIDGE_AUTOSYNC=1`

Expected result:
- `EDMC-Hotkeys` selects backend `linux-wayland-gnome-bridge`.
- Active bridge bindings are auto-synced into GNOME custom keybindings.
- Changing bindings in EDMC-Hotkeys updates GNOME shortcuts automatically.

### Tier 1 Modifier Guidance (Wayland)
- Tier 1 (Wayland portal/bridge) supports:
  - key-only bindings: `M`
  - generic modifiers: `Ctrl+M`, `Alt+F5`, `Ctrl+Shift+L`
- Tier 1 does not support side-specific modifiers:
  - `LCtrl+...`, `RCtrl+...`, `LShift+...`, `RShift+...`, `LAlt+...`, `RAlt+...`, `LWin+...`, `RWin+...`
  - these are auto-disabled with diagnostics when backend capability is non-side-specific
- Mixed same-family modifiers are invalid:
  - `Ctrl+LCtrl+M` (invalid)
  - `Shift+RShift+F2` (invalid)

If you are migrating an old side-specific binding for Wayland Tier 1:
- `LCtrl+LShift+F1` -> `Ctrl+Shift+F1`
- `RCtrl+M` -> `Ctrl+M`

## Troubleshooting
- Open EDMC debug log and search for `EDMC-Hotkeys`.
- Check for:
  - backend selected/started messages.
  - backend unavailable reason.
  - settings frame/type errors in plugin preferences.
  - feature-flag state for platform-specific behavior (see `docs/feature-flags.md`).

Example:

```bash
rg -n "EDMC-Hotkeys|backend|Auto-disabled binding|plugin_prefs|Failed for Plugin" ~/edmc-logs/EDMarketConnector-debug.log
```

## bindings.json Location
- Bindings are stored in:
  - `<EDMC plugin dir>/EDMC-Hotkeys/bindings.json`
- If missing, the plugin creates the file with defaults on startup.
