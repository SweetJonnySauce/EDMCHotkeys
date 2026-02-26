# EDMC-Hotkeys Release Notes

## 2026-02-26 - Wayland Tier 1 Generic Modifier Support

Summary:
- Tier 1 backends now support non-side-specific modifiers (`Ctrl`, `Alt`, `Shift`, `Win`) for hotkey bindings.
- Side-specific modifiers (`LCtrl`, `RCtrl`, etc.) remain Tier 2-only and are auto-disabled on Tier 1 backends.

Behavior changes:
- Valid on Tier 1:
  - `Ctrl+M`
  - `Ctrl+Shift+F1`
  - `Alt+F5`
- Invalid:
  - mixed same-family tokens such as `Ctrl+LCtrl+M` or `Shift+RShift+F2`

Migration guidance:
- If a Wayland user has side-specific bindings, replace them with generic equivalents:
  - `LCtrl+LShift+F1` -> `Ctrl+Shift+F1`
  - `RCtrl+M` -> `Ctrl+M`

Diagnostics:
- Auto-disable logs should reference only side-specific bindings on Tier 1 backends.
- Generic bindings should no longer be auto-disabled by side-specific capability checks.
