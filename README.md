# EDMCHotkeys

Global hotkeys plugin for EDMarketConnector with Windows, Linux X11, and Linux Wayland backends.

## Installation

1. Extract the plugin into your EDMC plugins directory.
2. Use `EDMCHotkeys` as the plugin folder name for new installs.
3. Ensure only one hotkeys plugin folder is installed during cutover.

## Plugin Integration

Downstream plugins should use direct import:

```python
import EDMCHotkeys as hotkeys
```

Reference guide:
- [`docs/register-action-with-edmchotkeys.md`](docs/register-action-with-edmchotkeys.md)

## Breaking Rename (Pre-release)

- Canonical plugin/import name is now `EDMCHotkeys`.
- Legacy import path `EDMC-Hotkeys.load` is not supported.
- Remove old integration snippets that use `importlib.import_module("EDMC-Hotkeys.load")`.
- During local cutover, avoid keeping both `EDMC-Hotkeys` and `EDMCHotkeys` folders installed at the same time.

## User Setup Docs

- Linux setup: [`docs/linux-user-setup.md`](docs/linux-user-setup.md)
- Manual QA: [`docs/manual-qa-checklist.md`](docs/manual-qa-checklist.md)
- Feature flags: [`docs/feature-flags.md`](docs/feature-flags.md)
