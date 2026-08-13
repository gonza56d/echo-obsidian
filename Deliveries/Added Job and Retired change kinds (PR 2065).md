---
type: delivery
status: in-review
env: both
delivered:
tags: [contact, jobs, change-kind, dashboard, notifications, warm-leads, profiles-api]
prs:
  - https://github.com/taller-projects/echo-backend/pull/2065
  - https://github.com/taller-projects/echo-backend/pull/2066
  - https://dev.azure.com/TallerInternTools/Echo%20Core/_git/profiles_api/pullrequest/10799
fe_prs: []
tickets: []
prd: https://app.notion.com/p/3bbaedca11f0814392fdc104776f3c37
---

# Added Job and Retired change kinds (PR 2065)

## What

M1 (backend, Taller dev) of the **Contact job-update signals** feature
([PRD Técnico](https://app.notion.com/p/3bbaedca11f0814392fdc104776f3c37),
private Notion): extend `ChangeKind` with **`added_job`** (contact started a
concurrent job without leaving the current one — side gig, consulting, own
startup) and **`retired`** (LinkedIn "Retired"-style position). Echo never
classifies — `profiles_api` does (its `compute_change_kind` rework is M3);
this lands the backend surface first because of the deploy-order gate.

Full investigation + feature context:
[[Contact job-update signals — Changed Jobs vs Promoted (investigation)]].
No Azure tickets yet (PRD-stage work; tickets when the PRD is shared).

## PRs

- BE M1 (dev): [#2065](https://github.com/taller-projects/echo-backend/pull/2065) — **OPEN, in review** (2026-08-13, commit `502ec0b3`)
- BE M1b (kforce twin): [#2066](https://github.com/taller-projects/echo-backend/pull/2066) — **OPEN, in review** (2026-08-13, `213ec382`; migration `n3rw8xq2kd7p` off `z8kqr3nw2p6t`; copy+adapt — kforce timestamps method has no `handle_commit_errors` decorator, tests use raw models + org-as-tenant, no AC/tenant fixtures)
- profiles_api classifier v2 (M3): [PR 10799](https://dev.azure.com/TallerInternTools/Echo%20Core/_git/profiles_api/pullrequest/10799) → dev — **OPEN, in review** (2026-08-13, branch `feat/change-kind-added-job-retired`). **DO-NOT-MERGE gate declared in the PR**: deploy after BOTH echo PRs (#2065 + #2066 — ECHO_SYNC_TARGETS pushes to both envs). Rules: retired-title word-boundary first, then oldest→NULL, same-company→promotion, open-older-neighbor→added_job, else changed_job. 12 new unit tests (55 total green locally via PYTHONPATH stubs for the 2 private packages — real feed runs in CI).
- FE (M2, both apps): not started — mapping must land before profiles_api emits (M3)

## How

- Migration `h4vq8sk2wnre` (parent `k3n8owxr2p9m`): `ALTER TYPE
  contact_job_change_kind_enum ADD VALUE IF NOT EXISTS` ×2 + nullable
  `contact.last_job_added_at` / `contact.last_retired_at`; downgrade drops
  only the columns (PG can't remove enum values — documented).
- Stamps recompute (`update_contact_job_status_timestamps`) covers all 4
  kinds via a single per-kind subquery helper.
- `hot_lead` (Warm Leads) spans the 4 stamps through a new shared
  `hot_lead_expr()` in `contact/models.py`, used by both the column_property
  and the `hot_lead` custom sort — killed the pre-existing duplication.
- Metrics: 6 new buckets ({clients, consultants, prospects} ×
  {added_jobs, retired}) on `GET /contacts/dashboard/metrics`; prospect
  buckets `include_nulls` like the existing ones.
- Notifications: `contact.job.added_job` / `contact.job.retired` subscribers →
  kinds `contact_added_job` / `contact_retired`; titles "X - Added Job" /
  "X - Retirement"; the existing 90-day/open-job gate applies.

## Decisions

- **Naming `added_job`** (not `new_job`): "New Job" read too close to
  "Changed Jobs" (Gonzalo, 2026-08-13). FE label suggestion "Added Job";
  stamp `last_job_added_at` mirrors `last_job_change_at`.
- **Deploy order is a hard gate**: this must be in prod before profiles_api's
  classifier v2 emits — the sync reconciliation DELETEs history before the
  bulk POST, so an unknown enum 422 leaves contacts jobless until retry.
- `retired` feeds `hot_lead` like every other kind (closed with Pedro in the
  PRD §8).

## Gotchas

- **AC-leak root cause of the local TestClient 404 flake** (documented in the
  investigation note §10): import-time `ENABLE_ACCESS_CONTROL=False` +
  module-teardown restore re-enables access control behind later modules →
  their requests 404 with `user_id=None`. The 3 `-k contact` local failures
  are baseline-identical on clean dev (verified by stash+rerun). New test
  module uses per-test `monkeypatch` instead. Suite-wide cleanup unticketed.
- The 6 new metrics keys will read as ADDITIVE diffs in the kforce
  golden-snapshot replay until the twin lands (waivers/ledger if a replay
  runs in between).
- `last_job_update` only carries new values once M3 ships; FE renders
  unmapped values as raw strings (no validation in `Tag`) → M2 before M3.

## Pending

- [ ] #2065 review + merge
- [ ] #2066 (kforce twin) review + merge
- [ ] FE mappings M2 (both FEs) — labels/colors/icons + tiles + notification
      labels + `types/contact.ts` union
- [ ] profiles_api PR 10799 (M3 classifier) review + merge — **deploy gated
      on #2065 + #2066 deployed** (declared in the PR description)
- [x] ~~profiles_api classifier v2 (M3) implementation~~ — shipped as PR
      10799; `retired` heuristic = word-boundary retired/retiree.
      Dev data (2026-08-13, `profile.profiles`, 1,776,213 rows): **16,247
      profiles with a 'retir%' title** — samples show the trap: "Senior
      Regional Retirement Consultant" (Fidelity) is a false positive →
      word-boundary match on retired/retiree, not 'retir%'; real patterns:
      "Retired", "(Retired)", "[RETIRED]", "Retired - former VP …", company
      sometimes "Retired"/"Self Employed"/"Formerly X". **449,739 profiles
      (~25%) hold ≥2 concurrent open jobs** → added_job will be a BIG bucket
      (volume matters for tiles/notifications/backfill).
- [ ] Backfill / re-sync wave (M4) + duplicate-notification plan
- [ ] Azure tickets once the PRD is shared with the team
- [ ] qa/main promotion after merge

## Related

- [[Contact job-update signals — Changed Jobs vs Promoted (investigation)]]
- [[Map - Contact Relationships]]
- [[Label-state dashboard contract convergence (Task 24200)]] (same metrics
  endpoint, ledger precedent for additive keys)
