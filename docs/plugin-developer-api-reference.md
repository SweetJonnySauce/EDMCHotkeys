# Plugin Developer API Reference

## Scope
Canonical reference for the `EDMCHotkeys` plugin developer API exposed via:

```python
import EDMCHotkeys as hotkeys
```

For practical setup and examples, use:
- `docs/register-action-with-edmchotkeys.md`

For failure diagnosis, use:
- `docs/plugin-developer-api-troubleshooting.md`

## Public API Surface
Source of truth:
- `__init__.__all__` in `__init__.py`
- runtime wrappers in `load.py`
- dataclasses in `edmc_hotkeys/registry.py` and `edmc_hotkeys/plugin.py`

All public symbols below are currently labeled `stable`.

| Symbol | Signature | Compatibility | Source |
| --- | --- | --- | --- |
| `Action` | `Action(id, label, plugin, callback, params_schema=None, thread_policy="main", enabled=True, cardinality="single")` | stable | `edmc_hotkeys/registry.py` |
| `Binding` | `Binding(id, hotkey, action_id, payload=None, enabled=True, plugin="")` | stable | `edmc_hotkeys/plugin.py` |
| `register_action` | `register_action(action: Action) -> bool` | stable | `load.py` |
| `list_actions` | `list_actions() -> list[Action]` | stable | `load.py` |
| `list_bindings` | `list_bindings(plugin_name: str) -> list[Binding]` | stable | `load.py` |
| `get_action` | `get_action(action_id: str) -> Action \| None` | stable | `load.py` |
| `invoke_action` | `invoke_action(action_id: str, payload=None, source="hotkey", hotkey=None) -> bool` | stable | `load.py` |
| `invoke_bound_action` | `invoke_bound_action(binding: Binding, source="hotkey") -> bool` | stable | `load.py` |

## Public Dataclass Contracts

### `Action`
| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `id` | `str` | required | Unique across all registered actions. |
| `label` | `str` | required | User-facing label in settings UI. |
| `plugin` | `str` | required | Owning plugin name. |
| `callback` | `Callable[..., Any]` | required | Invoked with keyword args (`payload`, `source`, optional `hotkey`). |
| `params_schema` | `dict \| None` | `None` | Optional payload schema metadata. |
| `thread_policy` | `str` | `"main"` | `"main"` or `"worker"`. Invalid value is rejected at registration. |
| `enabled` | `bool` | `True` | Disabled actions are not invokable. |
| `cardinality` | `str` | `"single"` | Determines reuse of action in EDMCHotkeys preference pane. `"single"`: Action can only be used once or `"multi"`: action can be reused (payloads must be unique); invalid values normalize to `"single"` with warning. |

### `Binding`
| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `id` | `str` | required | Binding identifier. |
| `hotkey` | `str` | required | Canonical hotkey text at runtime; pretty form exposed when listed. |
| `action_id` | `str` | required | Target action ID. |
| `payload` | `dict \| None` | `None` | Optional callback payload. |
| `enabled` | `bool` | `True` | Disabled bindings do not invoke actions. |
| `plugin` | `str` | `""` | Owning plugin label used by `list_bindings(plugin_name)`. |

## API Behavior Details

### `register_action(action)`
- Returns `True` when action registration succeeds.
- Returns `False` when:
  - plugin runtime is not started
  - action ID is duplicate
  - `thread_policy` is invalid
  - callback is not callable

### `list_actions()`
- Returns registered actions in registration order.
- Returns `[]` if plugin runtime is not started.

### `list_bindings(plugin_name)`
- Requires non-empty `plugin_name`; empty string returns `[]`.
- Match is case-insensitive against binding owner plugin.
- Returns bindings for that plugin only.
- `hotkey` values returned are pretty-rendered for display.

### `get_action(action_id)`
- Returns matching `Action` when found.
- Returns `None` if plugin runtime is not started or action is missing.

### `invoke_action(action_id, payload=None, source="hotkey", hotkey=None)`
- Returns `True` when dispatch path accepts execution.
- Returns `False` for missing/disabled actions, dispatch failure, or callback error.
- `hotkey` kwarg is passed to callback only if callback supports it.

### `invoke_bound_action(binding, source="hotkey")`
- Returns `False` for disabled bindings.
- Returns `False` when target action cannot be invoked.
- Returns `True` when action dispatch succeeds.

## Callback Contract
Recommended callback shape:

```python
def my_callback(*, payload=None, source="hotkey", hotkey=None):
    ...
```

Guarantees:
- `payload` is always provided (may be `None`).
- `source` is always provided.
- `hotkey` is provided only when available and callback supports `hotkey` or `**kwargs`.

## Threading and Dispatch
- `thread_policy="main"`:
  - callback is routed through main-thread dispatch path.
- `thread_policy="worker"`:
  - callback is routed through worker-thread execution path.

UI safety:
- UI updates should remain on main-thread callback paths.
- Worker callbacks should be used for background/non-UI work.

## Backend Capability Notes
| Backend | Side-specific modifiers (`LCtrl`, `RShift`, etc.) |
| --- | --- |
| Windows | Supported |
| Linux X11 | Supported |
| Linux Wayland keyd | Supported |

## Failure Semantics Matrix
| Condition | Typical return | Notes |
| --- | --- | --- |
| Plugin not started | `False` / `[]` / `None` | Depends on API return type. |
| Duplicate action ID | `False` (`register_action`) | First registration wins. |
| Invalid thread policy | `False` (`register_action`) | Must be `"main"` or `"worker"`. |
| Missing action ID | `False` (`invoke_action`) | Logged warning. |
| Disabled action | `False` (`invoke_action`) | Logged warning. |
| Callback exception | `False` (`invoke_action`) | Logged exception. |
| Empty `plugin_name` in `list_bindings` | `[]` | Logged warning. |

## Related Docs
- Practical guide: `docs/register-action-with-edmchotkeys.md`
- Troubleshooting: `docs/plugin-developer-api-troubleshooting.md`
- Requirements baseline: `docs/plugin-developer-api-phase1-requirements.md`
