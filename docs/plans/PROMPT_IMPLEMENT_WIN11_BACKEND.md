# Prompt: Implement Windows 11 Backend (EDMC-Hotkeys)

Use this prompt in a new Codex session.

---

Implement and harden the Windows 11 backend for `EDMC-Hotkeys`.

Follow all repository rules in `AGENTS.md` first.  
This project is a single EDMC plugin (`EDMC-Hotkeys`) with `load.py` in plugin root.

## Current project context (must preserve)
- Binding storage is v3 in plugin-local `bindings.json`:
  - `plugin`, `modifiers`, `key`, `action_id`, optional `payload`, `enabled`.
- Canonical modifier tokens are side-specific:
  - `ctrl_l`, `ctrl_r`, `alt_l`, `alt_r`, `shift_l`, `shift_r`, `win_l`, `win_r`.
- Pretty format exposed in UI/API is:
  - `LCtrl`, `RCtrl`, `LAlt`, `RAlt`, `LShift`, `RShift`, `LWin`, `RWin`.
- Windows backend currently uses:
  - `RegisterHotKey` for non-side-specific paths,
  - optional low-level hook fallback for side-specific paths,
  - feature flag: `EDMC_HOTKEYS_ENABLE_WINDOWS_LOW_LEVEL_HOOK`.
- X11 side-specific order issues were fixed with polling + edge detection.
  - Preserve behavior on other backends; no regressions.
- Settings validation flow was fixed so errors do not close Settings.
  - Do not regress this.

## Goal
Make Win11 backend robust and production-ready for both:
1. non-side-specific hotkeys (RegisterHotKey path),
2. side-specific hotkeys (low-level hook path).

## Constraints
- Maintain compatibility with current backend capability model (`supports_side_specific_modifiers`).
- Keep EDMC/Tk thread-safety rules (backend threads dispatch via current plugin pipeline).
- Keep existing module-level API behavior stable.
- No destructive architecture changes; extend current backend cleanly.
- Keep logging informative but not noisy.

## Functional requirements
1. Side-specific correctness
   - `LCtrl` vs `RCtrl`, `LShift` vs `RShift`, `LAlt` vs `RAlt`, `LWin` vs `RWin` must be honored.
   - Modifier press order must not matter.
2. Edge-trigger behavior
   - Holding keys should not spam callbacks unintentionally.
   - Trigger on press transition; require release before retrigger.
3. Conflict-free routing
   - Non-side-specific bindings should remain on `RegisterHotKey`.
   - Side-specific bindings should use low-level path when available.
4. Availability handling
   - Clear diagnostics when low-level hook path is disabled/unavailable.
   - Capability flag reflects actual runtime support.
5. Lifecycle safety
   - Clean startup/shutdown for message loop and hook thread.
   - No leaked registrations/hooks after stop.

## Deliverables
1. Windows backend code updates in `edmc_hotkeys/backends/windows.py` (and related files if needed).
2. Tests for:
   - side-specific matching (left/right + order),
   - edge-trigger behavior,
   - capability/feature-flag handling,
   - start/stop lifecycle correctness.
3. Docs updates:
   - `docs/plans/IMPLEMENTATION_PLAN.md` implementation results.
   - any user/dev docs impacted by Win11 behavior and feature flag usage.

## Verification commands
- `source .venv/bin/activate && python -m pytest`
- `source .venv/bin/activate && python -m compileall load.py edmc_hotkeys tests`
- add targeted Windows backend tests and run them explicitly.

## Output format
- Implement code changes directly.
- Summarize:
  - what changed,
  - why it is correct for Win11,
  - test results,
  - remaining risks/gaps.

---

If there are ambiguous platform tradeoffs (e.g., feature-flag default behavior), ask focused clarifying questions before coding.

