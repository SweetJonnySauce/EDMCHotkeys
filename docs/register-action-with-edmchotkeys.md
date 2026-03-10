# Registering Actions With EDMCHotkeys

Practical integration guide for plugin developers.

Canonical contract references:
- API signatures and semantics: `docs/plugin-developer-api-reference.md`
- Failure diagnosis: `docs/plugin-developer-api-troubleshooting.md`

## Prerequisites
- `EDMCHotkeys` is installed and enabled.
- Your callbacks are thread-safe:
  - use `thread_policy="main"` for Tk/UI work
  - use `thread_policy="worker"` for non-UI/background work

## Quickstart

### 1. Import the API
```python
import EDMCHotkeys as hotkeys
```

### 2. Register actions during plugin startup
```python
from __future__ import annotations

import logging
import EDMCHotkeys as hotkeys

plugin_name = "My-Test-Plugin"
logger = logging.getLogger(plugin_name)


def plugin_start3(plugin_dir: str) -> str:
    del plugin_dir
    _register_hotkey_actions()
    return plugin_name


def _toggle(*, payload=None, source="hotkey", hotkey=None):
    del payload
    logger.info("TOGGLE action from %s (hotkey=%s)", source, hotkey)


def _set_color(*, payload=None, source="hotkey", hotkey=None):
    color = (payload or {}).get("color", "gray")
    logger.info("COLOR action from %s (hotkey=%s) -> %s", source, hotkey, color)


def _register_hotkey_actions() -> bool:
    actions = [
        hotkeys.Action(
            id="my_test.toggle",
            label="Toggle",
            plugin=plugin_name,
            callback=_toggle,
            thread_policy="main",
            cardinality="single",
        ),
        hotkeys.Action(
            id="my_test.color",
            label="Set Color",
            plugin=plugin_name,
            callback=_set_color,
            thread_policy="main",
            cardinality="multi",
        ),
    ]

    all_ok = True
    for action in actions:
        ok = hotkeys.register_action(action)
        all_ok = all_ok and ok
        if not ok:
            logger.warning("Failed to register action: %s", action.id)
    return all_ok
```

### 3. Configure bindings
Create bindings in settings UI or `EDMCHotkeys/bindings.json`.

Single-use action example:
```json
{
  "id": "test-toggle-generic",
  "plugin": "My-Test-Plugin",
  "modifiers": ["ctrl", "shift"],
  "key": "t",
  "action_id": "my_test.toggle",
  "enabled": true
}
```

Multi-use action with payload:
```json
{
  "id": "test-color-red",
  "plugin": "My-Test-Plugin",
  "modifiers": ["ctrl", "shift"],
  "key": "4",
  "action_id": "my_test.color",
  "payload": {"color": "red"},
  "enabled": true
}
```

## Callback Contract Notes
Recommended callback shape:
```python
def my_callback(*, payload=None, source="hotkey", hotkey=None):
    ...
```

Behavior:
- `payload` and `source` are always provided.
- `hotkey` is provided when available and callback supports it.

## Hotkey and Backend Notes
- Generic modifiers: `ctrl`, `alt`, `shift`, `win`
- Side-specific modifiers: `ctrl_l`, `ctrl_r`, `alt_l`, `alt_r`, `shift_l`, `shift_r`, `win_l`, `win_r`
- Mixed same-family generic + side-specific tokens are invalid.

Backend caveat:
- Linux Wayland keyd supports side-specific modifiers.

## Integration Verification Checklist
1. Confirm `register_action(...)` returned `True` for all expected actions.
2. Confirm actions are visible in EDMCHotkeys settings dropdowns.
3. Trigger a bound hotkey and verify your callback log line appears.
4. Validate payload-driven bindings produce expected behavior.

## Related Docs
- API reference: `docs/plugin-developer-api-reference.md`
- Troubleshooting: `docs/plugin-developer-api-troubleshooting.md`
- Linux backend setup: `docs/linux-user-setup.md`
