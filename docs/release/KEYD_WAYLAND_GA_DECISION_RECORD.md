# keyd Wayland GA Decision Record

Status: No-Go  
Decision Date: 2026-03-07

## Decision
- `No-Go` for broad rollout/default-path promotion at this time.

## Why
- Automated quality gates passed, but manual real-environment gates are still open:
  - systemd Wayland runtime validation (`Q6`-`Q9` in manual QA matrix),
  - non-systemd fallback restart guidance validation,
  - staged cohort rollout execution (`W1` and above).

## Blocking Items
1. Complete manual scenarios `Q6`-`Q9` in [KEYD_WAYLAND_MANUAL_QA_MATRIX.md](./KEYD_WAYLAND_MANUAL_QA_MATRIX.md).
2. Execute rollout waves `W1` and `W2` in [KEYD_WAYLAND_ROLLOUT_TRACKER.md](./KEYD_WAYLAND_ROLLOUT_TRACKER.md).
3. Reassess go/no-go after triaging any S1/S2 findings.

## Rollback Triggers
- Any `S1` issue involving incorrect binding dispatch, backend mis-selection, or startup failure.
- Repeated `S2` issues without an accepted mitigation plan.

## Contingency Owner
- EDMCHotkeys maintainer.
