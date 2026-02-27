# GNOME Wayland Bridge Issue Triage Template

Status: Phase 5 rollout triage template
Owner: EDMC-Hotkeys
Last Updated: 2026-02-27

## Severity Model
- `S0`: data loss/security exposure
- `S1`: startup safety or core dispatch broken for supported environment
- `S2`: degraded behavior with viable workaround
- `S3`: cosmetic/docs/low-impact ergonomics

## Classification Buckets
- Startup/Fatality Regression
- Dispatch Correctness Regression
- Sender Sync/Runtime Compatibility
- Installation/Packaging/Docs UX

## Required Incident Fields
- Incident ID:
- Date (UTC):
- Reporter:
- Environment:
  - Ubuntu version
  - GNOME Shell version
  - Session type
- Bridge mode/config:
- Reproduction steps:
- Expected behavior:
- Actual behavior:
- Log evidence (timestamped lines):
- Severity (`S0`..`S3`):
- Bucket:
- Workaround available (Y/N):
- Rollback required (Y/N):
- Owner:
- Status (`Open`, `In Progress`, `Resolved`, `Deferred`):
- Fix/decision notes:

## Resolution Gate
- `S0`/`S1` must be resolved before GA.
- `S2` may be deferred only with documented workaround and support note.
- `S3` may be deferred if no rollout safety/correctness impact exists.
