# Manual QA Checklist

## Scope
- Release/milestone validation for `EDMCHotkeys` in real EDMC runtime.
- Covers settings UI, dispatch behavior, persistence, and backend smoke checks.

## Preflight
1. Confirm plugin is installed as a single folder with `load.py`:
   - `<EDMC plugins>/EDMCHotkeys/load.py`
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
rg -n "EDMCHotkeys|Failed for Plugin|Traceback|TypeError|ImportError" ~/edmc-logs/EDMarketConnector-debug.log
```

## Settings UI
1. Open `Settings` and select `EDMCHotkeys`.
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

### Action Dropdown Filtering
1. In settings, add two rows with plugin `alpha` and one row with plugin `beta`.
2. For a row with empty plugin, open the Action dropdown and verify it is empty.
3. For a row with plugin `ALPHA`, verify only `alpha` actions appear (case-insensitive plugin matching).
4. Select a `single` cardinality action in one enabled row, then verify that action is removed from Action dropdowns in other enabled matching-plugin rows.
5. Select a `multi` cardinality action in one enabled row, then verify that action remains available in other matching-plugin rows.
6. Mark a row disabled (`Enabled = No`) while it has an assigned `single` action; verify that action becomes available again in other enabled rows.
7. Change a row plugin so its current action is no longer valid; verify action is cleared immediately.
8. After step 7, verify payload text for that row is also cleared immediately.
9. Remove the row that currently holds a previously excluded `single` action; verify the action becomes available again in other matching-plugin rows.
10. Save with duplicate enabled `single` bindings and verify a warning is shown (not an error block).
11. Save with duplicate enabled `multi` bindings using identical payload JSON and verify a warning is shown.
12. Save with duplicate enabled `multi` bindings using different payload JSON and verify no cardinality warning is shown.

Pass criteria:
- All 12 checks match expected dropdown/validation behavior with no stale action/payload values.

Fail criteria:
- Empty-plugin rows show actions, `single`/`multi` behavior is not respected, disabled rows still reserve actions, invalid action/payload fields fail to clear, or cardinality warnings are missing/incorrect.

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
2. Confirm backend `linux-wayland-keyd` is selected.
3. If keyd is active and integration is installed, confirm registration/dispatch works.
4. If keyd is unavailable, confirm hotkeys are disabled with explicit warning (not a crash).
5. Validate side-specific modifier behavior with representative bindings:
   - generic binding (for example `Ctrl+Shift+F1`) stays enabled
   - side-specific binding (for example `LCtrl+LShift+F1`) stays enabled
   - mixed-family binding (for example `Ctrl+LCtrl+F1`) is rejected by validation
6. Confirm no Windows-specific ambiguity warning appears for Linux capture interactions:
   - `Ambiguous Windows modifier state during hotkey capture`

### Windows
1. Confirm Windows backend starts.
2. Verify generic modifier hotkeys register and trigger (RegisterHotKey path).
3. Verify side-specific modifier hotkeys (for example `LCtrl+LShift+F1`) trigger via low-level hook.
4. Verify no-modifier hotkeys register and trigger.
5. In settings hotkey capture with side-specific mode enabled, verify state-only modifier bits do not synthesize side-specific tokens:
   - example: typing `X` while ambiguous `Alt` state is reported should capture `X`, not `LAlt+X`.
6. Verify explicit side-modifier capture remains correct:
   - example: `Alt_R` + `X` captures `RAlt+X`.
7. Verify generic mode remains unchanged (`supports_side_specific_modifiers=False`):
   - example: state-only `Alt` + `X` still captures `Alt+X`.
8. With debug logging enabled, verify capture diagnostics appear:
   - `Hotkey capture resolved: ...`
9. Verify ambiguity warning appears only for Windows side-specific ambiguous-state captures:
   - `Ambiguous Windows modifier state during hotkey capture`
10. Verify no ambiguity warning appears for explicit side-modifier captures.

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
