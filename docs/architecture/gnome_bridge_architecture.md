# GNOME Bridge Architecture Freeze (Phase 1)

Status: Frozen for Phase 1 (2026-02-26)

## Objective
Define architecture boundaries for GNOME Wayland bridge behavior so platform-specific logic stays in adapters and plugin core remains stable.

## Sender Tracks
- Current Sender Path (implemented):
  - GNOME custom keybindings managed via `gsettings`.
  - Shortcut commands invoke `scripts/gnome_bridge_send.py`.
  - Sender emits activation payloads to backend socket.
- Future Companion Artifact Path (planned):
  - GNOME extension captures shortcuts.
  - Extension forwards to helper process.
  - Helper emits authenticated payloads to plugin backend socket.

## Architecture Decision
- For future companion-artifact v1 planning, topology is:
  - extension -> helper -> plugin backend
- Direct extension -> plugin IPC is not selected for v1 planning.

Rationale:
- Keeps privileged/session-specific extension behavior separate from plugin process concerns.
- Centralizes token/replay/rate-limit logic in helper + backend boundary.
- Improves rollback and diagnosability (disable helper/extension independently).

## Component Boundaries
- Plugin Core (`load.py`, `plugin.py`):
  - Action dispatch.
  - Binding lifecycle orchestration.
  - No GNOME-specific business logic.
- GNOME Bridge Backend (`gnome_bridge.py`):
  - Socket lifecycle.
  - Activation intake and validation hooks.
  - Sender status telemetry.
- Sender Sync (`gnome_sender_sync.py`):
  - GNOME custom-keybinding reconciliation for active bindings.
  - Accelerator conversion and conflict filtering.
- Sender (`gnome_bridge_send.py` today, helper tomorrow):
  - Emits activation payloads to bridge socket.

## Responsibility Matrix
| Concern | Plugin Core | Bridge Backend | Sender Sync | Sender |
| --- | --- | --- | --- | --- |
| Action invocation | Yes | No | No | No |
| Binding persistence | Yes | No | No | No |
| Socket bind/listen | No | Yes | No | No |
| Payload parse/validate | No | Yes | No | No |
| GNOME keybinding registration | No | No | Yes | No |
| Key capture | No | No | No | Yes |
| Security auth/replay checks (target) | No | Yes | No | Sender+Backend |

## Non-Fatal Invariants
- Backend startup failure must not crash EDMC.
- Missing sender must not block plugin startup.
- Unsupported bindings must be skipped with actionable logs.
- Fallback paths (portal/x11) remain selectable independently.

## Mode Policy Freeze (Phase 1.4)
Frozen policy semantics:
- `auto`:
  - On Wayland, prefer portal backend when available.
  - Use GNOME bridge only when explicitly opted in by bridge mode flag/policy.
- `wayland_portal`:
  - Force portal backend behavior.
- `wayland_gnome_bridge`:
  - Force GNOME bridge sender path behavior.
- `x11`:
  - Force X11 backend behavior when session supports it.

Deterministic precedence (current implementation reality):
1. Platform/session detection (`wayland`/`x11`/unknown).
2. On Wayland:
  - if bridge explicitly enabled, choose bridge backend;
  - else choose portal backend.
3. On X11:
  - choose X11 backend.
4. Unknown session:
  - disabled backend with explicit reason.

## Explicit Out of Scope for Phase 1
- Security hardening implementation (token/replay/rate-limit enforcement).
- Migration of current sender path to extension/helper runtime.
- Changing default backend selection behavior in code.
