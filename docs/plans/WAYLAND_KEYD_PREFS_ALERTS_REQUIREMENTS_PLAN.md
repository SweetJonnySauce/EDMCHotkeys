# Wayland keyd Preferences Alerts Requirements Plan

Status: In Progress  
Owner: EDMCHotkeys  
Last Updated: 2026-03-08

Follow persona details in AGENTS.md
Document implementation results in the Implementation Results section.
After each stage is complete change status to Completed
When all stages are complete change the phase status to Completed
if something is not clear, ask clarifying questions

## Objective
Add clear, minimal setup/export guidance in the EDMCHotkeys preferences pane for `wayland_keyd` users, with optional one-click actions and safe manual fallback commands.

## UI Placement Requirement
- Render the alerts/instructions block in preferences directly below the `Add Binding` button.

## Top-Level Requirements
1. Only show this flow when the selected runtime backend is `wayland_keyd`.
   - Exception: in `auto` mode on Wayland, if `wayland_keyd` is preferred but not selected because keyd is unavailable/inactive, show a short keyd-availability hint.
   - Hint text: `EDMCHotkeys is running in Wayland auto mode, but keyd is not active. Install/start keyd, restart EDMC, then return to this settings page to enable keyd integration.`
2. Detect whether `keyd` is available and service is active.
3. If `keyd` is unavailable or inactive:
   - Show instructions to install `keyd`.
   - Instruct user to restart EDMC.
   - Instruct user to return to settings page for integration steps.
4. Detect whether keyd integration install has completed successfully.
5. If integration is not installed:
   - Explain what integration does.
   - Provide two buttons:
     - `Install Integration`: runs integration install automatically.
     - `Copy Commands`: copies equivalent manual commands.
6. If keyd + integration are installed:
   - Show no informational block by default.
   - Only show UI again when bindings changed and export/apply is required.
7. If export/apply is required:
   - Provide two buttons:
     - `Export Config`: exports/applies updated config only (no restart).
     - `Copy Commands`: copies equivalent manual commands.
8. If elevated privileges are required, show an explicit warning.
9. If automatic action opens a terminal window, show an explicit warning.

## UX State Model
1. `Inactive` (backend is not `wayland_keyd`)
   - No alert block shown.
2. `KeydMissing`
   - Show install-keyd instructions only.
3. `IntegrationMissing`
   - Show integration explanation + `Install Integration` + `Copy Commands`.
4. `Ready`
   - Hide alert block.
5. `ExportRequired`
   - Show export-needed message + `Export Config` + `Copy Commands`.

## Detection Requirements
- `keyd available`:
  - True when both are true:
    - `keyd` executable is discoverable (`command -v keyd` equivalent).
    - keyd service/process is active:
      - systemd hosts: `systemctl is-active keyd`
      - non-systemd hosts: `pgrep -x keyd`
- `integration installed`:
  - True when all are true:
    - helper exists and executable: `/usr/local/bin/edmchotkeys_send.py`
    - active config exists: `/etc/keyd/edmchotkeys.conf`
    - keyd config validates (`keyd check /etc/keyd/edmchotkeys.conf` succeeds).
- `export required`:
  - True when generated bindings state indicates change requiring apply.
  - Source of truth: `keyd/runtime/export_state.json` (`reload_required` and hash comparison behavior from exporter contract).

## Button Action Requirements
- `Install Integration`:
  - Runs in terminal.
  - Performs helper install + config apply only (no restart).
  - Must surface stdout/stderr summary in plugin logs.
- `Export Config`:
  - Runs in terminal.
  - Performs config apply only (no restart).
  - Must surface stdout/stderr summary in plugin logs.
- Post-action behavior:
  - After automatic actions complete, refresh state immediately and update/hide the alert block based on new state.
  - Show inline success confirmation when action completes successfully.
- `Copy Commands`:
  - Copies one combined command block matching current resolved paths/config.
  - For integration-missing state:
    - copy combined block for install + apply
    - systemd hosts: include restart command (`sudo systemctl restart keyd`)
    - non-systemd hosts: do not include restart command; include manual restart instruction text.
  - For export-required state:
    - copy combined block for apply
    - systemd hosts: include restart command (`sudo systemctl restart keyd`)
    - non-systemd hosts: do not include restart command; include manual restart instruction text.

## Warning Requirements
- Privilege warning text must be shown next to auto-action buttons:
  - Action uses `sudo` / elevated privileges.
- Terminal warning text must be shown:
  - Automatic run opens a terminal/auth prompt.
- Errors from automatic actions must be displayed inline in preferences (not logs-only).
  - Error presentation must be a short user-friendly summary with a `Details` toggle for full output.

## Terminal Launcher Portability Requirement
- Automatic action buttons must use terminal execution.
- Launcher fallback order:
  1. `x-terminal-emulator`
  2. `kgx`
  3. `gnome-terminal`
  4. `konsole`
  5. `xfce4-terminal`
  6. `xterm`
- Runtime behavior:
  - Probe launchers in order and use the first available executable.
  - Execute the prepared command block in that terminal.
  - Terminal should remain open after command completion; user closes it manually.
- If no terminal launcher is available, show inline error text and instruct user to use `Copy Commands`.

## Phase Plan
## Phase 1 — Requirements Freeze (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Freeze visibility gates: selected runtime backend `wayland_keyd` + `auto` fallback hint behavior | Completed |
| 1.2 | Freeze detection matrix for systemd/non-systemd keyd availability + integration/export-required signals | Completed |
| 1.3 | Freeze command policy: auto actions do not restart; copied block includes restart only on systemd | Completed |
| 1.4 | Freeze terminal execution policy and launcher fallback order (terminal remains open) | Completed |
| 1.5 | Freeze user feedback model: inline success + user-friendly inline errors with `Details` toggle | Completed |

## Phase 2 — Preferences UI Integration (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Add alert container below `Add Binding` button and wire dynamic state rendering | Completed |
| 2.2 | Render all UI states/messages/buttons (`Inactive`, `KeydMissing`, `IntegrationMissing`, `Ready`, `ExportRequired`, auto-hint) | Completed |
| 2.3 | Wire `Copy Commands` combined-block behavior with systemd/non-systemd restart-rule differences | Completed |
| 2.4 | Implement inline success banner and inline error summary + `Details` toggle UX | Completed |
| 2.5 | Implement post-action auto-refresh so UI updates/hides immediately after action completion | Completed |

## Phase 3 — Detection + Execution Wiring (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Implement selected runtime-backend detection and `auto`-mode keyd-unavailable hint trigger | Completed |
| 3.2 | Implement keyd availability checks (`command -v` + `systemctl is-active` / `pgrep -x`) | Completed |
| 3.3 | Implement integration-installed detection (helper/config/keyd check pass) | Completed |
| 3.4 | Implement export-required detection from exporter state | Completed |
| 3.5 | Implement terminal launcher probing/fallback and terminal-open execution behavior | Completed |
| 3.6 | Implement install/apply action execution and command-block generation policy | Completed |

## Phase 4 — Tests and Validation (Status: In Progress)
| Stage | Description | Status |
| --- | --- | --- |
| 4.1 | Unit tests for state transitions, including `auto` fallback hint path | Completed |
| 4.2 | Unit tests for command-block generation (systemd vs non-systemd restart handling) | Completed |
| 4.3 | Unit tests for terminal launcher fallback and no-launcher inline error path | Completed |
| 4.4 | Unit tests for inline success + inline error summary/`Details` toggle behavior | Completed |
| 4.5 | Manual validation on Wayland + `wayland_keyd` | Pending |

### Phase 1 Detailed Execution Plan
| Stage | Goal | Detailed Work Plan | Required Artifacts | Exit Criteria |
| --- | --- | --- | --- | --- |
| 1.1 | Freeze visibility gates and auto-hint behavior | Define exact gating source as selected runtime backend; document auto-mode exception and approved hint string; confirm `Inactive` state behavior in non-keyd runtime selections. | Finalized requirement text in this plan; state machine mapping table. | No ambiguity remains on when alert block appears or is hidden. |
| 1.2 | Freeze detection matrix | Define deterministic checks for `keyd available`, `integration installed`, and `export required`; document systemd/non-systemd branches and failure semantics. | Detection requirements section with exact command semantics. | Each state transition has one canonical detector and fallback behavior. |
| 1.3 | Freeze command policy | Lock auto-action behavior (`--install --apply` vs `--apply`), restart policy (systemd copy-only), and manual restart instructions for non-systemd hosts. | Button-action requirements and copied-command policy text. | Command behaviors are deterministic and host-appropriate. |
| 1.4 | Freeze terminal execution policy | Lock launcher fallback order, "keep terminal open" behavior, and no-launcher fallback UX path. | Terminal launcher portability requirement section. | Auto-action execution policy is implementable without unresolved platform assumptions. |
| 1.5 | Freeze feedback UX contract | Lock inline success message requirement and inline error summary + `Details` toggle requirement; confirm logs are supplemental, not primary UX. | Warning/feedback requirements section. | Success/failure user feedback behavior is explicit and testable. |

### Phase 1 Deliverables Checklist
1. [x] Requirements text is internally consistent with no contradictory restart behavior.
2. [x] Detection and command policies are fully specified for systemd and non-systemd.
3. [x] Terminal fallback and inline feedback requirements are finalized.
4. [x] Phase 2/3 implementation stages align one-to-one to frozen requirements.

### Phase 1 Validation Plan
1. Plan review pass for contradictions (restart policy, gating source, auto-hint behavior).
2. Command-policy review against existing scripts:
   - `scripts/install_keyd_integration.sh`
   - `scripts/verify_keyd_integration.sh`
3. Update this plan if script contract changes are required before implementation starts.

### Phase 1 Validation Results (2026-03-08)
| Stage | Validation Performed | Evidence | Result |
| --- | --- | --- | --- |
| 1.1 | Reviewed gating and hint requirements in Top-Level Requirements + UX state model. | `wayland_keyd` selected-backend gate and approved auto-mode hint text are present and explicit. | Completed |
| 1.2 | Reviewed detector requirements for systemd and non-systemd host paths. | Detection section defines `command -v` + `systemctl is-active`/`pgrep -x` plus integration/export criteria. | Completed |
| 1.3 | Reviewed command policy text and compared with current scripts. | Policy is frozen in plan; current `scripts/install_keyd_integration.sh --apply` still restarts keyd, so implementation alignment is required in Phase 3. | Completed |
| 1.4 | Reviewed terminal policy and fallback order. | Launcher order, terminal-open behavior, and no-launcher inline-error fallback are explicitly defined. | Completed |
| 1.5 | Reviewed inline success/error UX contract. | Inline success requirement and user-friendly summary + `Details` toggle requirement are explicitly defined. | Completed |

#### Phase 1 Command Review Outputs
1. `bash -n scripts/install_keyd_integration.sh scripts/verify_keyd_integration.sh scripts/uninstall_keyd_integration.sh`  
   Result: pass (no shell syntax errors).
2. `./scripts/install_keyd_integration.sh --help`  
   Result: confirms current contract still says `--apply` installs config and restarts keyd; planned behavior updates remain in Phase 3 scope.

### Phase 2 Detailed Execution Plan
| Stage | Goal | Detailed Work Plan | Required Artifacts | Exit Criteria |
| --- | --- | --- | --- | --- |
| 2.1 | Add alert container in prefs | Add a dedicated keyd-status panel below `Add Binding`; ensure panel can be hidden/shown without disturbing existing layout. | Updated preferences UI code path (likely `edmc_hotkeys/settings_ui.py`). | Panel is rendered in required location and does not regress existing controls. |
| 2.2 | Render state-specific content | Implement state-to-view rendering for `Inactive`, `KeydMissing`, `IntegrationMissing`, `Ready`, `ExportRequired`, and auto-hint path. | State rendering helpers + view templates/messages. | Each state renders correct text/buttons and `Ready`/`Inactive` hide behavior works. |
| 2.3 | Wire `Copy Commands` behavior | Implement combined command block generation with systemd/non-systemd restart-rule branching; wire clipboard copy action and confirmation feedback. | Command-block builder + clipboard integration hooks. | Copied text matches policy and is verified in both host branches. |
| 2.4 | Implement inline status UX | Add inline success message and inline error summary with `Details` toggle; keep output concise by default. | UI components for success/error details; message formatting helpers. | Users see immediate, understandable status without checking logs. |
| 2.5 | Auto-refresh after actions | Refresh state immediately after auto-action completion and update/hide panel accordingly. | Refresh trigger wiring from action completion callback. | Panel converges to correct post-action state without manual reopen/restart of settings. |

### Phase 2 Deliverables Checklist
1. [x] Alert panel added below `Add Binding`.
2. [x] All required states rendered with approved text and button labels.
3. [x] Copy-to-clipboard command block behavior implemented.
4. [x] Inline success/error UX implemented with `Details` toggle.
5. [x] Post-action auto-refresh behavior implemented.

### Phase 2 Test Plan
1. `source .venv/bin/activate && python -m pytest tests -k "settings_ui or prefs or keyd"`
2. `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`
3. Manual smoke in EDMC settings pane:
   - verify panel placement and visibility in each state.

### Phase 2 Validation Results (2026-03-08)
| Stage | Validation Performed | Evidence | Result |
| --- | --- | --- | --- |
| 2.1 | Added alert container in settings UI below `Add Binding`; moved validation label below alert container. | `edmc_hotkeys/settings_ui.py` `_build_layout` now defines `_keyd_alert_frame` at row 3 and validation at row 4. | Completed |
| 2.2 | Added explicit state model/rendering helper for all required states including auto-hint. | `keyd_alert_view_for_state` handles `Inactive`, `KeydMissing`, `IntegrationMissing`, `Ready`, `ExportRequired`, `AutoHint`. | Completed |
| 2.3 | Added combined command-block builder with systemd/non-systemd restart handling and copy button wiring. | `build_keyd_copy_commands`; `SettingsPanel._on_keyd_copy_commands`; tests in `tests/test_settings_ui.py`. | Completed |
| 2.4 | Added inline success and inline error summary with details toggle UX. | `show_keyd_alert_success`, `show_keyd_alert_error`, `_toggle_keyd_error_details`. | Completed |
| 2.5 | Added action outcome flow that refreshes rendered alert state post-action. | `_apply_keyd_action_outcome` applies `refreshed_alert`; `_on_keyd_primary_action` route covered by tests. | Completed |

#### Phase 2 Command/Test Outputs
1. `source .venv/bin/activate && python -m pytest tests -k "settings_ui or prefs or keyd"`  
   Result: `70 passed, 154 deselected`.
2. `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`  
   Result: pass (no compile errors).
3. Manual EDMC settings-pane smoke test  
   Result: not run in this headless environment (deferred to local interactive validation).

### Phase 3 Detailed Execution Plan
| Stage | Goal | Detailed Work Plan | Required Artifacts | Exit Criteria |
| --- | --- | --- | --- | --- |
| 3.1 | Runtime backend + auto-hint detection | Read selected runtime backend from plugin runtime status path; implement auto-wayland keyd-unavailable hint trigger branch. | Backend-status adapter/helper consumed by prefs UI. | Gating uses actual selected backend and auto-hint appears only in intended fallback case. |
| 3.2 | keyd availability detection | Implement binary + active-service/process checks with systemd/pgrep branching; return normalized detector result for UI state engine. | Detection helper module/function with explicit result object. | `keyd available` truth table matches requirements across host types. |
| 3.3 | Integration-installed detection | Implement helper/config/check detector (`/usr/local/bin/edmchotkeys_send.py`, `/etc/keyd/edmchotkeys.conf`, `keyd check`). | Integration detector helper + error classification. | Integration state is accurately detected and errors are explainable. |
| 3.4 | Export-required detection | Read exporter state (`keyd/runtime/export_state.json`) and derive apply-needed state; handle missing/invalid state robustly. | Export-state detector helper. | Export-needed state is deterministic and resilient to missing/corrupt state files. |
| 3.5 | Terminal launcher execution | Implement launcher probing in configured order; execute auto-action command in terminal and keep terminal open. | Terminal runner helper with launcher fallback chain. | Auto-action launches in first available terminal; no-launcher case shows inline error. |
| 3.6 | Command execution + copy generation | Implement action command preparation and combined copy-block generation with systemd/non-systemd restart rules. | Command builder/shared formatter used by actions and copy button. | Executed and copied commands are consistent and policy-compliant. |

### Phase 3 Deliverables Checklist
1. [x] Detector helpers implemented for backend, keyd availability, integration, and export-required.
2. [x] Terminal launcher runner implemented with required fallback order.
3. [x] Action execution wiring complete for install/apply buttons.
4. [x] Combined copy-block generator implemented with restart policy branching.

### Phase 3 Test Plan
1. `source .venv/bin/activate && python -m pytest tests -k "keyd and (detector or command or terminal or prefs)"`
2. `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`
3. Targeted script contract sanity:
   - `bash -n scripts/install_keyd_integration.sh scripts/verify_keyd_integration.sh`

### Phase 3 Validation Results (2026-03-08)
| Stage | Validation Performed | Evidence | Result |
| --- | --- | --- | --- |
| 3.1 | Wired selected backend gating + auto-wayland keyd-unavailable hint trigger. | `load.py` `_build_keyd_alert_model` + `_should_show_auto_keyd_hint`; unit coverage in `tests/test_load_keyd_prefs_alerts.py`. | Completed |
| 3.2 | Implemented keyd availability detector with strict systemd/non-systemd branches. | `edmc_hotkeys/keyd_prefs_alerts.py` `detect_keyd_availability`; unit coverage in `tests/test_keyd_prefs_alerts.py`. | Completed |
| 3.3 | Implemented integration detector for helper/config/`keyd check` contract. | `edmc_hotkeys/keyd_prefs_alerts.py` `detect_keyd_integration`; unit coverage in `tests/test_keyd_prefs_alerts.py`. | Completed |
| 3.4 | Implemented export-required detector from `export_state.json` (`reload_required`). | `edmc_hotkeys/keyd_prefs_alerts.py` `detect_keyd_export_required`; unit coverage in `tests/test_keyd_prefs_alerts.py`. | Completed |
| 3.5 | Implemented terminal launcher fallback probe + terminal command launch and status/log capture files. | `edmc_hotkeys/keyd_prefs_alerts.py` `launch_terminal_command`; `load.py` pending-action poll wiring. | Completed |
| 3.6 | Implemented install/export action execution wiring, no-restart auto actions, and completion polling refresh flow. | `load.py` `_run_install_integration_action`, `_run_export_config_action`, `_run_keyd_terminal_action`, `_poll_pending_keyd_action`. | Completed |

#### Phase 3 Command/Test Outputs
1. `source .venv/bin/activate && python -m pytest tests/test_keyd_prefs_alerts.py tests/test_load_keyd_prefs_alerts.py`  
   Result: `13 passed`.
2. `source .venv/bin/activate && python -m pytest tests -k "keyd and (detector or command or terminal or prefs)"`  
   Result: `18 passed, 219 deselected`.
3. `source .venv/bin/activate && python -m pytest tests -k "settings_ui or prefs or keyd"`  
   Result: `83 passed, 154 deselected`.
4. `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`  
   Result: pass (no compile errors).

### Phase 4 Detailed Execution Plan
| Stage | Goal | Detailed Work Plan | Required Artifacts | Exit Criteria |
| --- | --- | --- | --- | --- |
| 4.1 | Validate state transitions | Add/extend unit tests covering all state transitions, including runtime-backend gating and auto-hint path. | State-machine tests in `tests/`. | All state combinations map to expected view/actions. |
| 4.2 | Validate command generation rules | Add unit tests for combined copy block content in systemd and non-systemd scenarios. | Command-block tests with host-mode fixtures. | Restart command inclusion/omission behavior matches requirements. |
| 4.3 | Validate terminal fallback/error path | Add tests for launcher probing order, first-available selection, and no-launcher inline error behavior. | Terminal-runner tests with mocked executables. | Launcher selection and failure handling are deterministic. |
| 4.4 | Validate inline success/error UX | Add tests for success message rendering and error summary + `Details` toggle behavior. | UI behavior tests for feedback components. | Users get concise feedback with optional full details. |
| 4.5 | Manual end-to-end validation | Run manual matrix on Wayland with keyd present/missing/integration-missing/export-required and confirm panel behavior/buttons. | Manual QA checklist + run notes. | End-to-end behavior matches acceptance criteria in live EDMC session. |

### Phase 4 Deliverables Checklist
1. [x] Unit coverage for state engine, command policy, terminal fallback, and feedback UX.
2. [ ] Manual QA checklist executed for all required states.
3. [x] No regressions in existing settings/bindings workflows.

### Phase 4 Test Plan
1. `source .venv/bin/activate && python -m pytest`
2. `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`
3. Manual QA on Linux Wayland:
   - keyd missing/inactive
   - integration missing
   - integration ready/no export required
   - export required with changed bindings

### Phase 4.5 Manual QA Runbook (Wayland Interactive)
Prereqs:
1. Run EDMC on Wayland with EDMCHotkeys installed and backend mode set to `wayland_keyd` (or `auto` for auto-hint case).
2. Ensure plugin path is correct and scripts are executable.
3. Keep EDMC debug log open for verification (`/home/jon/edmc-logs/EDMarketConnector-debug.log` in your environment).

Scenario A: `auto` hint when keyd unavailable
1. Stop keyd (`sudo systemctl stop keyd`) or otherwise make it inactive.
2. Set backend mode to `auto`.
3. Open EDMCHotkeys preferences.
Expected:
1. Alert block is visible below `Add Binding`.
2. Hint text matches approved auto-mode keyd-unavailable message.
3. No install/export action buttons are shown in this auto-hint state.

Scenario B: `KeydMissing`
1. Select backend mode `wayland_keyd` while keyd is unavailable/inactive.
2. Open EDMCHotkeys preferences.
Expected:
1. Alert summary indicates keyd is not installed/active.
2. Instructions mention install/start keyd, restart EDMC, then return to settings.

Scenario C: `IntegrationMissing`
1. Ensure keyd is active.
2. Remove integration artifacts:
   - helper `/usr/local/bin/edmchotkeys_send.py`
   - config `/etc/keyd/edmchotkeys.conf`
3. Open EDMCHotkeys preferences.
Expected:
1. Integration explanation is shown.
2. Buttons shown: `Install Integration`, `Copy Commands`.
3. Privilege and terminal warnings are shown.
4. `Copy Commands` contains install+apply block; includes systemd restart line on systemd hosts.

Scenario D: `Install Integration` auto action
1. From Scenario C, click `Install Integration`.
2. Complete sudo auth in opened terminal.
3. Wait for prefs panel to auto-refresh.
Expected:
1. Inline success appears on success.
2. Terminal remains open until user closes it.
3. On failure, inline error summary appears with `Show details`.
4. Plugin logs include action output summary.

Scenario E: `Ready` (no export required)
1. Ensure integration is installed and `reload_required` is false in export state.
2. Open EDMCHotkeys preferences.
Expected:
1. Alert block is hidden.

Scenario F: `ExportRequired`
1. Change/add a binding and save so export state becomes `reload_required=true`.
2. Open/reopen EDMCHotkeys preferences.
Expected:
1. Export-required alert is shown.
2. Buttons shown: `Export Config`, `Copy Commands`.
3. `Copy Commands` block includes restart line on systemd hosts; manual restart note on non-systemd hosts.

Scenario G: `Export Config` auto action
1. From Scenario F, click `Export Config`.
2. Complete terminal prompts if any.
Expected:
1. Inline success appears on success with restart instruction.
2. On failure, inline error summary + `Show details` appears.
3. After completion, panel refreshes and hides if state becomes `Ready`.

Evidence to capture:
1. Screenshot of each visible state panel (A/B/C/F).
2. `Copy Commands` pasted text for Scenario C and F.
3. Relevant EDMC log lines around action launch/completion/failure.
4. Any terminal output for failed actions.

### Phase 4 Validation Results (2026-03-08)
| Stage | Validation Performed | Evidence | Result |
| --- | --- | --- | --- |
| 4.1 | Expanded and ran state transition tests for keyd prefs alert model. | `tests/test_load_keyd_prefs_alerts.py` now covers `AutoHint`, `KeydMissing`, `IntegrationMissing`, `ExportRequired`, `Ready` paths. | Completed |
| 4.2 | Verified command-block generation behavior across restart policy modes. | `tests/test_settings_ui.py` and `tests/test_keyd_prefs_alerts.py` assert systemd restart inclusion and non-systemd manual restart text. | Completed |
| 4.3 | Verified terminal launcher fallback order and no-launcher error path. | `tests/test_keyd_prefs_alerts.py` validates first launcher and fallback (`x-terminal-emulator` -> `kgx`) and no-launcher inline fallback reason. | Completed |
| 4.4 | Verified inline success/failure and details toggle behavior paths. | `tests/test_settings_ui.py` (`_toggle_keyd_error_details`) and `tests/test_load_keyd_prefs_alerts.py` terminal action success/failure polling assertions. | Completed |
| 4.5 | Manual Wayland QA matrix execution. | Not run in this headless environment; requires interactive EDMC + keyd session. | Pending |

#### Phase 4 Command/Test Outputs
1. `source .venv/bin/activate && python -m pytest tests/test_settings_ui.py tests/test_keyd_prefs_alerts.py tests/test_load_keyd_prefs_alerts.py`  
   Result: `67 passed`.
2. `source .venv/bin/activate && python -m pytest`  
   Result: `243 passed`.
3. `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`  
   Result: pass (no compile errors).
4. Manual Wayland QA  
   Result: pending (requires local interactive validation).

## Acceptance Criteria
- Alerts appear only when selected runtime backend is `wayland_keyd`.
- Missing `keyd` users receive install + restart guidance.
- Missing integration users can install with one click or copy manual commands.
- Ready users see no extra info unless export/apply is required.
- Export-required users can apply via one click or copy command block.
- Copied command block behavior:
  - systemd hosts include restart command.
  - non-systemd hosts omit restart command and include manual restart instruction text.
- `auto` mode on Wayland shows the approved keyd-unavailable hint when keyd backend is preferred but not selected.
- Privilege/terminal warnings are visible.
- Auto-action success is shown inline.
- Auto-action failures show inline user-friendly summary with `Details` toggle.

## Implementation Results
## Phase 1 — Requirements Freeze
- Finalized and documented the complete requirements contract for:
  - selected-backend gating and auto-mode fallback hint text
  - systemd/non-systemd detection logic
  - copy-command restart behavior split by host type
  - terminal launcher fallback order and keep-open behavior
  - inline success and inline error-with-details UX
- Completed a command-policy review against existing integration scripts.
- Identified one known implementation delta to address in later phases:
  - current `--apply` behavior still restarts keyd; plan requires auto-actions to avoid restart.

## Phase 2 — Preferences UI Integration
- Added a dedicated keyd alert panel below `Add Binding` in the preferences layout.
- Implemented state-driven keyd alert view models for all required states and the approved auto-hint message.
- Implemented command-block generation for `Copy Commands`, including:
  - systemd hosts: include `sudo systemctl restart keyd`
  - non-systemd hosts: include manual restart instruction text
- Added inline success UX plus inline error summary with `Show details` / `Hide details` toggle.
- Added primary-action outcome handling that supports post-action state refresh (`refreshed_alert`).
- Added unit tests validating:
  - state view generation
  - copy command block rules
  - primary-action outcome path and exception-to-inline-error path

## Phase 3 — Detection + Execution Wiring
- Added a new keyd prefs integration helper module with:
  - keyd availability detection (`command -v keyd` + strict systemd/pgrep active checks)
  - integration detection (helper/config/`keyd check`)
  - export-required detection from `keyd/runtime/export_state.json`
  - command set generation for install/apply/export flows
  - terminal launcher fallback probing and launch wrappers with runtime status/log file tracking
- Wired preferences alert rendering to runtime state detection in `load.py`:
  - selected backend gate for `linux-wayland-keyd`
  - auto-mode Wayland keyd-unavailable hint path
  - integration-missing and export-required action callbacks
- Wired automatic terminal action flow in `load.py`:
  - no-restart auto action command blocks (`Install Integration`, `Export Config`)
  - pending action polling using status/log files
  - auto-refresh of alert state after action completion
  - inline success/error updates with terminal output surfaced in plugin logs
- Added focused unit tests for:
  - detector logic
  - command generation policy
  - terminal launcher fallback behavior
  - load-layer alert model wiring and terminal action polling

## Phase 4 — Tests and Validation
- Expanded Phase 4 unit coverage to include:
  - full keyd prefs state transition coverage in the load-layer alert model
  - systemd/non-systemd command policy assertions
  - terminal launcher fallback ordering and no-launcher handling
  - inline error details toggle behavior and terminal-action success/failure polling
- Executed full project regression suite:
  - `python -m pytest` -> `243 passed`
  - `python -m compileall load.py edmc_hotkeys tests` -> pass
- Remaining pending work:
  - manual Wayland interactive QA matrix execution (`keyd missing`, `integration missing`, `ready`, `export required`) is not runnable in this headless environment.
- Added a concrete Stage 4.5 manual QA runbook with scenario-by-scenario expected outcomes and evidence capture list to close manual validation quickly.
