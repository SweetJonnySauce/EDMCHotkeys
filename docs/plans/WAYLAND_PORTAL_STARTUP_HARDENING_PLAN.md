# Wayland Portal Startup Hardening Plan

Status: Draft  
Owner: EDMC-Hotkeys  
Last Updated: 2026-02-26

## Problem Statement
Wayland startup currently fails with:

- `Wayland portal startup failed: invalid member name: power-saver-enabled`
- `Hotkey backend 'linux-wayland-portal' failed to start`

Goal: harden the plugin-side Wayland backend by removing runtime dependence on fragile portal introspection parsing and keeping behavior contract-compatible.

## Touch Points
- `edmc_hotkeys/backends/wayland.py`
- `tests/test_backends.py`
- `docs/linux-user-setup.md` (only if logging/behavior text needs updates)

## Expected Unchanged Behavior
- No public API changes.
- Wayland remains `supports_side_specific_modifiers=False`.
- Core capability gating stays in `load.py`.
- X11/Windows behavior unchanged.

## Phase 1 — Design Freeze (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 1.1 | Lock invariants from current logs/code (failure source, non-fatal startup requirement) | Completed |
| 1.2 | Define minimal static introspection XML for `GlobalShortcuts`, `Request`, and `Session` | Completed |
| 1.3 | Define explicit `Activated` signal argument handling contract | Completed |

## Phase 1 Detailed Execution Plan

Execution order:
1. Complete `1.1` before `1.2`.
2. Complete `1.2` before `1.3`.
3. Do not start Phase 2 code edits until all Phase 1 stages are complete.

### Stage 1.1 — Lock Invariants and Failure Contract
Objective:
- Freeze behavior-scoped invariants so implementation changes do not alter plugin contract.

Touch points:
- `edmc_hotkeys/backends/wayland.py`
- `/home/jon/edmc-logs/EDMarketConnector-debug.log`
- `docs/plans/CROSS_PLATFORM_COMPLEXITY_MINIMIZATION_SPEC.md`

Tasks:
- Record current failing path from startup logs (`invalid member name: power-saver-enabled`) and map it to runtime introspection usage.
- Record non-negotiable runtime invariants:
  - backend startup must remain non-fatal.
  - capability policy remains core-owned.
  - Wayland capability remains `supports_side_specific_modifiers=False`.
- Define explicit out-of-scope boundaries for this change:
  - no side-specific support expansion.
  - no compositor-specific bypass path.
  - no public API shape changes.

Acceptance criteria:
- A written invariants block exists in this plan and is referenced by implementation stages.
- Failure mode and likely root cause are documented in one place.
- Scope boundaries are explicit enough to reject drift during code review.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"`

Risk and rollback:
- Risk: over-constraining invariants can block needed internal refactors.
- Rollback: trim invariants to externally observable guarantees only.

### Stage 1.2 — Define Static Introspection Baseline
Objective:
- Define the minimal interface surface needed so startup does not depend on broad runtime introspection parsing.

Touch points:
- `edmc_hotkeys/backends/wayland.py`
- `tests/test_backends.py`
- This plan file

Tasks:
- Define minimal introspection XML for:
  - `org.freedesktop.portal.GlobalShortcuts`
  - `org.freedesktop.portal.Request`
  - `org.freedesktop.portal.Session`
- Limit methods/signals/properties to only members used by current backend flow:
  - session create
  - shortcut bind
  - request response signal
  - session close
  - activated signal
- Document each member and signature with source note (spec/runtime observation).
- Define parser fallback behavior if static definitions are unavailable/invalid (backend start must fail cleanly with actionable log).

Acceptance criteria:
- Static interface definitions are fully specified and implementation-ready.
- No unused members are included.
- Signatures required by current call sites are documented and test-plannable.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"`

Risk and rollback:
- Risk: signature mismatch can cause silent call/signal handling errors.
- Rollback: keep static set minimal and add assertion logs around method return/signal payload checks.

### Stage 1.3 — Define `Activated` Signal Contract
Objective:
- Remove ambiguity from current `*args` signal handling and define deterministic binding-id extraction.

Touch points:
- `edmc_hotkeys/backends/wayland.py`
- `tests/test_backends.py`
- This plan file

Tasks:
- Define canonical `Activated` callback argument contract used by backend code.
- Define allowed fallback parsing order when payload shape differs from expectation.
- Define guard behavior for malformed signal payloads:
  - no exception propagation to loop.
  - debug/warning logs with payload-shape context.
  - no action invocation when binding id is unresolved.
- Define idempotency/duplication expectation for repeated activated signals.

Acceptance criteria:
- One canonical extraction path and one documented fallback path.
- Malformed payload behavior is explicit and testable.
- Callback contract is clear enough to write deterministic unit tests.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"`

Risk and rollback:
- Risk: overly strict parsing drops valid activations from portal variants.
- Rollback: keep guarded fallback extraction plus diagnostic logs while preserving non-crashing behavior.

Phase 1 done definition:
- Stages `1.1`, `1.2`, and `1.3` marked `Completed`.
- Phase 1 status flipped to `Completed`.
- Phase 2 implementation can begin only after this section is reviewed/approved.

### Stage 1.1 Outputs (Completed)
Failure mapping:
- Runtime failure was observed in EDMC logs as:
  - `Wayland portal startup failed: invalid member name: power-saver-enabled`
  - backend/plugin startup failures immediately after.
- The backend startup path currently performs runtime portal introspection:
  - `DbusNextPortalService._initialize_async()` calls `bus.introspect(...)` before interface usage.
- `dbus-next` introspection parsing enforces D-Bus member-name rules and raises on invalid names.
  - Hyphenated names (such as `power-saver-enabled`) are invalid member names under that validator.

Locked invariants:
- Startup remains non-fatal when Wayland backend cannot initialize.
- Capability policy ownership remains in core (`load.py` startup/settings paths), not adapter code.
- Wayland capability declaration remains `supports_side_specific_modifiers=False`.
- No public API changes in plugin entry points.
- No compositor-specific fallback path is introduced in this hardening scope.

### Stage 1.2 Outputs (Completed)
Static introspection baseline (minimal members used by current backend flow):

`org.freedesktop.portal.GlobalShortcuts`:

```xml
<node>
  <interface name="org.freedesktop.portal.GlobalShortcuts">
    <method name="CreateSession">
      <arg name="options" type="a{sv}" direction="in"/>
      <arg name="handle" type="o" direction="out"/>
    </method>
    <method name="BindShortcuts">
      <arg name="session_handle" type="o" direction="in"/>
      <arg name="shortcuts" type="a(sa{sv})" direction="in"/>
      <arg name="parent_window" type="s" direction="in"/>
      <arg name="options" type="a{sv}" direction="in"/>
      <arg name="handle" type="o" direction="out"/>
    </method>
    <signal name="Activated">
      <arg name="session_handle" type="o"/>
      <arg name="shortcut_id" type="s"/>
      <arg name="timestamp" type="t"/>
      <arg name="options" type="a{sv}"/>
    </signal>
  </interface>
</node>
```

`org.freedesktop.portal.Request`:

```xml
<node>
  <interface name="org.freedesktop.portal.Request">
    <signal name="Response">
      <arg name="response" type="u"/>
      <arg name="results" type="a{sv}"/>
    </signal>
  </interface>
</node>
```

`org.freedesktop.portal.Session`:

```xml
<node>
  <interface name="org.freedesktop.portal.Session">
    <method name="Close"/>
  </interface>
</node>
```

Implementation note for Phase 2:
- Runtime `bus.introspect(...)` calls for these interfaces should be replaced with proxy objects built from these static nodes so unrelated portal metadata cannot break startup parsing.

### Stage 1.3 Outputs (Completed)
`Activated` contract for backend callback handling:
- Canonical expected signal args:
  - `session_handle: object-path`
  - `shortcut_id: string`
  - `timestamp: uint64`
  - `options: a{sv}`
- Canonical extraction path:
  - Use positional `shortcut_id` argument directly.
  - Ignore activation when `shortcut_id` is not in current registration map.
- Fallback parsing path (defensive only):
  - If positional shape is unexpected, scan string-like args for an exact registered binding id.
- Guard behavior:
  - Never raise from signal handler into event loop.
  - Log malformed/unsupported payload shapes at debug or warning level.
  - Do not invoke action callbacks when binding id is unresolved.
- Invocation behavior:
  - Maintain current edge-triggered behavior from portal signal delivery.
  - Do not introduce deduplication semantics in this phase.

## Phase 1 Implementation Results
- Phase 1 stages `1.1`–`1.3` completed in documentation with frozen invariants and implementation-ready contracts.
- Verification run:
  - `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"` passed (`7 passed, 16 deselected`).

## Phase 2 — Implementation (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 2.1 | Add helpers in `wayland.py` to build proxy objects from static introspection nodes | Completed |
| 2.2 | Replace runtime `bus.introspect(...)` call sites in startup/request/session-close paths | Completed |
| 2.3 | Tighten `on_activated` handling to explicit expected args with defensive fallback | Completed |
| 2.4 | Preserve and clarify actionable warning logs for startup failures | Completed |

## Phase 2 Detailed Execution Plan

Execution order:
1. Complete `2.1` before `2.2`.
2. Complete `2.2` before `2.3`.
3. Complete `2.3` before `2.4`.
4. Run targeted Wayland tests after each stage and full checks at phase end.

### Stage 2.1 — Add Static-Node Proxy Helpers
Objective:
- Introduce explicit helper seams that create portal proxy objects from static introspection definitions instead of runtime introspection XML.

Touch points:
- `edmc_hotkeys/backends/wayland.py`
- `tests/test_backends.py`

Tasks:
- Add module-level static introspection XML constants for:
  - `org.freedesktop.portal.GlobalShortcuts`
  - `org.freedesktop.portal.Request`
  - `org.freedesktop.portal.Session`
- Add helper functions to parse and cache static nodes safely.
- Add helper functions to create proxy objects/interfaces from those static nodes.
- Keep helper behavior pure/data-driven where possible (no policy decisions in helpers).
- Add defensive error wrapping so helper parse/build failures surface as actionable backend warnings.

Acceptance criteria:
- Startup code can obtain portal/request/session interfaces without calling `bus.introspect(...)` for these interfaces.
- Helper failures do not crash plugin startup and produce clear reason text.
- No backend capability semantics change in this stage.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"`

Risk and rollback:
- Risk: static XML signature mismatch with runtime methods/signals.
- Rollback: keep helper layer isolated so fallback to current path can be restored in one commit if needed.

### Stage 2.2 — Replace Runtime Introspect Call Sites
Objective:
- Move runtime call sites in startup/request/session-close flow to the new static helper path.

Touch points:
- `edmc_hotkeys/backends/wayland.py`
- `tests/test_backends.py`

Tasks:
- Replace `bus.introspect(...)` usage in:
  - `_initialize_async()`
  - `_wait_for_request_response_async()`
  - `_close_session_async()`
- Ensure create/bind/request/close lifecycle remains behavior-equivalent:
  - `CreateSession` still populates session handle.
  - `BindShortcuts` still synchronizes registered shortcuts.
  - request `Response` still drives completion futures.
  - session `Close` still runs during stop/shutdown.
- Keep non-fatal start semantics unchanged when any stage fails.

Acceptance criteria:
- No runtime dependency on broad portal introspection parsing remains in the above paths.
- Backend start failure still returns cleanly and logs root reason.
- Existing registration/unregistration flow remains deterministic.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"`
2. `source .venv/bin/activate && python -m pytest tests/test_phase6_smoke.py -k "backend"`

Risk and rollback:
- Risk: asynchronous request-response wiring regressions (timeouts, unresolved futures).
- Rollback: revert only call-site rewiring, keep static helper code staged for reattempt.

### Stage 2.3 — Implement Explicit `Activated` Signal Handling
Objective:
- Replace permissive `*args` handling with explicit contract-driven parsing while retaining defensive fallback.

Touch points:
- `edmc_hotkeys/backends/wayland.py`
- `tests/test_backends.py`

Tasks:
- Implement canonical extraction path using expected `Activated` arg positions.
- Implement documented fallback scan only when canonical shape is missing.
- Add guardrails:
  - unresolved/unknown binding IDs are ignored.
  - malformed payloads log diagnostics and do not raise.
  - callback exceptions are caught and logged with binding id context.
- Preserve current dispatch semantics (no dedupe/throttling changes).

Acceptance criteria:
- Signal handler behavior is deterministic and matches Phase 1 contract text.
- Malformed payloads do not break listener loop.
- Action callbacks receive only known binding IDs.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"`

Risk and rollback:
- Risk: strict parsing may reject valid portal variants.
- Rollback: keep guarded fallback path and downgrade strictness behind explicit logging.

### Stage 2.4 — Harden Diagnostics and Observability
Objective:
- Ensure operators can distinguish availability, startup, and runtime signal/register failure modes quickly from logs.

Touch points:
- `edmc_hotkeys/backends/wayland.py`
- `docs/linux-user-setup.md` (if message wording changes)
- `tests/test_backends.py`

Tasks:
- Standardize warning messages for:
  - static-node parse/build failures
  - startup initialization failure
  - bind/register operation failures
  - callback/runtime signal anomalies
- Include backend name and operation context in each failure log line.
- Keep noise controlled (single actionable warning per failure category where possible).
- Update docs if user-facing troubleshooting text needs alignment.

Acceptance criteria:
- Logs clearly separate:
  - `available=False` prerequisite failures
  - `available=True but start failed` runtime failures
  - registration/signal callback failures post-start
- Test coverage validates expected warning content for deterministic failure branches.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"`
2. `source .venv/bin/activate && make check`

Risk and rollback:
- Risk: excessive logging obscures key operator signals.
- Rollback: compress repeated warnings and keep one-line structured reason logs.

Phase 2 done definition:
- Stages `2.1`, `2.2`, `2.3`, and `2.4` marked `Completed`.
- Phase 2 status updated to `Completed`.
- Phase 2 implementation results added with executed commands and outcomes.

## Phase 2 Implementation Results
- Added static introspection XML + parse cache for:
  - `org.freedesktop.portal.GlobalShortcuts`
  - `org.freedesktop.portal.Request`
  - `org.freedesktop.portal.Session`
- Added static proxy-interface helper path in `DbusNextPortalService`:
  - `_portal_interface()`
  - `_request_interface(request_path)`
  - `_session_interface(session_path)`
  - `_static_interface(...)`
- Replaced runtime `bus.introspect(...)` usage in:
  - `_initialize_async()`
  - `_wait_for_request_response_async()`
  - `_close_session_async()`
- Tightened `Activated` handling to explicit contract-based callback:
  - explicit signal args in `_on_activated_signal(...)`
  - deterministic resolver via `_resolve_activated_binding_id(...)`
  - defensive unresolved-binding diagnostics (debug) and callback exception guard
- Expanded Wayland backend test coverage in `tests/test_backends.py`:
  - explicit activated signal binding-id path
  - options-based fallback extraction path
  - unknown binding ignore behavior
  - static request-interface proxy path behavior

Verification run:
- `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"` passed (`11 passed, 16 deselected`).
- `source .venv/bin/activate && python -m pytest tests/test_phase6_smoke.py -k "backend"` passed (`1 passed, 9 deselected`).
- `source .venv/bin/activate && python -m pytest` passed (`83 passed`).
- `source .venv/bin/activate && make test` passed (`83 passed`).
- `source .venv/bin/activate && make check` passed.

## Phase 3 — Validation (Status: Completed)
| Stage | Description | Status |
| --- | --- | --- |
| 3.1 | Add/adjust unit tests for Wayland startup path + callback arg handling | Completed |
| 3.2 | Run targeted Wayland backend tests | Completed |
| 3.3 | Run repository test/check targets | Completed |
| 3.4 | Verify Wayland startup logs (no `invalid member name`, clear backend state logs) | Completed |

## Phase 3 Detailed Execution Plan

Execution order:
1. Complete `3.1` before `3.2`.
2. Complete `3.2` before `3.3`.
3. Complete `3.3` before `3.4`.
4. Mark stages completed in-order with command outputs/log excerpts captured in this file.

### Stage 3.1 — Close Unit-Test Gaps
Objective:
- Ensure Phase 2 startup hardening is covered by deterministic unit tests for both success and failure paths.

Touch points:
- `tests/test_backends.py`
- `tests/test_phase6_smoke.py` (only if existing smoke assertions need alignment)
- `edmc_hotkeys/backends/wayland.py` (only if minimal seams are required for deterministic testing)

Tasks:
- Add or adjust Wayland tests to verify:
  - static proxy path is exercised for portal/request/session interfaces.
  - startup failure surfaces actionable reason text (`Wayland portal startup failed: ...`) and remains non-fatal.
  - activation callback handling dispatches only known binding IDs.
  - unresolved activation payloads are ignored without raising.
- Keep tests fully headless:
  - no real D-Bus session dependency.
  - use fakes/mocks for bus/proxy/signal wiring.
- Keep assertions behavior-scoped:
  - no change to capability policy ownership.
  - no change to side-specific modifier support contract.

Acceptance criteria:
- Wayland unit tests explicitly cover the startup path and activated signal parsing contract.
- Failure branches assert warning/error context, not only boolean outcomes.
- No regressions in existing backend contract tests.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"`
2. `source .venv/bin/activate && python -m pytest tests/test_phase6_smoke.py -k "backend"`

Risk and rollback:
- Risk: over-mocking may hide real integration behavior.
- Rollback: keep tests focused on deterministic contract edges and defer runtime behavior checks to Stage `3.4`.

### Stage 3.2 — Execute Targeted Wayland Validation
Objective:
- Validate Phase 2 behavior in the focused backend test slice before full-suite checks.

Touch points:
- `tests/test_backends.py`
- `tests/test_phase6_smoke.py`
- This plan file (command outcomes)

Tasks:
- Run the targeted Wayland/backend commands.
- Capture exact pass/fail counts in this plan under a Phase 3 results section.
- If failures occur:
  - classify as test bug vs implementation regression.
  - fix only behavior-scoped regressions.
  - rerun the same targeted commands until green.

Acceptance criteria:
- All targeted Wayland/backend tests pass.
- No skipped tests are introduced without explicit documented rationale.
- Result summary includes concrete command output counts.

Tests to run:
1. `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"`
2. `source .venv/bin/activate && python -m pytest tests/test_phase6_smoke.py -k "backend"`

Risk and rollback:
- Risk: targeted-only pass can mask unrelated suite regressions.
- Rollback: do not mark this stage complete until Stage `3.3` is green.

### Stage 3.3 — Run Repository-Wide Quality Gates
Objective:
- Confirm no cross-module regression from Phase 2 changes.

Touch points:
- Repository root quality/test targets
- `scripts/check_edmc_python.py`
- This plan file (command outcomes)

Tasks:
- Run repository checks in order:
  - `python scripts/check_edmc_python.py`
  - `make test`
  - `make check`
- If environment-specific constraints block a command, document the blocker and continue with remaining checks.
- Record results with concrete pass/fail status and notable warnings.

Acceptance criteria:
- `make test` passes.
- `make check` passes.
- Python baseline check passes, or mismatch is explicitly documented with reason and override status.

Tests to run:
1. `source .venv/bin/activate && python scripts/check_edmc_python.py`
2. `source .venv/bin/activate && make test`
3. `source .venv/bin/activate && make check`

Risk and rollback:
- Risk: unrelated pre-existing failures can obscure Wayland-specific status.
- Rollback: isolate failures, document unaffected Wayland evidence, and open follow-up items without broad code churn.

### Stage 3.4 — Verify Live EDMC Log Outcomes
Objective:
- Prove runtime startup no longer fails due to invalid member name parsing and that logs remain actionable.

Touch points:
- `/home/jon/edmc-logs/EDMarketConnector-debug.log`
- `docs/linux-user-setup.md` (only if troubleshooting text needs updates)
- This plan file (captured evidence)

Tasks:
- Capture a log boundary timestamp before launching EDMC/plugin.
- Start EDMC and let plugin initialize on Wayland.
- Inspect new log lines for backend startup flow:
  - backend selection line with capability context.
  - backend start success/failure line.
  - any Wayland startup failure reason.
- Verify absence of the known regression signature:
  - `invalid member name: power-saver-enabled`
- Validate operator clarity:
  - if start succeeds, logs confirm backend start.
  - if start fails, reason is actionable and no invalid-member introspection crash appears.
- Record the exact timestamped evidence lines in this plan.

Acceptance criteria:
- No new log occurrences of `invalid member name: power-saver-enabled` after Phase 2 deployment.
- Startup outcome is explicit (`started`, `failed to start`, or `unavailable`) with clear reason context.
- Evidence includes absolute timestamps from log lines.

Tests to run:
1. `rg --line-number "linux-wayland-portal|Wayland portal startup failed|invalid member name|Hotkey backend selected" /home/jon/edmc-logs/EDMarketConnector-debug.log | tail -n 120`

Risk and rollback:
- Risk: compositor/portal runtime differences produce new startup failures unrelated to invalid member names.
- Rollback: keep startup non-fatal, capture exact failure lines, and route follow-up as a separate runtime-compatibility phase.

Phase 3 done definition:
- Stages `3.1`, `3.2`, `3.3`, and `3.4` marked `Completed`.
- Phase 3 status updated to `Completed`.
- `## Phase 3 Implementation Results` section added with:
  - targeted and full test command outcomes.
  - EDMC log evidence with concrete timestamps.

## Phase 3 Implementation Results (Completed)
### Stage 3.1 Results (Completed)
- Added coverage in `tests/test_backends.py` for remaining Phase 3 startup/contract validation gaps:
  - `test_wayland_dbus_service_portal_interface_uses_static_proxy_path`
  - `test_wayland_dbus_service_session_interface_uses_static_proxy_path`
  - `test_wayland_backend_logs_start_failure`
- Existing Phase 2 activation-path coverage retained:
  - known shortcut-id dispatch
  - options fallback extraction
  - unknown binding ignore behavior

### Stage 3.2 Results (Completed)
- `source .venv/bin/activate && python -m pytest tests/test_backends.py -k "wayland"` passed (`14 passed, 16 deselected`).
- `source .venv/bin/activate && python -m pytest tests/test_phase6_smoke.py -k "backend"` passed (`1 passed, 9 deselected`).

### Stage 3.3 Results (Completed)
- `source .venv/bin/activate && python scripts/check_edmc_python.py` could not run in this repo snapshot:
  - `python: can't open file '.../scripts/check_edmc_python.py': [Errno 2] No such file or directory`
- `source .venv/bin/activate && make test` passed (`86 passed`).
- `source .venv/bin/activate && make check` passed (includes `check_no_print`, pytest `86 passed`, and compileall).

### Stage 3.4 Results (Completed)
- Evidence command run:
  - `rg --line-number "linux-wayland-portal|Wayland portal startup failed|invalid member name|Hotkey backend selected" /home/jon/edmc-logs/EDMarketConnector-debug.log | tail -n 160`
- Fresh post-Phase-2 Wayland startup evidence:
  - `2026-02-26 05:02:22.706 UTC ... Hotkey backend selected: name=linux-wayland-portal available=True supports_side_specific_modifiers=False`
  - `2026-02-26 05:02:22.711 UTC ... Wayland portal startup failed: No such interface “org.freedesktop.portal.GlobalShortcuts” on object at path /org/freedesktop/portal/desktop`
  - `2026-02-26 05:02:22.712 UTC ... Hotkey backend 'linux-wayland-portal' failed to start` (backend + plugin warnings)
- Regression verification:
  - No `invalid member name: power-saver-enabled` observed in the `2026-02-26 05:* UTC` startup window.
  - Startup outcome remains explicit and actionable; failure mode has shifted from introspection-parse crash to portal capability/interface availability.
