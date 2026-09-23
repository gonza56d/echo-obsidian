---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, contacts, relationships, kforce, migration]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2341"
fe_prs: []
tickets: []
prd: ""
---

# Relationship recency by activity dates (PR 2341)

KForce reported that the expanded rows of the contacts list put older relationships above newer ones. The recency order was `end_date DESC NULLS FIRST, start_date DESC NULLS FIRST`. KForce Clients carry no `start_date`/`end_date` (806k of 808k on kforce-dev; their dates live in `activity_dates`), so every Client tied, came back in arbitrary order, and outranked any dated Consultant or Prospect. Pedro's (rocha-p) PR replaces it with one key, `relationship_recency_order`: an open relationship first, then `greatest(activity_dates bounds, start_date, end_date) DESC NULLS LAST`, then the legacy order. No ticket. I reviewed it, fixed the one blocker myself and approved on 2026-09-23.

## Azure / docs
- No ticket or PRD. The PR body is the spec.
- Repo doc: `docs/contact-groups.md` → "Recency order (2026-09-23)".

## PRs
- [#2341](https://github.com/taller-projects/echo-backend/pull/2341) → dev. Pedro's commit `aa02e77a`, plus my blocker fix `0e55dbad`. **APPROVED by me 2026-09-23**, not merged yet.
- FE: the overlay Activity tab (`Relationship/Activity.tsx`) still sends `order_by=-end_date,-start_date`. It should send `-recency`, which has no FE ticket yet. The route shapes are unchanged: `recency` is an added sort value, and the default order is unchanged.

## How
- The key has four copies: `relationship_recency_order` (models.py), used by `Contact.relationships`, `_last_relationship_type_expr` and `recency_sort`; `RELATIONSHIP_RECENCY_ORDER_SQL` (the trigger function); the repo view `smart_search_contacts_info.sql`; and `_relationship_recency` (the Python key for the group merge). Tests pin parity between them.
- `RelationshipFilter` moves to `AdvancedFilter` and gains the custom sort `order_by=-recency` / `recency` with an `id` tiebreak.
- Migration `j03pxu12yitx` (revises `zolvj810zl6j`) does three things. It replaces `_recompute_last_relationship_type`. It rewrites the view only where it has the repo shape. It recomputes `last_relationship_type` for contacts that have more than one relationship type, in an `autocommit_block` with `statement_timeout` cleared and then restored. The reason: the scan takes about 60 s cold on kforce-dev.
- **My fix `0e55dbad`:** `previous_relationship_id` now orders by `relationship_recency_order`, and there is a new `bulk_check` test. `docs/contact-groups.md` was updated.

## Decisions
- **The review blocker (fixed by me):** `previous_relationship` (`_last_relationship_type_expr`, new key) and `previous_relationship_company` (via `previous_relationship_id`, old key) came from different rows. `POST /contacts/bulk_check` returns both, and the FE shows "<type> at <company>" (`ContactMatchReviewForm.tsx`). Example: an ended Consultant at A plus an undated Client at B read "Consultant at B". The test fails without the fix (it returned B's name) and passes with it.
- Left as follow-ups (review nits, not done): `current_relationship_id` still uses the old key and a different definition of "open", so the TrackerRMS outbox type diverges from the pill. `_latest_relationship_company_id` (tenure) also still uses the old key. The shared key has no terminal `id`. The 4 activity kinds are hard-coded in the SQL copies. The Python copy of the key could be removed.

## Gotchas
- **Data impact on Taller prod is not in the PR body.** I measured it read-only on 2026-09-23: 49 contacts change. 46 are Navitec (Prospect→Consultant 28, Prospect→Client 17, Client→Prospect 1) and 3 are Taller (Client→Prospect). kforce-dev shows 598 changes, which matches the author's count. kforce-prod shows 520 per the author.
- The deployed `view_smart_search_contacts_info` on prod, dev and kforce-dev is the 41-column owner-managed view and reads the **persisted** column, so the migration's view no-op is correct there. qa runs the repo's 12-column view, which the migration rewrites.
- No malformed `activity_dates` bounds on kforce-dev, prod, dev or qa. A bad bound would now break every write, because the trigger casts it to `timestamptz`. I couldn't check kforce-prod: there is no PGSERVICE for it.
- A pre-existing failure unrelated to this PR: `tests/system/test_contact_bulk_check.py::test_classifies_by_current_user_tracker` fails (`'U' == 'u'`) with or without the PR. CI doesn't run tests/system.
- In a worktree-isolated session, `source`, compound VCS commands and Write outside the worktree are blocked. Call the main venv's python directly: `/Users/gonza56d/taller/repos/echo-backend/.venv/bin/python -m pytest`.

## Pending
- Pedro: merge, then qa/main promotion.
- Product sign-off for the pill change on about 570 prod contacts (KForce 520 + Navitec 46 + Taller 3). There is no ticket.
- FE ticket for the overlay's `order_by=-recency`.
- Ticket the follow-ups: `current_relationship_id` and `_latest_relationship_company_id` onto the new key.
- The PR body's "Not changed" list should drop `previous_relationship_id` (flagged in the approval comment).

## Related
- [[Map - Contact Relationships]] · [[Map - Kforce]] · [[Generic Contact Relationships (US 23240)]] · [[Kforce Contact Relationships port (US 23370)]] · [[Alumni label removal (PR 1742)]]
