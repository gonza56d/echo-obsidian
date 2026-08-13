---
type: investigation
status: done
env: both
delivered: 2026-08-13
tags: [investigation, contact, jobs, dashboard, notifications, warm-leads]
prs: []
fe_prs: []
tickets: []
prd: https://app.notion.com/p/3bbaedca11f0814392fdc104776f3c37
---

# Contact job-update signals — Changed Jobs vs Promoted (investigation)

Investigation (2026-08-13, no ticket) into how the **Update** column of the
Contacts dashboard ("Latest Updates") gets its **Changed Jobs / Promoted**
values, what rules drive them, and where else they surface. Verified against
`dev` and spot-checked against `origin/kforce-dev`. Draft PRD (private):
[Contact job-update signals — PRD Técnico (Draft)](https://app.notion.com/p/3bbaedca11f0814392fdc104776f3c37).

## TL;DR

- The badge value = `contact_job.change_kind` (`promotion` | `changed_job`,
  nullable ENUM) **of the contact's latest job**. Echo never computes the
  classification — it arrives pre-classified from the data-team LinkedIn
  tracking pipeline through the job CRUD endpoints.
- The date next to the badge is **not** the event date: it's
  `current_job.start_date` (latest *open* job), formatted `MM/dd/yy`.
- "Warm Leads" = the `hot_lead` boolean sort: *has a job signal* AND *hasn't
  been talked to since (or in 6 months)*.
- Kforce has the identical mechanism (pre-fork feature, migration
  `492db619e39d` 2025-03-05 "add_contact_kforce_fields").

## 1. Data model

- `contact_job` (`app/modules/contact/job/models.py`): `role`, `description`,
  `start_date`, `end_date`, `company_id`, `change_kind` ENUM
  `contact_job_change_kind_enum` — nullable, indexed. RLS policy keyed on
  `contacts.view`; composite FK `(contact_id, tenant_id)`.
- `ChangeKind` enum: `app/modules/contact/job/schemas.py:14-16` —
  `PROMOTION = "promotion"`, `CHANGED_JOB = "changed_job"`.
- Persisted stamps on `contact`: `last_promoted_at`, `last_job_change_at`
  (`app/modules/contact/models.py:556-557`).

## 2. Who writes `change_kind` (the actual "calculation")

**Nothing in echo-backend assigns or derives it** — grep-confirmed: only the
migration, the schema, and pass-through CRUD mention it. Writers:

- Public `POST/PATCH /contacts/{id}/jobs` (+`/bulk`) — JWT + `ContactsView`
  (`app/routers.py:535-542`).
- Internal `POST /internal/contacts/{id}/jobs` (+`/bulk`, ON CONFLICT DO
  NOTHING) — API key (`app/routers.py:723-727`). **This is the data-team
  pipeline's entry point.**

The pipeline scrapes LinkedIn for **tracked** contacts and pushes the job
history already classified (promotion ≈ new title at same company,
changed_job ≈ new company — exact rules live in the pipeline, NOT in Echo;
unconfirmed, open question for data team).

Tracking lifecycle: a user tracks a contact → `contact_tracker` row (unique
per contact+user, `app/modules/contact/tracker/models.py`). Derived
`tracking_status` (`contact/models.py:894-924`): ACTIVE (tracked + has jobs),
PENDING (tracked, no jobs yet — pipeline hasn't delivered), FAILED (tracked +
`has_invalid_linkedin`), NOT_TRACKED. `started_tracking_at` is per-viewing-user
(reads the `request.user_id` GUC, `contact/models.py:544-554`).
`ContactFollower` is the kforce-era sibling (follow ⊃ track when linkedin
exists); **notifications go to trackers**, not followers.

Dev DB reality (2026-08-13): `changed_job` 194,622 rows / 37,471 contacts;
`promotion` 114,821 / 32,472; NULL 39,390. ~97% of classified rows belong to
**Navitec** (active pipeline); Taller ~9.5k; every other tenant near zero.
Prod unverified (access blocked this session).

## 3. Derived fields (all in `app/modules/contact/models.py`)

- `latest_job_cte` (:815-827): `DISTINCT ON (contact_id) ORDER BY end_date
  DESC, start_date DESC`. Postgres DESC = NULLS FIRST → **an open job always
  wins**; otherwise the most recently ended one.
- `Contact.last_job_update` (:867-873) = that job's `change_kind` → **the
  badge**.
- `Contact.has_updated_job` (:875-881) = that job's `change_kind IS NOT NULL`.
- `Contact.current_job` relationship (:472-488) = latest among **open** jobs
  only → supplies the badge's **date** on the FE.
- Stamps recompute (`contact/repository.py:148-170`,
  `update_contact_job_status_timestamps`, called from every
  create/update/delete/bulk in `job/service.py`): `last_promoted_at` /
  `last_job_change_at` = `MAX(start_date)` per change_kind over **all** jobs
  (not just the latest).
- `Contact.hot_lead` (:926-947): `(last_job_change_at OR last_promoted_at
  IS NOT NULL) AND (no last_interaction_date OR it's older than 6 months OR
  older than GREATEST(the two stamps))`.

## 4. Where it shows (all surfaces)

| Surface | Endpoint | Rules |
|---|---|---|
| Contacts → Dashboard → **Latest Updates** table | `GET /contacts/dashboard` (`contact/routers.py:155-172`) | Contacts **tracked by current user** (GUC; `tracked_by_id__in` overrides, `[]` = everyone) whose **latest job has `change_kind` NOT NULL** (INNER JOIN LATERAL, `filters.py:421-437`). Filters: `last_job_update`, `last_relationship_type(__in)`, `relationship_state__in`, `current_job_start_date__gte/lte`, `current_experience_company_id`. Badge cyan/pink + icons; null → grey "None". |
| Metric tiles (same tab) | `GET /contacts/dashboard/metrics?start_date=` (`repository.py:350-510`) | 6 tiles {Client Contacts, Consultants, Prospects} × {Changed Jobs, were Promoted}: tracked-by-me contacts whose **latest job** has that kind AND `start_date >= timeframe` (FE default 6 months; Last Week → Last 2 Years). Bucket = `last_relationship_type` label; **Prospect buckets also count label-NULL contacts** (`include_nulls=True`). Tile click applies `last_relationship_type__in` + `last_job_update` to the table. Permission `contacts.metrics`. |
| Company Deep Dive → Snapshot → **Latest Updates** card | same `/contacts/dashboard` | Hardcoded `page=1&size=10&order_by=-current_job_start_date&current_experience_company_id=<org>&tracked_by_id__in=<me>` (`echo-frontend src/services/organizations.ts:319-334`); shows 3 + View More. Permission `contacts.view`. |
| In-app notifications | `contact.job.{promotion\|changed_job}` events | Fired on job create/update when the job is **open**, has change_kind, and `start_date` is within the **last 90 days** (`job/service.py:43-65` — measured at push time, so old-history backfills never notify). One notification per **tracker** (`notification/service.py:401-427,486-504`). Labels "Promotion" / "Job Change". Click opens the contact overlay. |
| Email digest | APScheduler every `EMAIL_SCHEDULER_INTERVAL_MINUTES` if `EMAIL_SCHEDULER_ENABLED` (`app/services/email_scheduler_service.py`) | Generic digest of unread+unemailed notifications per user; template `contact_job_update.jinja` **serves all notification kinds** despite the name. Manual trigger: `POST /notifications/send_emails`. |
| **Not shown** | — | Main Contacts tab table (no Update column), contact detail / Job History overlay (no per-job markers). |

## 5. Warm Leads mechanics

- FE dashboard's only sort option: label **"Warm Leads"**, key `hot_lead`,
  default desc (`echo-frontend src/pages/contacts/index.tsx:130-131`,
  `src/components/contacts/filters/Sorts.tsx:3-14`).
- FE **expands** it into 3 backend params (`src/helpers/helpContacts.ts:39-65`):
  `∓last_relationship_type` (opposite prefix!), `±hot_lead`,
  `±client_visits_count`.
- Backend custom sort `hot_lead_sort` (`contact/filters.py:90-121`): leading
  direction-independent "no interaction sorts last" key (on
  `last_interaction_id`), then the boolean expression. Registered in both
  `ContactFilter` and `ContactDashboardFilter` — so the main Contacts tab can
  sort by it too, even though it renders no badge.
- Clicking the Update column header actually sorts by
  `current_job_start_date` (`DASHBOARD_SORT_FIELD_MAP`,
  `src/helpers/helpContacts.ts:16-25`) — never by the enum.

## 6. FE rendering details

- Badge mapping `contactsUpdatesOptions` (`src/constants/optionsEnum.ts:108-121`):
  `promotion` → "Promoted", cyan, `PromotedIcon12`; `changed_job` → "Changed
  Jobs", pink, `ChangedJobsIcon14`. Wired via `Tag type='contactUpdate'`.
- Filter-dropdown mapping `updateOptions` (`optionsEnum.ts:650-663`): same
  labels, **blue/green, no icons** — used only by the dashboard Update filter.
- Date renders as `| MM/dd/yy` (`src/components/ui/Tag.tsx:78-83,146`), only
  when the value is truthy; null value → grey "None" chip, no icon/date.
- `GET /contacts/dashboard` response: `ContactDashboardListResponse`
  (`contact/schemas.py:621-638`) — `last_job_update` is **required** there
  (guaranteed by the filter's NOT NULL join).

## 7. Kforce parity

Same mechanism on `origin/kforce-dev`: `last_job_update` (models.py:1110),
`hot_lead` (:1161), identical 90-day notification gate in `job/service.py`.
Drift is tenancy plumbing only (~150 deleted lines: tenant_id/RLS). FE badge
components are generic — no tenant gate (kforce-only extras are elsewhere:
City/State/Country filters, Business Funnel).

## 8. Gotchas / inconsistencies found

1. **Badge kind vs date disagree**: kind comes from the latest job
   (open-or-ended), date from `current_job` (open only). No open job → badge
   with no date; and the date shown is the *current job's start*, not the
   change event's date.
2. **Dashboard ≠ hot_lead semantics**: a contact whose latest job is
   unclassified but has older classified jobs (stamps set → `hot_lead` TRUE)
   is **excluded** from Latest Updates and the tiles (both key on the latest
   job) yet ranks as a warm lead in the Contacts-tab sort and may have
   produced notifications.
3. **Three FE vocabularies** for one enum: badge (Promoted/Changed Jobs,
   cyan/pink + icons), filter dropdown (same labels, blue/green, no icons),
   notifications ("Promotion"/"Job Change"). Icon sizes differ (12 vs 14 px).
4. Update column pretends to sort but sorts `current_job_start_date`.
5. Metric-tile toggling accumulates filters across tiles (only the last is
   highlighted, previous tile's filters stay applied).
6. `has_updated_job` FE param is dead code.
7. `formatDate` uses naive `new Date(...)` → UTC-midnight dates can shift a
   day in local render.
8. 90-day notification window is measured at pipeline-push time
   (`datetime.now()` naive) — deliberate anti-flood, undocumented.
9. `contact_job_update.jinja` is the digest template for ALL notification
   kinds (misleading name).
10. Domain doc `echo-flows-docs/03-contacts.md` calls hot lead a "score…
    based on relationship and client visits" — inaccurate (it's the boolean
    above; relationship/client-visits are FE tiebreak sort params).
11. Deprecated legacy metric keys (`clients/consultants/alumni_tracked_count`)
    still served during the FE deprecation window (see
    [[Label-state dashboard contract convergence (Task 24200)]]).

## 9. Open questions

1. ~~**Data team**: exact classification rules~~ **RESOLVED 2026-08-13** — the
   classifier is ours: `profiles_api` repo,
   `app/modules/webhook/jobs_sync.py::compute_change_kind` (flat DESC chain by
   `(end_date|today, start_date)`; same company vs older neighbor → promotion,
   different → changed_job, oldest → NULL). Still open: re-scrape cadence and
   which tenants have an active pipeline (dev: almost only Navitec).
2. **Product**: should Latest Updates include contacts with signals only in
   older history (gotcha 2)? What date should the badge show (gotcha 1)?
3. Prod volumes unverified (dev measured only).

## 10. Update 2026-08-13 — feature kicked off (PRD In Progress)

The PRD stopped being a maybe: extending `ChangeKind` with **`added_job`**
(added a concurrent job without leaving the current one — startup, consulting)
and **`retired`** (LinkedIn "Retired" position). Decisions already closed with
Pedro live in the PRD §8; split of work: `profiles_api` reworks
`compute_change_kind`, echo-backend adds the enum values + stamps + metrics +
notification subscribers (dev + kforce twin), FE maps the new values (both apps).

Key findings from the profiles_api code dive (all in the PRD):

- Sync is a **delete-all + bulk-create reconciliation** per (mapping, profile)
  with a signature fast-path (`_job_signature` includes `change_kind`) —
  so the PRD's original "backfill can't go through bulk" claim was **wrong**:
  re-enqueueing sync after classifier v2 rewrites history correctly.
  Side effects: rewrite wave (~350k rows dev) + duplicate `contact.job.*`
  notifications for open jobs < 90 days old.
- **Deploy order is a hard gate**: echo enum migration must land before
  profiles_api emits new values — the DELETE runs before the POST, so a 422
  on unknown enum leaves the contact with no job history until retry passes.
- Edge found: `added_job` rule keyed on "previous job still open **today**"
  drifts to `changed_job` when that job later closes (signature change →
  auto rewrite). Flagged as PRD §8.5.5.

Local setup note: profiles_api `.env` verified (settings load, dev DB
connects, both JSON blobs parse); `uv sync` blocked on the Azure Artifacts
feed — the existing PAT lacks **Packaging → Read** scope, `~/.netrc` is ready
and just needs the new PAT pasted in. `OUTBOX_ECHO_SYNC_ENABLED` in `.env` is
consumed by nothing (likely meant `OUTBOX_UNIFIED_UNTAG_ENABLED`). psycopg2
builds from source there: needs `LDFLAGS`/`CPPFLAGS` pointing at Homebrew
`openssl@3` + `libpq`.

## Related

- Map: [[Map - Contact Relationships]]
- Deliveries: [[Generic Contact Relationships (US 23240)]] ·
  [[Kforce Contact Relationships port (US 23370)]] ·
  [[Label-state dashboard contract convergence (Task 24200)]] ·
  [[Contact bulk_track IntegrityError (Bug 23251)]]
- PRD (private, **In Progress** since 2026-08-13):
  [Contact job-update signals — PRD Técnico](https://app.notion.com/p/3bbaedca11f0814392fdc104776f3c37)
- Sibling repo: `/Users/gonza56d/taller/repos/profiles_api` (the classifier —
  `app/modules/webhook/jobs_sync.py`)
- Domain doc: `taller-projects/echo-flows-docs/03-contacts.md`
