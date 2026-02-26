# GNOME Wayland Bridge

## Scope
- Intended for GNOME Wayland environments where `org.freedesktop.portal.GlobalShortcuts` is unavailable.
- Uses GNOME custom keybindings as the sender path (auto-managed by the plugin in bridge mode).

## Enable
Start EDMC with:

```bash
EDMC_HOTKEYS_GNOME_BRIDGE=1 \
EDMC_HOTKEYS_GNOME_BRIDGE_SOCKET=/tmp/edmc_hotkeys_gnome_bridge.sock \
EDMarketConnector
```

If `EDMC_HOTKEYS_GNOME_BRIDGE_SOCKET` is omitted, default is `/tmp/edmc_hotkeys_gnome_bridge.sock`.

Optional runtime controls:
- `EDMC_HOTKEYS_GNOME_BRIDGE_AUTOSYNC=0` disables GNOME keybinding auto-sync.
- `EDMC_HOTKEYS_GNOME_BRIDGE_SENDER_SCRIPT=/abs/path/to/gnome_bridge_send.py` overrides sender script path.
- `EDMC_HOTKEYS_GNOME_BRIDGE_NO_EVENTS_WARN_SECONDS=15` adjusts receiver-only warning delay.

## Auto-Sync Behavior
- On startup and settings save, EDMC-Hotkeys syncs active bridge bindings to GNOME custom keybindings.
- When a binding hotkey changes in EDMC-Hotkeys, GNOME keybinding entries are updated automatically.
- Only bridge-compatible bindings are synced:
  - generic/key-only modifiers (`Ctrl`, `Alt`, `Shift`, `Win`, function keys, alnum/supported specials)
  - side-specific modifiers are skipped with warnings.
- Managed keybindings use an `edmc-hotkeys-*` path prefix and do not overwrite non-EDMC custom keybindings.

## Activation payload
The backend accepts either:
- plain binding id text, e.g. `binding-id`
- JSON payload, e.g. `{"binding_id":"binding-id"}`

Use helper script for manual troubleshooting:

```bash
python scripts/gnome_bridge_send.py \
  --socket /tmp/edmc_hotkeys_gnome_bridge.sock \
  --binding-id hotkeys_test_toggle
```

JSON mode:

```bash
python scripts/gnome_bridge_send.py \
  --socket /tmp/edmc_hotkeys_gnome_bridge.sock \
  --binding-id hotkeys_test_toggle \
  --json
```

## Behavior notes
- Backend name: `linux-wayland-gnome-bridge`
- Side-specific modifier support remains disabled.
- Only currently registered binding ids are accepted; unknown ids are ignored.
- Startup log includes bridge runtime status (sender status and synced binding count).
- If no sender events are observed after startup grace period, backend logs an explicit receiver-only warning.
