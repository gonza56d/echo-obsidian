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
  - https://dev.azure.com/TallerInternTools/Echo%20Core/_git/profiles_api/pullrequest/10818
  - https://github.com/taller-projects/echo-backend/pull/2114
  - https://github.com/taller-projects/echo-backend/pull/2115
  - https://github.com/taller-projects/echo-backend/pull/2116
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

## ⏪ Where things stand — snapshot 2026-08-20 EOD (prod promotion in flight), read this first when back

**Promotion status:**

- **Dev canary VALIDATED end-to-end** (2026-08-20 ~13:37 UTC): 100 profiles /
  101 legs enqueued, ~95+ delivered, ZERO errors; echo dev gained its first
  **14 `added_job` rows** (no `retired` in 100 — expected, ~0.9% base rate).
  321 contact_job rows rewritten. Canary cursor: `00883583-35fc-4e6c-99b5-cb2f0b194a30`.
- **Full Taller-dev wave RUNNING in background** since ~13:45 UTC
  (`--environment development --start-after <canary cursor>`; log:
  scratchpad `wave-dev.log`). Real enqueue rate ~2.5 profiles/s (RTT-bound,
  NOT the dry-run's 83/s) → ~5.5h for 49,588 profiles. Resume-safe via
  cursor in log. kforce-development wave (23,243 profiles, ~2.5h) queued
  after dev validates.
- **Release PR 10889 MERGED → master 2026-08-20 (`a2b3192`) and PROD
  DEPLOY PIPELINE GREEN**: build 27034 (definition `profiles-api` =
  azure-pipelines-api.yaml, the ONLY registered pipeline for this repo —
  azure-pipelines.yaml is orphaned/legacy) ran tests, image build+push,
  prod DB migrations (no-op for this release) and DeployArgoCD; pushed
  `update tag: 27034_master` to taller-ttit-kubernetes
  `applications/profiles-api/values-prod.yaml` at 15:08:37 UTC (`7de1b68a`,
  = infra HEAD). Argo auto-syncs from HEAD → pods roll within its poll
  interval. Note: pre-merge PR build 27030 FAILED at 13:39 but the
  post-merge master build succeeded — failure cause unexamined.
- **Prod enum Taller: VERIFIED** (`contact_job_change_kind_enum` has
  added_job + retired). **kforce-prod enum: UNVERIFIED — no local creds**
  (no pg_service entry; manual check pending).
- **Prod notification sizing DONE (Taller)**: up to **2,876 duplicate
  notifications across 42 recipients (~68 each worst case)** — vs 189 in dev.
  Order of magnitude bigger → RECOMMEND the temporary
  `CONTACT_JOB_NOTIFICATIONS_ENABLED` flag (ROLE_NOTIFICATIONS_ENABLED
  precedent) in echo-backend before the PROD wave. Note: the flag gates the
  WAVE only — merging 10889 (classifier live organically) is safe without it,
  organic re-scrapes trickle normal notifications.
- **Flag SHIPPED 2026-08-20: [echo-backend PR #2114](https://github.com/taller-projects/echo-backend/pull/2114)
  → dev OPEN** (branch `24312/contact_job_notifications_flag`, commit `fbc87500`).
  `CONTACT_JOB_NOTIFICATIONS_ENABLED` (default true, inert) next to
  ROLE_NOTIFICATIONS_ENABLED in config; guard at the TOP of
  `_create_contact_job_notifications` (notification/service.py) — one guard
  covers the 4 `contact.job.*` subscribers, publisher untouched (mirrors the
  role-flag placement: gate the subscriber, not the event). Test:
  TestContactJobNotificationsDisabled (2 passed locally w/ Docker).
  PR link commented on US 24312. **Kforce twin NOT created** — needed before
  the KFORCE prod wave (same duplicate risk); Taller-only for now per scope.
  Ops: promotion PRs OPEN 2026-08-20: [#2115](https://github.com/taller-projects/echo-backend/pull/2115)
  → qa + [#2116](https://github.com/taller-projects/echo-backend/pull/2116) → main
  (clean cherries of `fbc87500`; tests re-run green on BOTH branches;
  MERGE-COMMIT not squash per release convention; merge order: #2114 dev
  first). Flip false in prod Vault only during the wave, restore after
  (blackout mutes genuine job-change notifications while off). Both PRs
  commented on US 24312. **Review nits addressed 2026-08-20 (`d104e2b4` on
  #2114, cherried to #2115 `59d779af` / #2116 `2f0c52a5`)**: disabled-flag
  test rewritten — direct synchronous calls to the 4 subscriber handlers
  (contact_promoted/job_changed/job_added/retired) with hand-built
  ContactJobUpdateEvent, covering ALL 4 kinds and dropping the flaky
  time.sleep(0.5); docstring now matches what's verified. Tests green on
  all 3 branches.

**KFORCE DESCOPED (Gonzalo, 2026-08-20): no kforce wave, no kforce flag
twin, no kforce-prod enum check.** Only the Taller prod wave matters.
Caveat noted: the shared profiles_api prod deployment still classifies
kforce-prod mappings ORGANICALLY (if the prod contact_mappings table has
kforce env rows) — safe because M1 merged to kforce-master via #2070, but
nobody is running a kforce backfill.

**FLAG FLIPPED FALSE in BOTH dev and prod (Gonzalo, 2026-08-20 ~17:00 UTC)**
— prod wave gate #2 CLEARED. Verified consistent in dev: zero contact-kind
notifications during today's wave (12.3k legs delivered); note the last
organic contact notification in dev was 06-18, so dev couldn't show a
before/after edge — no spam either way. REMEMBER: restore the flag to true
in BOTH envs after the waves (while false, genuine job-change notifications
are muted). Kinds stored as `contact_changed_job`/`contact_promotion`
(lowercase) in the notification table.

**PROD profiles DB pre-checks DONE (2026-08-20, host
`postgresql-echo-scrapers-prod-001.postgres.database.azure.com`; creds from
Vault, used inline only — NEVER stored):** wave env value is **`production`**
(52,888 profiles / 53,332 legs — same scale as Taller dev, expect ~5.5h
enqueue + overnight drain); `kforce-production` exists too (126,810 profiles,
DESCOPED — confirms organic kforce flow). Outbox dead-letter baseline: **473
dead** / 4,709,378 success — validation target is dead stays at 473.

**Echo PROD pre-wave baseline (2026-08-20 ~16:15 UTC, before any wave):**
changed_job 267,949 / promotion 150,832 / NULL 54,395 / added_job 0 /
retired 0 — total 473,176 rows.

## Previous snapshot — 2026-08-20 midday

**TL;DR: ALL code is merged — backend on all 5 branches, and BOTH profiles_api
PRs merged to dev 2026-08-20 (10799 `818af23d` 12:51 UTC, 10818 `4cda3bea`
12:54 UTC). What's left is operational: (1) confirm profiles_api dev deploy
actually rolled (as of 2026-08-20 ~13:00 UTC Taller dev has ZERO
added_job/retired rows — baseline: changed_job 195,019 / promotion 115,007 /
NULL 39,468), (2) run the M4 wave in dev per the US 24312 runbook, validate
distribution pre/post + zero dead-letters, then (3) prod: enum verify,
re-size notification exposure, deploy profiles_api prod, run prod wave.
The US 24309 question is RESOLVED (2026-08-20): FE mappings ARE merged and
deployed everywhere — `added_job` present on both echo-frontend branches
(constants/contacts.ts, types/contact.ts, notificationHelpers.ts, verified
by grep on origin/dev + origin/kforce-dev); the ticket was Removed because
the work shipped under another ticket, not descoped. No FE gate remains.
Ticket hygiene: 24311 still Active, 24312 still New, Feature 24308 still
New — advance them.**

Milestone map (Feature [24308](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24308)):

| M | Ticket | State | What's left |
|---|---|---|---|
| M1 backend | US [24310](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24310) (Developed) | ✅ merged on ALL 5 branches 2026-08-14 (#2065 dev, #2066 kforce-dev, #2067 qa, #2068 main, #2070 kforce-master); enum verified live in BOTH dev DBs | Verify PROD DBs post-deploy (echo-prod + kforce-prod: 4 enum labels + heads `h4vq8sk2wnre`/`n3rw8xq2kd7p`). Note: #2070 also carried the gated #2051 org_people DROP — whoever merged owned those preconditions; sanity-check kforce prod |
| M2 FE | US [24309](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24309) (Removed — work shipped under another ticket) | ✅ FE merged + deployed everywhere (confirmed 2026-08-20: `added_job` on origin/dev + origin/kforce-dev — constants, types, notification helpers) | Nothing |
| M3 classifier | US [24311](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24311) (Active — advance it) | ✅ [PR 10799](https://dev.azure.com/TallerInternTools/Echo%20Core/_git/profiles_api/pullrequest/10799) **MERGED → dev 2026-08-20** (`818af23d`, Pedro approved) | Confirm dev deploy rolled (no organic added_job/retired rows yet as of merge day); then prod deploy |
| M4 backfill | US [24312](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24312) (New — advance it) | ✅ [PR 10818](https://dev.azure.com/TallerInternTools/Echo%20Core/_git/profiles_api/pullrequest/10818) **MERGED → dev 2026-08-20** (`4cda3bea`) | **RUN the wave**: dev first (dry-run → real, `--environment development` / `kforce-development`), validate pre/post distribution + zero dead-letters; prod after prod sizing + deploy |

**Corrected sizing** (earlier notes overstated): the wave is **73,241 linked
mapping legs / 69,739 profiles** (248,075 was ALL contact_mappings incl.
never-linked `profile_id IS NULL` rows). Env values in `contact_mappings` are
`development` / `kforce-development` (+ stray QA/taller/taller3 rows that
warn+skip) — NOT "dev". Duplicate-notification exposure: 188 contacts in dev
(tiny → likely accept one-off; re-size on prod pre-wave).

Next-week checklist, in order of value:

1. Get votes on 10799 + 10818 (nothing merges itself); confirm US 24309
   reached the FE TL.
2. Verify prod enums (one psql each; prod reads got classifier-blocked once —
   may need to run by hand).
3. Run the M4 sizing queries on prod (notification exposure + wave size) so
   the suppression decision is made with prod numbers.
4. Fix `echo-flows-docs/03-contacts.md`: wrong "Hot Lead Score" description +
   document the two new kinds and Update-filter values.
5. Share the PRD with the team + close answered open questions (backfill
   "cómo" settled by 10818; drift settled by tests; Warm-Leads ranking for new
   kinds still genuinely open).
6. File the AC-leak suite cleanup ticket (import-time `ENABLE_ACCESS_CONTROL`
   + module-teardown restore = the local TestClient-404 flake factory).
7. PAT: needs **Packaging read** (uv sync for profiles_api) and **Build**
   scope (CI status via API). Until then, local profiles_api tests need the
   PYTHONPATH stub trick (stub `position_classifier` + a functional `outbox`
   package — the session scratchpad copy is gone; recipe: import-satisfying
   classes, `OutboxEvent`/`OutboxDelivery` as kwargs→attrs records with
   auto `id`).
8. Parked (post-feature cleanup batch, unticketed): badge date ≠ event date,
   dashboard vs warm-leads mismatch, three FE label vocabularies, "is now
   Retired" copy (PM call).

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
  - **Pedro review 2026-08-14 (`745f6b1`)**: no blockers, ship-with-nits. 3 nits addressed — `_is_retirement` now `str()`-coerces role before `re.search` (defensive vs a non-str role from raw-dict callers; `build_job_intents` already normalizes, so prod paths unaffected) + 3 tests: a non-latest historical retirement still classifies `retired` (locks the documented "rule 1 spans the whole chain"), `role=None` (no crash / no match), and non-str role coercion. **60 unit tests total green.** Pedro reiterated the merge-gate ("do not clear yourself"): both echo dev deploys must have applied the enum migrations (`h4vq8sk2wnre` / `n3rw8xq2kd7p` — verified done) **and M2 FE (US 24309) merged**, else the new values render as raw strings.
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
- [x] Promotions ALL MERGED 2026-08-14 ~16:30 UTC: [#2067](https://github.com/taller-projects/echo-backend/pull/2067) → qa, [#2068](https://github.com/taller-projects/echo-backend/pull/2068) → main, [#2070](https://github.com/taller-projects/echo-backend/pull/2070) → kforce-master (incl. gated #2051 DROP + #2057) — **M1 is on every branch**
- [x] FE mappings M2 — DONE and deployed everywhere (confirmed 2026-08-20 by
      grep: `added_job` on echo-frontend origin/dev + origin/kforce-dev in
      `constants/contacts.ts`, `types/contact.ts`, `notificationHelpers.ts` +
      dashboard/filter tests). US [24309](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24309)
      was Removed because the work shipped under another ticket — NOT descoped
- [x] profiles_api PR 10799 (M3 classifier) **MERGED → dev 2026-08-20 12:51 UTC** (`818af23d`, Pedro approved). The M2 gate dissolved with 24309's removal
- [ ] Confirm profiles_api dev deploy rolled: as of 2026-08-20 ~13:00 UTC
      Taller dev `contact_job` has ZERO added_job/retired (baseline for
      pre/post validation: changed_job 195,019 / promotion 115,007 /
      NULL 39,468)
- [ ] Run the M4 wave in dev (dry-run → real; `--environment development`,
      then `kforce-development`), validate distribution shift + zero
      dead-letters
- [ ] Prod path: verify prod enums (still unchecked), run prod sizing queries
      (notification exposure → suppression decision), profiles_api prod
      deploy, prod wave
- [ ] Advance tickets: US 24311 (Active) + US 24312 (New) + Feature 24308 (New)
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
- [ ] Backfill / re-sync wave (M4) — **plan scoped 2026-08-14** (US 24312 comment): dev sizing **corrected by review**: 69,739 linked profiles / **73,241 linked mapping rows = actual jobs legs** (the earlier "248,075 mappings" figure = ALL `contact_mappings` incl. `profile_id IS NULL` never-linked rows — wave is ~3.4× smaller than first stated); recommend a jobs-only enqueue variant (full `enqueue_for_profile` doubles echo calls with contact+DM legs); duplicate-notification exposure in dev is tiny (188 contacts / ~189 notifications) → likely accept the one-off, re-size on prod first; validation = change_kind distribution pre/post + zero dead-letters. **Script SHIPPED as [profiles_api PR 10818](https://dev.azure.com/TallerInternTools/Echo%20Core/_git/profiles_api/pullrequest/10818) → dev, OPEN 2026-08-14** (`25053dc`): `enqueue_jobs_resync` producer method (jobs-only legs, lean snapshot, ~half the echo calls) + `scripts/backfill_resync_job_histories.py` (keyset pagination, --dry-run/--limit/--start-after/--environment; dry-run verified vs dev data). Merge-safe anytime; RUN gated on M3 deploy. **Self-review 2026-08-14 (fresh-eyes, fixes pushed `ac226ed` + PR description corrected)**: verified lean snapshot vs deliverer jobs-leg reads (signature computed inside `sync_jobs_for_mapping`, NOT over the snapshot → fast-path intact), mapping selection matches organic (`find_matching_mappings` ignores `is_tracked`; NULL `profile_id` never synced), constructor wiring, stray-env legs degrade to warn+skip no-ops. **Gotchas found**: `contact_mappings.environment` values are `development` / `kforce-development` (+strays `QA`/`taller`/`taller3`) — the docstring example said `--environment dev` which matches ZERO rows (fixed: real values in docs/help + zero-match warning); resume cursor now = last profile actually enqueued (pre-commit UUID; safe with `--limit` mid-batch); empty-batch guard. **Verification gap**: unit tests not re-runnable locally — PAT lacks Packaging read scope for the `taller-python` feed (and Build scope, so CI not visible via API); ruff + py_compile clean
- [x] ~~Azure tickets~~ full set created 2026-08-14: Feature 24308 + US 24310 (M1) / 24309 (M2) / 24311 (M3) / 24312 (M4); PRs back-linked
- [x] ~~PR 10799 needs a reviewer~~ Pedro approved; merged 2026-08-20. PR
      10818 also merged 2026-08-20 12:54 UTC (`4cda3bea`)

## Related

- [[Contact job-update signals — Changed Jobs vs Promoted (investigation)]]
- [[Map - Contact Relationships]]
- [[Label-state dashboard contract convergence (Task 24200)]] (same metrics
  endpoint, ledger precedent for additive keys)
