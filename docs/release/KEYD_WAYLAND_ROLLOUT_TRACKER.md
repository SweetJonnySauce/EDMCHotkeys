# keyd Wayland Rollout Tracker

Status: Initialized for Phase 5 Stage 5.2  
Last Updated: 2026-03-07

## Rollout Waves
| Wave | Cohort | Entry Criteria | Exit Criteria | Current State | Notes |
| --- | --- | --- | --- | --- | --- |
| W0 | Local automation gate | `pytest` + `make check` passing | No release-blocking automated regressions | Completed | Completed on 2026-03-07. |
| W1 | Small manual cohort | Stage 5.1 manual QA scenarios complete on at least one systemd host | No open S1/S2 issues after triage | Pending | Blocked by real EDMC Wayland runtime execution. |
| W2 | Broader manual cohort | W1 complete; non-systemd fallback validated | No open S1 issues; S2 have mitigations/owners | Pending | Includes fallback restart guidance validation. |
| W3 | Default path consideration | W2 complete with acceptable support burden | Recorded go/no-go decision | Pending | Governed by decision record. |

## Incident Triage Log
| Issue ID | Date | Wave | Severity | Summary | Root Cause | Owner | Status | Rollback Required |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| None | 2026-03-07 | W0 | N/A | No incidents observed in local automated gate | N/A | N/A | Closed | No |

Severity guide:
- `S1`: Release blocker or correctness/safety failure.
- `S2`: High-impact regression with workaround.
- `S3`: Low-impact issue that does not block rollout safety.
