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
- `EDMCHotkeys` should select and start backend `linux-x11`.

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
- `EDMCHotkeys` selects backend `linux-wayland-portal`.
- If portal/runtime prerequisites are available, backend starts and Wayland registrations can succeed.
- If prerequisites are missing, backend remains non-fatal and logs explicit unavailability reasons (for example missing `WAYLAND_DISPLAY` or `dbus-next`).

### GNOME Wayland Bridge Setup (Portal Fallback Path)
Use this when GNOME Wayland does not expose `org.freedesktop.portal.GlobalShortcuts`.

1. Start EDMC with bridge mode enabled:
   - `EDMC_HOTKEYS_BACKEND_MODE=wayland_gnome_bridge EDMC_HOTKEYS_GNOME_BRIDGE=1 EDMarketConnector`
2. Optional socket override:
   - `EDMC_HOTKEYS_GNOME_BRIDGE_SOCKET=/abs/path/bridge.sock`
3. Keep sender auto-sync enabled (default):
   - `EDMC_HOTKEYS_GNOME_BRIDGE_AUTOSYNC=1`
4. Default secure runtime location (if no socket override):
   - `$XDG_RUNTIME_DIR/edmc_hotkeys/bridge.sock`
   - token file: `$XDG_RUNTIME_DIR/edmc_hotkeys/sender.token`
5. Use hardened sender payloads (default):
   - `scripts/gnome_bridge_send.py --socket "$XDG_RUNTIME_DIR/edmc_hotkeys/bridge.sock" --token-file "$XDG_RUNTIME_DIR/edmc_hotkeys/sender.token" --binding-id <id>`

Expected result:
- `EDMCHotkeys` selects backend `linux-wayland-gnome-bridge`.
- Active bridge bindings are auto-synced into GNOME custom keybindings.
- Changing bindings in EDMCHotkeys updates GNOME shortcuts automatically.
- Runtime diagnostics expose explicit hardening failure classes (`auth_reject`, `replay_reject`, `malformed_reject`, `rate_limit_drop`, `queue_drop`).

### GNOME Companion Extension/Helper Setup (Phase 3 Optional Track)
Use this when validating the extension -> helper -> plugin bridge architecture.

1. Install companion artifacts:
   - `./scripts/install_gnome_bridge_companion.sh --enable`
2. Verify install:
   - `./scripts/verify_gnome_bridge_companion.sh`
3. Export current plugin bindings into companion config:
   - `./scripts/export_companion_bindings.py --bindings ./bindings.json --output ~/.config/edmc-hotkeys/companion-bindings.json`
4. Restart GNOME Shell extension/session if needed, then test key activation.
5. Roll back companion artifacts:
   - `./scripts/uninstall_gnome_bridge_companion.sh`

Companion compatibility matrix:
- [gnome-companion-compatibility-matrix.md](/home/jon/edmc_plugins/EDMCHotkeys/docs/gnome-companion-compatibility-matrix.md)
Companion QA matrix:
- [GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md](/home/jon/edmc_plugins/EDMCHotkeys/docs/qa/GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md)
Phase 5 rollout artifacts:
- [GNOME_WAYLAND_BRIDGE_ALPHA_ROLLOUT_CHECKLIST.md](/home/jon/edmc_plugins/EDMCHotkeys/docs/release/GNOME_WAYLAND_BRIDGE_ALPHA_ROLLOUT_CHECKLIST.md)
- [GNOME_WAYLAND_BRIDGE_ISSUE_TRIAGE_TEMPLATE.md](/home/jon/edmc_plugins/EDMCHotkeys/docs/release/GNOME_WAYLAND_BRIDGE_ISSUE_TRIAGE_TEMPLATE.md)
- [GNOME_WAYLAND_BRIDGE_GA_DECISION_RECORD.md](/home/jon/edmc_plugins/EDMCHotkeys/docs/release/GNOME_WAYLAND_BRIDGE_GA_DECISION_RECORD.md)

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
- Open EDMC debug log and search for `EDMCHotkeys`.
- Check for:
  - backend selected/started messages.
  - backend unavailable reason.
  - settings frame/type errors in plugin preferences.
  - feature-flag state for platform-specific behavior (see `docs/feature-flags.md`).

Example:

```bash
rg -n "EDMCHotkeys|backend|Auto-disabled binding|plugin_prefs|Failed for Plugin" ~/edmc-logs/EDMarketConnector-debug.log
```

## bindings.json Location
- Bindings are stored in:
  - `<EDMC plugin dir>/EDMCHotkeys/bindings.json`
- If missing, the plugin creates the file with defaults on startup.
