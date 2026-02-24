# EDMC Key Listener - Requirements & Architecture Notes

## References
- EDMC plugin developer documentation: https://github.com/EDCD/EDMarketConnector/blob/main/PLUGINS.md

## Goal
- Provide global hotkeys that work even when Elite:Dangerous has focus.
- Allow mapping hotkeys to actions that control EDMC or other plugins (e.g., toggle overlay visibility, change plugin layout).
- Cross-platform: Linux (various distros) and Windows.
- Linux must support both X11 and Wayland.
- Windows target: Windows 11.
- Must work with both EDMC from source and the packaged app.
- Log messages using the EDMC logger and respect the EDMC log level.

## Non-Goals (for now)
- No implementation details or code yet.
- No commitment yet to a specific hotkey library or OS hook mechanism.
- No commitment to a specific inter-plugin messaging approach.

## EDMC Plugin Constraints (from PLUGINS.md)
- Plugins are Python modules in a folder under `plugins/`, with a `load.py` that must implement `plugin_start3(plugin_dir)` returning the plugin name.
- Only specific imports from EDMC core are supported; `config` usage is intended for plugin-owned config only.
- Long-running work should run in a separate thread to avoid blocking the UI.
- Tkinter calls must occur on the main thread; sub-threads should only use `event_generate()` to communicate UI updates.
- Do not call `event_generate()` during shutdown; use `config.shutting_down` to detect shutdown.
- Shared modules across plugins can collide; relative imports are recommended to avoid name conflicts.

## High-Level Architecture Options
1. **Action Registry Plugin (preferred baseline)**
   - This plugin owns a registry of actions (string IDs -> callable + metadata).
   - Other plugins expose actions by registering with this plugin at runtime.
   - Hotkey bindings map to action IDs.

2. **Synthetic Event Injection**
   - Hotkeys generate synthetic events (e.g., journal-like events) that EDMC and/or plugins already listen for.
   - This leverages existing event handlers but requires agreement on event schemas.

3. **Direct Plugin-to-Plugin Calls**
   - Hotkey plugin imports other plugins and calls their functions.
   - Requires a stable API contract and careful module naming to avoid collisions.

4. **Hybrid**
   - Action registry is primary.
   - Optional synthetic events for legacy compatibility or broad fan-out.

## Action Registry Plugin - Detailed Design
- Implement as a **package plugin** so it loads before non-package plugins.
- Expose a stable API for action registration and discovery, intended to be imported by other plugins.
- Registry entry fields (conceptual):
  - `id`: stable action ID (example: `edmcmodernoverlay.toggle`).
  - `label`: human-readable name for settings UI.
  - `plugin`: owning plugin name.
  - `callback`: callable to execute.
  - `params_schema` (optional): schema describing action parameters so the UI can render inputs.
- `thread_policy`: indicates whether the action must run on main thread or can run in a worker.
  - Default policy: `main` (safe by default).
- `enabled` (dynamic): if `False`, action is visible but unavailable.
- Registration flow:
  - Registry plugin loads first and exposes `register_action(...)` and `list_actions()`.
  - Other plugins call `register_action(...)` during `plugin_start3`.
  - Hotkey plugin reads `list_actions()` to populate the settings UI.
- Dispatch flow:
  - Hotkey fires -> lookup by action ID -> dispatch.
  - Default dispatch is on the main thread. This prevents Tkinter UI crashes from background thread calls.
  - Actions that are explicitly marked `worker` may run in a background thread; UI-safe actions should remain on `main`.
- Storage:
  - Hotkey plugin stores bindings as `{hotkey, action_id, payload}` in its own config.
- Failure behavior:
  - Missing action ID -> no-op + log line.
  - Exceptions in action -> caught/logged to avoid crashing EDMC.

## Action Registry API (Normative)
- Plugin ID / config prefix: `edmc_hotkeys`.
- Registration API: `register_action(action)` returns `True`/`False` and rejects duplicate IDs (first wins).
- Discovery: `list_actions()` returns all actions; `get_action(action_id)` returns the action or `None`.
- Dispatch: `invoke_action(action_id, payload=None, source="hotkey")` performs lookup + dispatch with logging.
- Action schema (minimum fields):
  - `id` (string, stable, unique)
  - `label` (string for UI)
  - `plugin` (string owner name)
  - `callback` (callable)
  - `params_schema` (optional dict for UI)
  - `thread_policy` (`main` default, `worker` optional)
  - `enabled` (bool, default `True`)
- Threading contract: hotkey listener runs in the background; **dispatch defaults to main thread**. Actions explicitly marked `worker` may execute off-main.
- Error handling: missing ID -> no-op + warning; callback exceptions -> caught + logged; never crash EDMC.

## Hotkey Capture Considerations (OS-level)
- Must be global (works while the game has focus).
- Linux must account for both X11 and Wayland environments.
- Windows requires system-wide hooks.
- The hotkey listener should run in a background thread and marshal actions back to the main thread when UI interaction is required.
- The plugin itself should spin up a background listener thread, but **action execution defaults to main thread** dispatch.

## Platform Backend Notes (Draft)
- Windows: prefer OS-native global hotkeys (`RegisterHotKey`), with low-level hook as fallback for non-modifier combos.
- Linux X11: use an X11 global hotkey backend implemented in-process.
- Linux Wayland: use XDG Desktop Portal GlobalShortcuts (no privileged fallback yet).
- No privileged/evdev fallback at this stage.

## Backend Selection Strategy (Normative)
- Linux session detection: use `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY`, and `DISPLAY`.
- Wayland: use XDG Desktop Portal GlobalShortcuts only. If unavailable, disable hotkeys and log the error.
- X11: use in-process X11 grabs (`python-xlib`).
- Windows: use `RegisterHotKey`; allow low-level hook fallback for non-modifier combos.

## Linux X11 Backend Proposal
- Use a pure-Python X11 client (likely `python-xlib`) to avoid compiled dependencies in packaged EDMC.
- Register global hotkeys via passive grabs on the root window (one grab per hotkey).
- Normalize modifier state by also grabbing with common lock modifiers (CapsLock/NumLock/ScrollLock) to avoid missing events.
- Run the X11 event loop in a dedicated background thread, translate `KeyPress` events into normalized hotkey IDs, and dispatch via the Action Registry.

## Config Storage + Migration (Normative)
- Single JSON blob stored at config key `edmc_hotkeys.bindings`.
- Schema (v1):
  - `version`: `1`
  - `active_profile`: string, default "Default"
  - `profiles`: map of profile name -> list of bindings
  - binding fields: `id`, `hotkey`, `action_id`, `payload` (optional), `enabled` (bool)
- Reserve profile switching action: `edmc_hotkeys.profile.set` with `profile_name` parameter.
- Migration: missing key -> create v1 defaults; missing `version` -> treat as v1.

## Decisions / Clarifications
- Store mappings in EDMC config per best practices.
- Profile-aware bindings. Start with a "Default" profile that works globally; profile switching is key-bindable.
- UI requirement: EDMC settings dialog needs a flexible, table-like editor for bindings:
  - Hotkey entry cell.
  - Plugin selection cell.
  - Command/action selection cell.
  - vertical scroll bar
