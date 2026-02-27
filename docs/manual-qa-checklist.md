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
2. Verify debug log contains backend selection diagnostics:
   - `Hotkey backend selected: name=... available=... supports_side_specific_modifiers=...`
3. Verify debug log contains either:
   - backend started line for the active session path, or
   - explicit unavailable reason (non-fatal).
4. Verify there are no `TypeError`/`ImportError` entries for plugin hooks.

Pass criteria:
- All four checks pass and no fatal plugin load error appears.

Fail criteria:
- Missing backend selection diagnostics, startup traceback, or plugin load failure.

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
5. Click Apply/Save with valid rows and confirm settings persist.
6. Click Apply/Save with invalid rows and confirm dialog stays open with validation errors.

Pass criteria:
- Valid edits persist and invalid edits are blocked without crashing EDMC.

Fail criteria:
- Settings pane fails to render, apply closes incorrectly on errors, or values do not persist.

## Bindings Persistence
1. Edit bindings and click Save in EDMC preferences.
2. Confirm `bindings.json` updates in plugin directory.
3. Restart EDMC and verify bindings are reloaded and still present.

## Dispatch + Action Invocation
1. Register at least one known action.
2. Trigger the bound hotkey and verify target behavior occurs.
3. Confirm no unhandled exceptions in logs during callback execution.
4. Confirm disabled bindings do not invoke actions.
5. Trigger journal/dashboard updates (normal EDMC activity) and confirm no dispatch-pump warnings or hangs.

Pass criteria:
- Enabled bindings invoke expected actions and dispatch remains responsive.

Fail criteria:
- Missed invocations for valid bindings, unexpected invocations for disabled bindings, or dispatch-related warnings/errors.

## Backend Smoke Checks

### Linux X11
1. Run under an X11 session (`DISPLAY` present).
2. Confirm backend selection/start for X11 path.
3. Trigger a hotkey and confirm callback dispatch works.

### Linux Wayland
1. Run under Wayland (`WAYLAND_DISPLAY` present).
2. Confirm backend `linux-wayland-portal` is selected.
3. If portal prerequisites are available (`xdg-desktop-portal` + `dbus-next`), confirm registration/dispatch works.
4. If prerequisites are missing, confirm hotkeys are disabled with explicit warning (not a crash).
5. Validate Tier 1 modifier policy with representative bindings:
   - generic binding (for example `Ctrl+Shift+F1`) stays enabled
   - side-specific binding (for example `LCtrl+LShift+F1`) is auto-disabled
   - mixed-family binding (for example `Ctrl+LCtrl+F1`) is rejected by validation
6. Confirm disable diagnostics only reference side-specific bindings and do not mention generic bindings.

### Windows
1. Confirm Windows backend starts.
2. Verify generic modifier hotkeys register and trigger (RegisterHotKey path).
3. Verify side-specific modifier hotkeys (for example `LCtrl+LShift+F1`) trigger via low-level hook.
4. Verify no-modifier hotkeys register and trigger.

## Shutdown
1. Exit EDMC cleanly.
2. Confirm plugin stop hook runs without shutdown exceptions.
3. Confirm no hang on exit related to plugin threads/hooks.

Pass criteria:
- EDMC exits normally, no stuck process/thread behavior, no plugin shutdown traceback.

Fail criteria:
- Exit hang, shutdown traceback, or repeated timer/thread errors.

## Manual-Only Checks
- These checks remain manual because they depend on real EDMC/Tk runtime behavior and OS-level focus/input:
  - global hotkey delivery while Elite Dangerous has focus.
  - compositor/session-specific backend startup behavior.
  - real shutdown lifecycle behavior across UI state transitions.
