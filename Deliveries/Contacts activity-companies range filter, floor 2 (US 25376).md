---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, contacts, filters, kforce-scale, review]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2387"
  - "https://github.com/taller-projects/echo-backend/pull/2218"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25376"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25377"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25378"
prd: ""
---

# Contacts activity-companies range filter, floor 2 (US 25376)

The company-detail Contacts tab had a `multi_company_activity` Yes/No toggle (Patricio's [#2218](https://github.com/taller-projects/echo-backend/pull/2218), 2026-09-04: contacts with activity in 2+ companies; `false` filters nothing). Product wants a **range of companies with activity** (2–4, 5+). Patricio's [#2387](https://github.com/taller-projects/echo-backend/pull/2387) adds `activity_companies_count__gte` / `__lte` to `ContactFilter` over the same CTE; my review (2026-10-06) found the floor-1 path is a guaranteed statement timeout on KForce, and I pushed the fix (floor 2) to his branch. This note also backfills #2218, which had none.

## Azure / docs
- [US 25376](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25376) → BE [Task 25377](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25377) (Patricio) · FE [Task 25378](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25378) (pending, options TBD).
- No Notion PRD. Patricio's kforce-dev measurements live in a comment on US 25376 (2026-10-05).

## PRs
- [#2218](https://github.com/taller-projects/echo-backend/pull/2218) → dev — merged 2026-09-04 (`1cb35705`): the original toggle. MATERIALIZED CTE `multi_company_activity_matches` over `contact_relationship` + partial index `ix_contact_relationship_multi_company_activity`, `id = ANY(ARRAY(...))` instead of a join (planner guesses ~140k matches and merge-joins the whole pkey, 40 s).
- [#2387](https://github.com/taller-projects/echo-backend/pull/2387) → dev — OPEN. Patricio `fbe520ce` (range, `ge=1`) + my `c18b669f` 2026-10-06 (floor 2, tests, docs). PR body rewritten by me to match floor 2 (`gh api -F body=@file`; `-f body=@file` sends the literal string).
- FE: none yet. Additive query params only; `multi_company_activity` still honoured; no response-shape change.

## How
- `MIN_ACTIVITY_COMPANIES = 2` in `app/modules/contact/constants.py` (with the why). Both params `Field(ge=MIN_ACTIVITY_COMPANIES)`; `filter()` computes `min_companies = gte or MIN_ACTIVITY_COMPANIES`, `max_companies = lte`, builds the HAVING bounds inline (`count(distinct company_id) >= min [AND <= max]`) on the existing CTE. `multi_company_activity=true` is `gte=2`; `false`/unset is "toggle off".
- Validation: `ge=2` on both + `model_validator` for `gte > lte` → 422 via fastapi-filter `FilterWrapper.__new__` → `RequestValidationError`.
- Contact groups: unchanged branch, companies counted per group root; new test in `tests/unit/test_contact_groups.py` (`2–2` vs `3+`). `docs/contact-groups.md` names the range params.
- Tests: `tests/unit/test_contact_multi_company_activity.py` (contacts active in 0–4 companies; ranges, toggle+range, toggle+explicit gte, false+range, rejections with `match=`, endpoint 422s). 71 passed locally across both modules.

## Decisions
- **Floor 2, not 1.** Patricio measured floor 1 on kforce-dev: CTE 371 ms but 277,168 ids → 43.8 s probing `contact_pkey` for 25 rows; request `DB_STATEMENT_TIMEOUT_MS` is 20 s. Distribution: 1 → 273,526, 2 → 3,642, 3+ → 0. `lte` shares the floor so `lte`-only cannot reopen the path. US 25376 text still says "1 allowed in the backend" — needs updating.
- Alias + ceiling: with `ge=2` on `lte`, `true&lte=1` is a 422 instead of a silently empty page.
- Single-use `_companies_count_bounds` staticmethod dropped; the floor is computed in one place.

## Gotchas
- `docs/` is gitignored: `git add -f docs/contact-groups.md` or the whole `git add` aborts and the commit silently does nothing.
- Worktree session: the guard blocks Write/Edit outside the worktree (scratchpad included) and refuses compound Bash / heredocs it cannot verify; write the script inside the worktree and run `python3 <file>` as a plain command.
- `uv run` in a fresh worktree creates its own `.venv` (fine, ~1 s); Pyright then shows bogus missing-import diagnostics.

## Pending
- CI on `c18b669f` + Patricio's ack of the floor change (his US comment proposed it).
- Update Task 25377 / US 25376 text: floor 2, `lte`-only = from 2.
- kforce-prod distribution query (US comment) → decide FE options with product (on kforce-dev every range above 2 is empty).
- Saved shortcuts mapping (`user_shortcuts.filter` JSONB, `true` → 2+, `false` → none) has no owner; needed before removing the alias. Precedent: migration `4f430d2b4997`.
- Squash-merged dev 2026-10-06 (`b6790711`). Release [#2392](https://github.com/taller-projects/echo-backend/pull/2392) `dev` → `qa` **OPEN 2026-10-07** (with #2381 + #2386). Next: merge it, then qa → main.

## Related
- [[Map - Contact Relationships]] · [[Map - Kforce]]
- [[Contact external ids follow-ups - list filter via links, links dropped on delete, duplicate references (25372-25374)]] (same `ContactFilter` / groups surface)
