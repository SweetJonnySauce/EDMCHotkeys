# Plugin Developer Quick Start

Use this when you want a minimal, working `EDMCHotkeys` integration quickly.

Related docs:
- API reference: `docs/plugin-developer-api-reference.md`
- Practical integration guide: `docs/register-action-with-edmchotkeys.md`
- Troubleshooting: `docs/plugin-developer-api-troubleshooting.md`

## Prerequisites
- `EDMCHotkeys` is installed and enabled in EDMC.
- Your plugin has a `plugin_start3` entrypoint.

## 5-Minute Setup

### 1. Import and define one callback
```python
import EDMCHotkeys as hotkeys

def toggle_overlay(*, payload=None, source="hotkey", hotkey=None):
    # Apply your plugin behavior here.
    pass
```

### 2. Register one action in `plugin_start3`
```python
def plugin_start3(plugin_dir: str) -> str:
    hotkeys.register_action(
        hotkeys.Action(
            id="my_plugin.toggle_overlay",
            label="Toggle Overlay",
            plugin="MyPlugin",
            callback=toggle_overlay,
            thread_policy="main",
            cardinality="single",
        )
    )
    return "MyPlugin"
```

### 3. Bind the action in EDMCHotkeys settings
In EDMC:
1. Open `File -> Settings -> EDMCHotkeys`.
2. Add a binding with:
- `Plugin`: `MyPlugin`
- `Action`: `Toggle Overlay`
- A hotkey (for example `Ctrl+Shift+O`)
- `Enabled`: `Yes`

### 4. Verify it works
- Press the hotkey.
- Confirm the expected plugin behavior occurs.

### 5. If it fails
- Use symptom-first troubleshooting:
  - `docs/plugin-developer-api-troubleshooting.md`

## Notes
- Use `thread_policy="main"` for UI changes.
- Use `thread_policy="worker"` only for non-UI/background work.
- On Wayland portal/GNOME bridge, use generic modifiers (`Ctrl`, `Alt`, `Shift`, `Win`), not side-specific (`LCtrl`, `RShift`).
