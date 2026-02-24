# Manual QA Checklist

## Scope
- Release/milestone validation for `EDMC-Hotkeys` in real EDMC runtime.
- Covers settings UI, dispatch behavior, persistence, and backend smoke checks.

## Preflight
1. Confirm plugin is installed as a single folder with `load.py`:
   - `<EDMC plugins>/EDMC-Hotkeys/load.py`
2. Confirm `bindings.json` exists in plugin directory (or is created on first start).
3. Start EDMC with debug logging enabled.

## Startup + Logging
1. Launch EDMC and confirm plugin loads without traceback.
2. Verify debug log contains plugin load/start lines for `EDMC-Hotkeys`.
3. Verify there are no `TypeError`/`ImportError` entries for plugin hooks.

Command:

```bash
rg -n "EDMC-Hotkeys|Failed for Plugin|Traceback|TypeError|ImportError" ~/edmc-logs/EDMarketConnector-debug.log
```

## Settings UI
1. Open `Settings` and select `EDMC-Hotkeys`.
2. Confirm settings pane renders and is scrollable.
3. Add/edit/remove binding rows.
4. Confirm validation messaging appears for:
   - duplicate hotkey conflicts.
   - unknown action IDs.
5. Save preferences and reopen Settings to confirm values persist.

## Bindings Persistence
1. Edit bindings and click Save in EDMC preferences.
2. Confirm `bindings.json` updates in plugin directory.
3. Restart EDMC and verify bindings are reloaded and still present.

## Dispatch + Action Invocation
1. Register at least one known action.
2. Trigger the bound hotkey and verify target behavior occurs.
3. Confirm no unhandled exceptions in logs during callback execution.
4. Confirm disabled bindings do not invoke actions.

## Backend Smoke Checks

### Linux X11
1. Run under an X11 session (`DISPLAY` present).
2. Confirm backend selection/start for X11 path.
3. Trigger a hotkey and confirm callback dispatch works.

### Linux Wayland
1. Run under Wayland (`WAYLAND_DISPLAY` present).
2. Confirm Wayland backend wrapper is selected.
3. If portal client is unavailable, confirm hotkeys are disabled with explicit warning (not a crash).

### Windows
1. Confirm Windows backend starts.
2. Verify modifier hotkeys register and trigger.
3. Verify no-modifier hotkeys follow fallback behavior (if configured).

## Shutdown
1. Exit EDMC cleanly.
2. Confirm plugin stop hook runs without shutdown exceptions.
3. Confirm no hang on exit related to plugin threads/hooks.
