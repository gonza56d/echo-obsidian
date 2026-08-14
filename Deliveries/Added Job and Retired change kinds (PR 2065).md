---
type: delivery
status: merged
env: both
delivered: 2026-08-14
tags: [contact, jobs, change-kind, dashboard, notifications, warm-leads, profiles-api]
prs:
  - https://github.com/taller-projects/echo-backend/pull/2065
  - https://github.com/taller-projects/echo-backend/pull/2066
  - https://dev.azure.com/TallerInternTools/Echo%20Core/_git/profiles_api/pullrequest/10799
fe_prs: []
tickets:
  - https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24308
  - https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24309
  - https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24310
  - https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24311
  - https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24312
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
Azure (full milestone set under Feature [24308](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24308), one US per milestone à la Feature 24051): M1 [24310](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24310) (backend, **Developed** — PRs merged, inert until M3) · M2 [24309](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24309) (FE, unassigned for the FE TL) · M3 [24311](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24311) (profiles_api classifier, Active, PR 10799) · M4 [24312](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24312) (backfill wave, New). PR bodies back-linked to their US (2065/2066 → 24310; 10799 → 24311).

## PRs

- BE M1 (dev): [#2065](https://github.com/taller-projects/echo-backend/pull/2065) — **MERGED to dev 2026-08-14** (squash `8d96aa6c`; Leo approved, nits fixed `dcc30f67`, CI green 11m)
- BE M1b (kforce twin): [#2066](https://github.com/taller-projects/echo-backend/pull/2066) — **MERGED to kforce-dev 2026-08-14** (squash `8a741dae`; Leo approved, nits fixed `c89e343f`, CI green) (originally `213ec382`; migration `n3rw8xq2kd7p` off `z8kqr3nw2p6t`; copy+adapt — kforce timestamps method has no `handle_commit_errors` decorator, tests use raw models + org-as-tenant, no AC/tenant fixtures)
- profiles_api classifier v2 (M3): [PR 10799](https://dev.azure.com/TallerInternTools/Echo%20Core/_git/profiles_api/pullrequest/10799) → dev — **OPEN, in review** (2026-08-13, branch `feat/change-kind-added-job-retired`). **DO-NOT-MERGE gate declared in the PR**: deploy after BOTH echo PRs (#2065 + #2066 — ECHO_SYNC_TARGETS pushes to both envs). Rules: retired-title word-boundary first, then oldest→NULL, same-company→promotion, open-older-neighbor→added_job, else changed_job. **r1 nits addressed by Gonzalo directly (`04af83f`, 2026-08-14)**: +2 rule-ordering tests (3-concurrent-opens chain → all added_job with single NULL anchor; retired-title outranks same-company promotion) + docstring scope notes (emeritus/demotions deferred pending calibration; historical retirements keep `retired` on old rows — badge unaffected, only stamps carry the rare stale signal). 14 new unit tests (57 total green locally via PYTHONPATH stubs for the 2 private packages — real feed runs in CI).
  - **Review 2026-08-14 (self-review)**: traced the classifier by hand + ran the suite + 6 edge probes against the real fn; **enum-string contract verified against echo-backend** (`ChangeKind.ADDED_JOB="added_job"` / `RETIRED="retired"` in `job/schemas.py:19,21` — exact match, so no 422). No blockers. Addressed 3 nits in follow-up commit `04af83f` (no behavior change, **57 tests** now): (1) added a 3+ concurrent-open chain test + a retirement-outranks-same-company-promotion test (lock rule ordering); (2) documented retirement scope = retired/retiree only, **emeritus + demotions deferred** pending their own dev-data calibration (PRD §8.5.1); (3) documented that rule 1 matches title over *all* history, so a historical retirement someone returned from keeps `retired` on the old row (badge unaffected; only `last_retired_at`/`hot_lead` carry the rare stale signal).
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

## Review round 1 (Leo, both APPROVED READY WITH NITS — fixed 2026-08-14)

Fixed on both twins (`dcc30f67` dev / `c89e343f` kforce): the migration
test's ADD VALUE assertion was **vacuous** under the create_all schema →
now `RENAME VALUE`s both labels away before `upgrade()` (residue
`*_pre_migration` labels stay, unused); negative 90-day/open-job gate
cases (stale added_job + ended retired emit nothing); a
`@subscribe`-binding test against `app.core.events._subscription_registry`
(typo in the event-name string would silently drop events); return
annotation on `latest_start_date()`; dev also got `_set_tenant` teardown.
Skipped with reason: polyfactory in the kforce module (mirrors suite
convention + dev twin). Questions answered on the PRs: `current_job`
resolves to the newly added position for added_job notifications;
"is now Retired" copy flagged as PM call.

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

- [x] #2065 merged to dev 2026-08-14 (`8d96aa6c`)
- [x] #2066 merged to kforce-dev 2026-08-14 (`8a741dae`)
- [x] Both dev deploys verified 2026-08-14: enum live (Taller dev head `h4vq8sk2wnre`, kforce-dev head `n3rw8xq2kd7p`) → 10799's only remaining gate is M2
- [ ] Promote PRs [#2067](https://github.com/taller-projects/echo-backend/pull/2067) → qa + [#2068](https://github.com/taller-projects/echo-backend/pull/2068) → main **OPEN 2026-08-14** (clean cherries of `8d96aa6c`; parent `k3n8owxr2p9m` already on both via #2059/#2060; MERGE COMMIT, qa first)
- [ ] kforce-master promotion of #2066 — not requested yet
- [ ] FE mappings M2 (both FEs) — **US [24309](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24309)** (handed to FE TL; labels/colors/icons + tiles + notification labels + `types/contact.ts` union)
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
- [ ] Backfill / re-sync wave (M4) — **plan scoped 2026-08-14** (US 24312 comment): 69,739 linked profiles / 248,075 mappings (dev); recommend a jobs-only enqueue variant (full `enqueue_for_profile` doubles echo calls with contact+DM legs); duplicate-notification exposure in dev is tiny (188 contacts / ~189 notifications) → likely accept the one-off, re-size on prod first; validation = change_kind distribution pre/post + zero dead-letters. Script pending (after M2+M3 deploy)
- [x] ~~Azure tickets~~ full set created 2026-08-14: Feature 24308 + US 24310 (M1) / 24309 (M2) / 24311 (M3) / 24312 (M4); PRs back-linked
- [ ] PR 10799 needs a reviewer (no vote yet as of 2026-08-14)

## Related

- [[Contact job-update signals — Changed Jobs vs Promoted (investigation)]]
- [[Map - Contact Relationships]]
- [[Label-state dashboard contract convergence (Task 24200)]] (same metrics
  endpoint, ledger precedent for additive keys)
