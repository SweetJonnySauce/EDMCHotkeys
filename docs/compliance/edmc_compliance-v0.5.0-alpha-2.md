# EDMC Compliance Tracker

Status: Completed  
Owner: EDMCHotkeys  
Date Checked: 2026-03-08  
Version Checked: 0.5.0-alpha-2

Prompt Used: Check compliance of this EDMC plugin against EDMC best practices. Copy `docs/compliance/_edmc_compliance_template.md` to a new file called `edmc_compliance-v0.0.0.md` in the same directory where `0.0.0` is the semver we are checking. Note whether this plugin meets or does not meet the requirement. If it does not meet the requirement, note the deficiency in the assessment along with what actions need to be taken.

## Exceptions
- configs stored in bindings.json will not be set with EDMC's `config.set/get_*`.

## Current Compliance Assessment

| Requirement | Meets Requirement (Yes/No) | Evidence | Deficiency | Required Action |
| --- | --- | --- | --- | --- |
| Stay aligned with EDMC core (`load.py` entrypoint, plugin directory structure, baseline Python checks, release/discussion monitoring) | No | `plugin_start3` exists in `load.py`; plugin is in its own directory. Missing `scripts/check_edmc_python.py` and missing `docs/compliance/edmc_python_version.txt`. | Baseline Python compliance enforcement is not implemented; EDMC core release/discussion monitoring process is not documented. | Add `scripts/check_edmc_python.py` and `docs/compliance/edmc_python_version.txt`; add CI check and release checklist item for EDMC Releases/Discussions monitoring cadence. |
| Use supported EDMC plugin API/helpers (`config`, `monitor`, `theme`, `timeout_session`, etc.) and avoid reimplementing EDMC runtime detection | Yes | Runtime integration uses EDMC `config` access via `get_str` fallback in `load.py`/`runtime_config.py`; no unsupported EDMC-internal imports detected. | None for current scope. | Keep import audits in release checks; if player-state logic is added, use `monitor.game_running()`/`monitor.is_live_galaxy()`. |
| Persist plugin settings with `config.set/get_*` namespaced keys and shared EDMC utility patterns | No | Settings are persisted primarily via plugin-local files (`bindings.json`, `config.ini`/`config.defaults.ini`), not EDMC `config.set/get_*`. | Preference persistence diverges from EDMC best-practice storage guidance. | Define migration plan for EDMC config-backed settings where appropriate; document explicit rationale for any intentionally file-backed state that must stay external. |
| Use EDMC logging/versioning patterns (`logger`, no `print` in runtime plugin code, `plugin_name` alignment, traceback logging) | No | Logger wiring is correct (`plugin_name = "EDMCHotkeys"`; logger namespaced); traceback logging uses `logger.exception`/`exc_info`. No `print()` in `load.py`/`edmc_hotkeys/*.py`. | `config.appversion` is not used to gate EDMC-version-specific behavior. | Add `config.appversion` compatibility gating where EDMC API-version differences are relevant (or document why all supported EDMC versions are behaviorally equivalent). |
| Keep runtime responsive and Tk-safe (worker threads for long-running/network tasks, UI only on main thread, safe shutdown/event behavior) | Yes | Backend listeners and worker dispatch use background threads (`registry.py`, backend modules). UI is managed through prefs panel path on main thread; no unsafe `event_generate` usage found. | None identified for current runtime behavior. | Maintain this boundary; if network calls are added to runtime hooks, route them through worker paths. |
| Integrate with EDMC prefs/UI hooks (`plugin_prefs`, `prefs_changed`, `myNotebook`, `config.get_int/str/bool/list`, `number_from_string`) | No | `plugin_prefs` and `prefs_changed` are implemented; `myNotebook` support is present with fallback. | Prefs path does not use EDMC typed config helpers (`get_int/get_bool/get_list`) or `number_from_string` where applicable. | Refactor preference reads/writes for EDMC-managed settings to typed config helpers; use locale-aware parsers for numeric user input surfaces. |
| Package dependencies and debug HTTP responsibly (venv, vendored deps, importable dir names, `debug_senders` for HTTP debug routing) | No | Dependency vendoring exists (`scripts/vendor_xlib.sh`) and plugin directory naming is import-safe (`EDMCHotkeys`). | No documented/runtime `config.debug_senders` HTTP debug routing path; no standard `timeout_session` helper path for future HTTP runtime traffic. | Add a small HTTP client utility that uses `timeout_session.new_session` + `config.user_agent` + `debug_senders` routing, and require it for all future runtime HTTP integrations. |
| Checks: Python baseline file/script and CI enforcement present | No | `.github/workflows/ci.yml` runs `make check`; baseline artifacts/script referenced in policy are absent. | Required compliance check assets are missing. | Implement the missing baseline script/file and add them to `make check` and CI. |
| Checks: Logger wiring and no runtime `print` in plugin modules | Yes | Logger initialization and plugin name alignment in `load.py`; no `print()` usage in `load.py` or `edmc_hotkeys/*.py`. | None. | Keep `scripts/check_no_print.py` gate in CI and enforce runtime module scope. |
| Checks: Long-running work off main thread / Tk safety | Yes | Threaded dispatch and backend listeners are present; dispatch queue pumping is explicit. | None identified. | Preserve thread-policy tests and add targeted tests when adding new background operations. |
| Checks: Prefs hooks use EDMC helper APIs and namespaced config keys | No | Prefs hooks exist and namespaced key exists for backend mode; typed config helper usage is incomplete. | Incomplete adherence to EDMC prefs-helper best practices. | Adopt `config.get_int/str/bool/list` in prefs pathways and document exceptions. |
| Checks: Monitor EDMC releases/discussions and include compliance items in PR checklist | No | PR template exists but does not include EDMC release/discussion monitoring or explicit compliance ticks from this checklist. | Governance/process gap. | Extend `.github/pull_request_template.md` with EDMC monitoring + compliance checklist items and required confirmation. |

## Recommended Action Plan (Priority)
1. Add missing baseline enforcement artifacts: `scripts/check_edmc_python.py` and `docs/compliance/edmc_python_version.txt`; wire into `make check` and CI.
2. Add EDMC compliance checklist items to `.github/pull_request_template.md`, including EDMC release/discussion monitoring confirmation.
3. Refactor EDMC-managed settings surfaces to `config.get_*`/`config.set` helper usage with namespaced keys.
4. Add compatibility policy for `config.appversion` (gated behavior or explicit documented rationale).
5. Add an HTTP utility wrapper for future runtime HTTP usage (`timeout_session`, `config.user_agent`, `debug_senders`) and codify as required path.

## Checks Run For This Assessment
- Repository scan for entrypoints, prefs hooks, logger wiring, and banned runtime `print` usage.
- Verification of baseline Python compliance artifacts and CI workflow content.
- Verification of dependency-vendoring path and plugin directory naming/importability.
