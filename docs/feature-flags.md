# Feature Flags

Canonical source of truth for runtime flags in `EDMC-Hotkeys`.

## Runtime Flags
| Flag | Default | Scope | Purpose | Risk | Removal Criteria |
| --- | --- | --- | --- | --- | --- |
| `EDMC_HOTKEYS_GNOME_BRIDGE` | `0` (disabled) | `edmc_hotkeys/backends/selector.py`, `edmc_hotkeys/backends/gnome_bridge.py` | Enables GNOME Wayland bridge backend selection on Wayland. | Medium: bridge path depends on local GNOME keybinding integration and sender transport. | Remove when bridge/portal selection becomes default-safe without explicit opt-in. |
| `EDMC_HOTKEYS_GNOME_BRIDGE_AUTOSYNC` | `1` (enabled) | `edmc_hotkeys/backends/gnome_bridge.py` | Enables automatic sync of active bridge bindings to GNOME custom keybindings. | Medium: misconfigured GNOME settings can prevent sender registration updates. | Remove when sender registration path is fixed and always-on for bridge mode. |
| `EDMC_HOTKEYS_GNOME_BRIDGE_SENDER_SCRIPT` | plugin-local default | `edmc_hotkeys/backends/gnome_bridge.py` | Overrides sender script path used in synced GNOME keybinding command entries. | Low: wrong path causes sender launch failures. | Remove when sender path is immutable and packaged in a fixed location. |
| `EDMC_HOTKEYS_GNOME_BRIDGE_NO_EVENTS_WARN_SECONDS` | `15` | `edmc_hotkeys/backends/gnome_bridge.py` | Controls grace period before receiver-only warning when no sender events are observed. | Low: diagnostic timing only. | Remove when runtime diagnostics strategy is finalized without env tuning. |

## Policy
- New runtime flags must be added to this file when introduced.
- Docs in other files should link here instead of duplicating default/semantics text.
- Flags should include explicit removal criteria to avoid permanent rollout toggles.
