# Prompt: Implement Wayland Backend (EDMC-Hotkeys)

Use this prompt in a new Codex session.
Terminology: `PROMPT_IMPLEMENT_WAYLAND_BACKEND.md` is referred to as the **"wayland plan"**.

---

Implement the Linux Wayland backend for `EDMC-Hotkeys`.

Follow all repository rules in `AGENTS.md` first.  
This project is a single EDMC plugin (`EDMC-Hotkeys`) with `load.py` in plugin root.

## Current project context (must preserve)
- Bindings are stored in plugin-local `bindings.json` using v3 schema:
  - `plugin`, `modifiers`, `key`, `action_id`, optional `payload`, `enabled`.
- Canonical modifiers are side-specific tokens:
  - `ctrl_l`, `ctrl_r`, `alt_l`, `alt_r`, `shift_l`, `shift_r`, `win_l`, `win_r`.
- Pretty hotkey display/API format is now:
  - `LCtrl`, `RCtrl`, `LAlt`, `RAlt`, `LShift`, `RShift`, `LWin`, `RWin`.
- X11 side-specific behavior was fixed using key-state polling + edge detection (order-insensitive).
  - Do not regress X11 behavior.
- Settings save behavior was fixed so validation errors keep Settings open.
  - Do not regress this.
- Current Wayland backend is a wrapper with a null portal client and no real GlobalShortcuts implementation.

## Decisions From Review (2026-02-25)
- Backend approach: implement **XDG GlobalShortcuts**.
- Runtime dependency policy: avoid new runtime dependencies if possible.
  - If adding one is unavoidable and may affect EDMC compliance/best-practice posture, stop and get user approval first.
- Rollout: Wayland backend should be **enabled by default** when available.
- Documentation rule: implementation results for this effort are recorded in this wayland plan.

## Clarifications
- "Unsupported systems" means any runtime where this backend cannot function safely/reliably, including:
  - not in a Wayland session,
  - `xdg-desktop-portal` unavailable or not running,
  - portal backend missing GlobalShortcuts support,
  - permission denied or portal call failures that prevent registration.
- Why side-specific modifiers are currently not implementable on standard Wayland:
  - XDG GlobalShortcuts exposes logical modifiers (`Ctrl/Alt/Shift/Super`), not left/right variants.
  - Compositors do not expose raw global key events to regular clients by design.
  - Left/right support would require compositor-specific/private APIs or privileged input paths, which are non-portable and likely non-compliant with project constraints.
- Registration timing note:
  - registering shortcuts can trigger desktop permission flows; implementation must define whether this happens at startup or only after explicit user action.
- Compositor target note:
  - GNOME/KDE portal implementations differ in behavior; target scope affects compatibility testing and fallback logic.

## Goal
Add a concrete Wayland GlobalShortcuts backend path under `edmc_hotkeys/backends/wayland.py` (and related modules as needed), so non-side-specific bindings can actually register and fire on Wayland sessions.

## Constraints
- Use EDMC logging patterns already used in this repo.
- Keep UI work on main thread only; backend listener work must be background-safe.
- Keep existing public API behavior stable (`register_action`, `list_bindings(plugin_name)`, callback `hotkey` kwarg behavior).
- Keep side-specific behavior explicit:
  - If Wayland API cannot represent left/right modifiers, keep `supports_side_specific_modifiers=False`.
  - Continue auto-disabling side-specific bindings on Wayland with clear diagnostics.
- Avoid unnecessary new dependencies. If a dependency is required:
  - make it optional and availability-gated,
  - update bundling docs/scripts.
- Do not introduce migration logic for old binding formats.

## Deliverables
1. Concrete Wayland portal client implementation with availability detection and actionable failure reasons.
2. Registration/unregistration/invocation flow for non-side-specific bindings.
3. Capability reporting integrated with current backend capability matrix.
4. Tests for:
   - availability paths,
   - successful register/unregister and callback dispatch,
   - unsupported side-specific handling.
5. Documentation updates:
   - `docs/linux-user-setup.md`
   - `docs/packaged-edmc-dependency-bundling.md` (if dependencies change)
   - `docs/plans/IMPLEMENTATION_PLAN.md` implementation results.

## Expected behavior
- On Wayland with portal support available:
  - backend starts,
  - compatible bindings register,
  - callbacks fire.
- On Wayland without portal support:
  - backend is unavailable with clear reason in logs,
  - plugin remains stable.
- Side-specific bindings remain explicitly unsupported on Wayland unless you can prove full side-specific support.

## Verification commands
- `source .venv/bin/activate && python -m pytest`
- `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`
- Add targeted backend tests for Wayland behavior.

## Output format
- Implement code changes directly.
- Summarize:
  - what changed,
  - why it is correct,
  - test results,
  - any remaining risks/gaps.

---

If anything is unclear, ask targeted clarifying questions before coding.
