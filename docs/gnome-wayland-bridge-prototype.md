# GNOME Wayland Bridge

## Scope
- Intended for GNOME Wayland environments where `org.freedesktop.portal.GlobalShortcuts` is unavailable.
- Uses GNOME custom keybindings as the sender path (auto-managed by the plugin in bridge mode).

## Enable
Start EDMC with:

```bash
EDMC_HOTKEYS_BACKEND_MODE=wayland_gnome_bridge \
EDMC_HOTKEYS_GNOME_BRIDGE=1 \
EDMarketConnector
```

If `EDMC_HOTKEYS_GNOME_BRIDGE_SOCKET` is omitted, default is:
- `$XDG_RUNTIME_DIR/edmc_hotkeys/bridge.sock`

Additional runtime controls:
- `EDMC_HOTKEYS_GNOME_BRIDGE_SOCKET=/abs/path/bridge.sock` overrides socket path.
- `EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN=<token>` sets auth token explicitly.
- `EDMC_HOTKEYS_GNOME_BRIDGE_TOKEN_FILE=/abs/path/sender.token` overrides token file path.

Optional runtime controls:
- `EDMC_HOTKEYS_GNOME_BRIDGE_AUTOSYNC=0` disables GNOME keybinding auto-sync.
- `EDMC_HOTKEYS_GNOME_BRIDGE_SENDER_SCRIPT=/abs/path/to/gnome_bridge_send.py` overrides sender script path.
- `EDMC_HOTKEYS_GNOME_BRIDGE_NO_EVENTS_WARN_SECONDS=15` adjusts receiver-only warning delay.
- `EDMC_HOTKEYS_GNOME_BRIDGE_HARDENED=0` relaxes hardened parser/auth mode (debug only).
- `EDMC_HOTKEYS_GNOME_BRIDGE_ALLOW_LEGACY=1` allows legacy payloads (compat only).

## Auto-Sync Behavior
- On startup and settings save, EDMC-Hotkeys syncs active bridge bindings to GNOME custom keybindings.
- When a binding hotkey changes in EDMC-Hotkeys, GNOME keybinding entries are updated automatically.
- Only bridge-compatible bindings are synced:
  - generic/key-only modifiers (`Ctrl`, `Alt`, `Shift`, `Win`, function keys, alnum/supported specials)
  - side-specific modifiers are skipped with warnings.
- Managed keybindings use an `edmc-hotkeys-*` path prefix and do not overwrite non-EDMC custom keybindings.

## Activation payload
Hardened mode (default) accepts only protocol-v1 activation payloads:
- required fields: `version`, `type`, `binding_id`, `timestamp_ms`, `nonce`, `token`
- required values for activate: `version="1"`, `type="activate"`

Legacy payloads (`binding-id` or `{"binding_id":"..."}`) are rejected unless:
- `EDMC_HOTKEYS_GNOME_BRIDGE_ALLOW_LEGACY=1`
- and hardened mode is disabled (`EDMC_HOTKEYS_GNOME_BRIDGE_HARDENED=0`)

Use helper script for manual troubleshooting:

```bash
python scripts/gnome_bridge_send.py \
  --socket "$XDG_RUNTIME_DIR/edmc_hotkeys/bridge.sock" \
  --token-file "$XDG_RUNTIME_DIR/edmc_hotkeys/sender.token" \
  --binding-id hotkeys_test_toggle
```

Legacy text mode (compat/debug only):

```bash
python scripts/gnome_bridge_send.py \
  --socket "$XDG_RUNTIME_DIR/edmc_hotkeys/bridge.sock" \
  --binding-id hotkeys_test_toggle \
  --legacy
```

## Behavior notes
- Backend name: `linux-wayland-gnome-bridge`
- Side-specific modifier support remains disabled.
- Only currently registered binding ids are accepted; unknown ids are ignored.
- Startup log includes bridge runtime status (sender status and synced binding count).
- If no sender events are observed after startup grace period, backend logs an explicit receiver-only warning.
- Runtime status includes hardening counters (`auth_reject`, `replay_reject`, `malformed_reject`, `rate_limit_drop`, `queue_drop`).

## Companion Artifact (Phase 3)
Companion artifacts provide an extension/helper path independent from plugin runtime modules:

- Extension source:
  - `companion/gnome-extension/edmc-hotkeys@edcd/`
- Helper sender:
  - `companion/helper/gnome_bridge_companion_send.py`

Install/remove/verify helpers:

```bash
./scripts/install_gnome_bridge_companion.sh --enable
./scripts/verify_gnome_bridge_companion.sh
./scripts/uninstall_gnome_bridge_companion.sh
```

Export current EDMC bindings into companion config:

```bash
./scripts/export_companion_bindings.py \
  --bindings ./bindings.json \
  --output ~/.config/edmc-hotkeys/companion-bindings.json
```

Default companion config path:
- `~/.config/edmc-hotkeys/companion-bindings.json`

Compatibility/support matrix:
- [gnome-companion-compatibility-matrix.md](/home/jon/edmc_plugins/EDMC-Hotkeys/docs/gnome-companion-compatibility-matrix.md)
Phase 4 QA evidence:
- [GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md](/home/jon/edmc_plugins/EDMC-Hotkeys/docs/qa/GNOME_WAYLAND_BRIDGE_PHASE4_QA_MATRIX.md)
