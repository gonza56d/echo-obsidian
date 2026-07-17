---
type: delivery
status: merged
env: kforce
delivered: 2026-07-08
tags: [feature, kforce, contact]
prs: [1725, 1726, 1727]
tickets: [23424, 23425, 23426, 23427]
prd: "Tech PRD Notion 38faedca §7 (People Involved + contact-level totals)"
---

# Kforce relationship card aggregates M6 (US 23424)

Follow-up to [[Kforce Contact Relationships port (US 23370)]] covering 3 business-PRD sections M1–M4 didn't: People Involved by role, and contact-level Total Placements / Total Client Visits. All additive/on-read, no enum or column changes.

**Docs:** [Tech PRD §7 — People Involved + contact-level totals](https://app.notion.com/p/38faedca11f0811d9ae4f0a5a2f4e76f)

## PRs (all → kforce-dev, merged 2026-07-08 — merge commits, not squash)
- [#1725](https://github.com/taller-projects/echo-backend/pull/1725) **M6.1** ([23425](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23425)) — `people_involved` JSONB column_property on `Relationship` (sales_reps/recruiters/consultants/client by role). Gap documented: Sales Rep has no source field → falls back to `contacted_by`.
- [#1726](https://github.com/taller-projects/echo-backend/pull/1726) **M6.2** ([23426](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23426)) — contact-detail **Total Placements**: grouped breakdown can't be a column_property (needs LATERAL) → `ContactRepository.total_placements()` + `Field(None, _select_strategy="lazy")` attached in a `get_contact_detail` service override.
- [#1727](https://github.com/taller-projects/echo-backend/pull/1727) **M6.3** ([23427](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23427)) — **Total Client Visits**, same pattern; client visits = `contact_interaction` by `related_company_id` (NOT `contact_activity`).

## The stacking saga (Pedro's round-2 blocker)
[#1726](https://github.com/taller-projects/echo-backend/pull/1726) and [#1727](https://github.com/taller-projects/echo-backend/pull/1727) each introduced their own `get_contact_detail` override attaching only its field — a "take one side" merge would silently drop a field. Fix: **stacked [#1727](https://github.com/taller-projects/echo-backend/pull/1727) on [#1726](https://github.com/taller-projects/echo-backend/pull/1726)'s branch** with a single combined override, re-targeted bases via `gh api` as parents merged. Lesson: when two open PRs add the same override/hook point, stack them and combine at the shared point — don't rely on merge luck.

## Related
- `repo.get(response_model=...)` returns the ORM row (response_model only shapes the SELECT) — set lazy computed attrs on it in the service, mirroring talent `similarity_score`.
- [[Map - Kforce]] · [[Map - Contact Relationships]]
