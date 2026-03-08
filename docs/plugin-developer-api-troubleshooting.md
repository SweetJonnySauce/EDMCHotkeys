# Plugin Developer API Troubleshooting

## Scope
Symptom-first troubleshooting for plugin developers integrating with `EDMCHotkeys`.

Reference docs:
- API contract: `docs/plugin-developer-api-reference.md`
- Integration guide: `docs/register-action-with-edmchotkeys.md`

## Symptom Index
1. Action callback never fires.
2. `register_action(...)` returns `False`.
3. `invoke_action(...)` returns `False`.
4. `list_bindings(plugin_name)` returns empty unexpectedly.
5. Side-specific binding works on Windows/X11 but not on Linux Wayland keyd.
6. Main-thread dispatch timeout warnings appear.
7. Backend unavailable warnings at startup.

## Symptom Cards

### 1. Action callback never fires
Likely causes:
- action registration was skipped or failed
- binding points to wrong `action_id`
- binding is disabled
- backend failed to start or hotkey registration failed

Checks:
- verify your plugin logs successful `register_action` calls
- confirm binding row in settings is enabled and action ID matches exactly
- inspect EDMC log for backend start/registration warnings

Remediation:
- register actions during plugin startup path
- correct binding `action_id` and enable row
- resolve backend prerequisites (session type, dependencies, bridge setup)

### 2. `register_action(...)` returns `False`
Likely causes:
- duplicate `action.id`
- invalid `thread_policy`
- callback is not callable
- `EDMCHotkeys` plugin not started

Checks:
- ensure `action.id` is globally unique
- confirm `thread_policy` is exactly `"main"` or `"worker"`
- verify callback function object is passed

Remediation:
- rename conflicting action IDs
- fix policy string
- register after `EDMCHotkeys` is available

### 3. `invoke_action(...)` returns `False`
Likely causes:
- action ID not registered
- action is disabled
- callback raised exception
- dispatch path failed

Checks:
- call `list_actions()` and verify target action exists/enabled
- inspect logs for "was not found", "is disabled", or exception traces

Remediation:
- correct action ID
- set action enabled
- harden callback error handling

### 4. `list_bindings(plugin_name)` returns empty unexpectedly
Likely causes:
- blank plugin name
- plugin name mismatch with persisted binding owner
- no bindings owned by that plugin

Checks:
- ensure `plugin_name` is non-empty
- compare requested name to binding `plugin` owner text
- confirm expected rows exist in settings/bindings document

Remediation:
- pass non-empty plugin name
- align plugin owner names used in bindings and registration

### 5. Side-specific binding fails on Linux Wayland keyd
Likely causes:
- backend is not actually `linux-wayland-keyd`

Checks:
- confirm backend path is `linux-wayland-keyd`
- check keyd integration/export state in settings

Remediation:
- ensure keyd integration is installed/applied and service is active

### 6. Main-thread dispatch timeout warnings
Likely causes:
- main-thread dispatch queue not being pumped in current runtime path
- long-running callback blocking dispatch responsiveness

Checks:
- inspect logs for timeout warnings
- verify callback thread policy and workload characteristics

Remediation:
- keep UI callbacks lightweight
- move non-UI/slow work to `thread_policy="worker"`

### 7. Backend unavailable at startup
Likely causes:
- missing platform prerequisites (for example `python-xlib`, keyd service, session env)
- unsupported session mode for forced backend mode
- keyd not installed or not active on Wayland

Checks:
- inspect backend selection/unavailability log lines
- verify environment:
  - `XDG_SESSION_TYPE`
  - `DISPLAY`
  - `WAYLAND_DISPLAY`

Remediation:
- install required backend dependency bundle
- run matching backend mode for active session
- for Wayland keyd: install/apply keyd integration and restart EDMC

## Useful Log Query
```bash
rg -n "EDMCHotkeys|backend|register|invoke|Auto-disabled binding|Timed out waiting for main-thread dispatch" \
  ~/edmc-logs/EDMarketConnector-debug.log
```

## Escalation
If the above checks do not isolate the issue:
1. capture relevant log lines around backend start and action registration
2. include your action registration snippet and one failing binding example
3. include session info (`XDG_SESSION_TYPE`, `DISPLAY`, `WAYLAND_DISPLAY`)
