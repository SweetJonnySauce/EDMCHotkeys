# Registering Actions With EDMC-Hotkeys

This guide shows how another EDMC plugin can register actions with `EDMC-Hotkeys` so they can be triggered by global hotkeys.

## Prerequisites
- `EDMC-Hotkeys` is installed and enabled.
- Your plugin callback code is UI-safe:
  - use `thread_policy="main"` for Tk/UI changes.
  - use `thread_policy="worker"` only for non-UI/background work.

## Action Callback Contract
Your callback should accept keyword args:

```python
def my_callback(*, payload=None, source="hotkey", hotkey=None):
    ...
```

- `payload`: optional dict from the binding.
- `source`: where invocation came from (for example `backend:linux-x11`).
- `hotkey`: hotkey string when invoked via a binding (optional; omitted if not available).
- `EDMC-Hotkeys` only passes `hotkey` when your callback declares it or accepts `**kwargs`.

## Minimal Registration Example

Put this in your plugin (for example in `load.py`), then call `_register_hotkey_actions()` from `plugin_start3`.

```python
from __future__ import annotations

import importlib
import logging

from edmc_hotkeys.registry import Action

plugin_name = "My-Test-Plugin"
logger = logging.getLogger(plugin_name)
_hotkeys_api = None


def plugin_start3(plugin_dir: str) -> str:
    del plugin_dir
    _register_hotkey_actions()
    return plugin_name


def _set_on(*, payload=None, source="hotkey", hotkey=None):
    del payload
    logger.info("ON action from %s (hotkey=%s)", source, hotkey)
    # Update your UI/state here (main-thread safe)


def _set_off(*, payload=None, source="hotkey", hotkey=None):
    del payload
    logger.info("OFF action from %s (hotkey=%s)", source, hotkey)


def _toggle(*, payload=None, source="hotkey", hotkey=None):
    del payload
    logger.info("TOGGLE action from %s (hotkey=%s)", source, hotkey)


def _set_color(*, payload=None, source="hotkey", hotkey=None):
    color = (payload or {}).get("color", "gray")
    logger.info("COLOR action from %s (hotkey=%s) -> %s", source, hotkey, color)
    # Apply color to your UI block here


def _register_hotkey_actions() -> bool:
    global _hotkeys_api
    try:
        _hotkeys_api = importlib.import_module("EDMC-Hotkeys.load")
    except Exception:
        logger.warning("EDMC-Hotkeys is not importable yet")
        return False

    actions = [
        Action(
            id="my_test.on",
            label="Turn On",
            plugin=plugin_name,
            callback=_set_on,
            thread_policy="main",
        ),
        Action(
            id="my_test.off",
            label="Turn Off",
            plugin=plugin_name,
            callback=_set_off,
            thread_policy="main",
        ),
        Action(
            id="my_test.toggle",
            label="Toggle",
            plugin=plugin_name,
            callback=_toggle,
            thread_policy="main",
        ),
        Action(
            id="my_test.color",
            label="Set Color",
            plugin=plugin_name,
            callback=_set_color,
            params_schema={
                "type": "object",
                "properties": {"color": {"type": "string"}},
            },
            thread_policy="main",
        ),
    ]

    all_ok = True
    for action in actions:
        ok = _hotkeys_api.register_action(action)
        all_ok = all_ok and ok
        if not ok:
            logger.warning("Failed to register action: %s", action.id)
    return all_ok
```

## Bindings Example
Add bindings in `EDMC-Hotkeys/bindings.json` (or via settings UI) that target your action IDs:

```json
{
  "id": "test-on",
  "hotkey": "Ctrl+Shift+1",
  "action_id": "my_test.on",
  "enabled": true
}
```

Color payload example:

```json
{
  "id": "test-color-red",
  "hotkey": "Ctrl+Shift+4",
  "action_id": "my_test.color",
  "payload": {"color": "red"},
  "enabled": true
}
```

## Troubleshooting
- `Action id '...' was not found`:
  - action registration did not run or failed.
  - verify your plugin loaded and `_register_hotkey_actions()` returned `True`.
- `Timed out waiting for main-thread dispatch`:
  - callback expected main-thread dispatch but queue was not being pumped; ensure you are on the latest `EDMC-Hotkeys` version.
- Action returns `False` on register:
  - duplicate action ID already exists; make IDs unique.
