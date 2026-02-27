# GNOME Wayland Bridge Phase 4 QA Matrix

Date: 2026-02-26  
Scope: Phase 4 manual/integration verification evidence for companion artifact track.

## Environment Baseline
- Ubuntu: `24.04.3 LTS`
- GNOME Shell: `46.0`
- Session target: GNOME Wayland companion path

## QA Matrix
| ID | Scenario | Type | Status | Evidence |
| --- | --- | --- | --- | --- |
| QA-4.3-01 | Install companion artifact in isolated HOME | Scripted manual | Pass | `./scripts/install_gnome_bridge_companion.sh` returned `0` (temp HOME run). |
| QA-4.3-02 | Verify companion artifact layout/config | Scripted manual | Pass | `./scripts/verify_gnome_bridge_companion.sh` returned `0` and printed `verify: OK`. |
| QA-4.3-03 | Export plugin bindings to companion config | Scripted manual | Pass | `./scripts/export_companion_bindings.py` returned `0` with `written=4 skipped_disabled=2 skipped_unsupported=0`. |
| QA-4.3-04 | Uninstall companion artifact and remove config | Scripted manual | Pass | `./scripts/uninstall_gnome_bridge_companion.sh --keep-enabled --remove-config` returned `0`. |
| QA-4.3-05 | Missing token file failure mode | Scripted manual | Pass | `gnome_bridge_companion_send.py` returned `2` with token-file resolution error. |
| QA-4.3-06 | Missing socket send/retry failure mode | Scripted manual | Pass | `gnome_bridge_companion_send.py` returned `1` with retry/failure logs. |
| QA-4.3-07 | Extension disabled while bridge backend active | Interactive | Pass | Extension reached `State: ACTIVE`, baseline enabled run produced `Hotkey pressed` events, then extension disable set `Enabled: No` / `State: INACTIVE` and bounded post-disable log window showed no new `Hotkey pressed` events. |
| QA-4.3-08 | Valid keypress activation (shortcut -> action dispatch) | Interactive | Pass | Extension enabled path (`Enabled: Yes`, `State: ACTIVE`) produced bounded-slice dispatch logs with `Hotkey pressed ... source=backend:linux-wayland-gnome-bridge` for configured shortcuts. |
| QA-4.3-09 | Backend mode switch across restart | Interactive | Pass | Three restart-mode runs validated selection behavior: `auto` -> `linux-wayland-gnome-bridge` started; `wayland_gnome_bridge` -> bridge started; `wayland_portal` -> portal selected and failed non-fatally with explicit `GlobalShortcuts` interface warning. |
| QA-4.3-10 | Stale runtime dir/socket recovery with live EDMC | Interactive | Pass | Injected stale runtime artifacts (`edmc_hotkeys` dir `0777`, stale `bridge.sock` file `0666`), restarted EDMC in bridge mode, backend started successfully on `/run/user/1000/edmc_hotkeys/bridge.sock`, and runtime dir/token were secured (`0700`/`0600`). |

## Command Evidence Snapshot
1. Install/verify/export/uninstall scripted workflow:
   - `install_rc=0`
   - `verify_rc=0`
   - `export_rc=0`
   - `uninstall_rc=0`
2. Failure mode checks:
   - missing token file run returned `rc=2`
   - missing socket run returned `rc=1`
3. Interactive disable-path evidence (QA-4.3-07):
   - `gnome-extensions info edmc-hotkeys@edcd` (enabled path) -> `Enabled: Yes`, `State: ACTIVE`
   - enabled-path log capture included multiple `Hotkey pressed` lines (`source=backend:linux-wayland-gnome-bridge`)
   - `gnome-extensions info edmc-hotkeys@edcd` (disabled path) -> `Enabled: No`, `State: INACTIVE`
   - bounded post-disable slice (`sed -n "$((before+1)),$p" ... | rg ...`) returned no `Hotkey pressed` matches
4. Interactive activation-path evidence (QA-4.3-08):
   - `gnome-extensions info edmc-hotkeys@edcd` -> `Enabled: Yes`, `State: ACTIVE`
   - bounded post-enable slice captured dispatch lines:
     - `Hotkey pressed: binding_id=hotkeys_test_on ... source=backend:linux-wayland-gnome-bridge`
     - `Hotkey pressed: binding_id=hotkeys_test_off ... source=backend:linux-wayland-gnome-bridge`
5. Backend mode switch across restart evidence (QA-4.3-09):
   - mode=`auto`, bridge flag=`1`:
     - selected `linux-wayland-gnome-bridge`
     - backend started on `/run/user/1000/edmc_hotkeys/bridge.sock`
   - mode=`wayland_gnome_bridge`, bridge flag=`1`:
     - selected `linux-wayland-gnome-bridge`
     - backend started on `/run/user/1000/edmc_hotkeys/bridge.sock`
   - mode=`wayland_portal`, bridge flag=`0`:
     - selected `linux-wayland-portal`
     - backend failed to start non-fatally with explicit warning:
       - `Wayland portal startup failed: No such interface “org.freedesktop.portal.GlobalShortcuts” ...`
6. Stale runtime dir/socket recovery evidence (QA-4.3-10):
   - injected stale state before launch:
     - `/run/user/1000/edmc_hotkeys` permissions `0777`
     - stale `/run/user/1000/edmc_hotkeys/bridge.sock` regular file permissions `0666`
   - bridge-mode launch selected and started:
     - `Hotkey backend selected: mode=wayland_gnome_bridge name=linux-wayland-gnome-bridge ...`
     - `Hotkey backend 'linux-wayland-gnome-bridge' started on /run/user/1000/edmc_hotkeys/bridge.sock`
   - no startup failure emitted for bridge backend in the bounded slice
   - post-run permissions confirmed hardened recovery:
     - runtime dir `0700`
     - token file `0600`

## Open Interactive Items
- None. Phase 4 interactive QA scenarios are complete (`QA-4.3-01` through `QA-4.3-10` all `Pass`).
