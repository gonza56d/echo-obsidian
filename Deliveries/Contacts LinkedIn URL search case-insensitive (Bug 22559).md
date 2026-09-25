---
type: delivery
status: merged
env: both
delivered: 2026-09-25
tags: [bugfix, contacts, search, linkedin]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2346"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22559"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22383"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/11124"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25148"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25149"
prd: ""
---

# Contacts LinkedIn URL search case-insensitive (Bug 22559)

QA (Gisel, TC-22383-A8) typed `HTTPS://WWW.LINKEDIN.COM/IN/TOMYTEST/` into the `/contacts` search bar and got "No matches". Stored `https://www.linkedin.com/in/tomytest/` exists (QA contact `cd9008f0…`). This is a bug in the LinkedIn search branch from [US 22383](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22383) ([#1359](https://github.com/taller-projects/echo-backend/pull/1359), May 2026). The fix: the section segment is now normalized case-insensitively, and the search matches `linkedin IN (as_typed, lowercased)`.

## Azure / docs
- [Bug 22559](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22559) (→ In revision 2026-09-24, PR linked → **Closed** 2026-09-25 on merge) · original [US 22383](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22383) · sibling [Bug 22560](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22560) (email search, closed) · Feature [11124 Contacts](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/11124)

## PRs
- [#2346](https://github.com/taller-projects/echo-backend/pull/2346) → dev — **MERGED 2026-09-25** (squash `88ce7381`, CI green on `341bf2f5`). No FE impact: same `search` param and response.
  - Commit 2 `7611bc1d` (review follow-up, 2026-09-24): new tests for the case variants, the pinned gap, another tenant and `/SCHOOL/`; removed a stale comment. PR body updated with the talent audit, the EXPLAIN re-run and a QA retest note.
  - Pedro's review ([5310179858](https://github.com/taller-projects/echo-backend/pull/2346#pullrequestreview-5310179858)): APPROVED, READY WITH NITS. Commit 3 `341bf2f5` (2026-09-25): uppercase and mixed-case inputs in `test_is_linkedin_profile_url_positive` (the PR body had claimed them), and `in_({…})` as a set so a lowercase search binds one value. Follow-ups opened: [Task 25148](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25148) and [Task 25149](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25149). Scope comment on Bug 22559 (TC-A8 covers lowercase-stored slugs). PR body updated via REST, and I replied on the PR.

## How
- Root cause 1: `app/core/linkedin.py::normalize_linkedin_url` compared `parts[0]` to `{"company","in","school"}` case-sensitively. `/IN/` fell through to `return url`, so the URL stayed raw.
- Root cause 2: `ContactFilter.global_search_query` did an exact `linkedin == normalized`. Even after normalization, `/in/TOMYTEST/` ≠ `/in/tomytest/`.
- Fix: `section = parts[0].lower()`, and the slug keeps its case. The filter now matches `linkedin.in_([normalized, normalized.lower()])`.

## Decisions
- **Not `lower(linkedin) = lower(:q)`**: no index covers `lower(linkedin)`. On kforce-dev (1.6M contacts) that is a parallel seq scan of **4.5 s**. The `IN` form uses `contact_tenant_linkedin_uniq_idx`: **0.5 ms**.
- **Stored values must NOT be lowercased**: prod has 133 case-sensitive member-id URLs (`/in/ACwAA…`, `/in/ACoAA…`), percent-encoded slugs (`%C3%A1`), and 10 tenant-level `lower(linkedin)` collisions. So no lowercase unique index and no write-side lowercasing.
- The normalizer change also hits the write path (`LinkedinUrl` annotation, orgs, talents): `/IN/…` or `/Company/…` inputs are now stored canonical instead of raw. No stored contact in dev / prod / kforce-dev has an uppercase section, so existing rows don't change.
- **Self-review r1 (/pr-review) was READY WITH NITS; all nits were fixed in `7611bc1d`.** Stored rows with an uppercase section: none in `contact` or `organization` in any env; `talent` has a few legacy raw rows with a scheme (`HTTPS://…/IN/…`): dev 2, prod 3, kforce-dev 4, qa 0. Those rows now miss the exact talent lookups; only a re-apply with a different email could duplicate them. They were left alone; a cleanup must skip the canonical collisions (1 dev, 1 prod). Scheme-less `Linkedin.com/in/…` rows are unaffected because the normalizer passes them through.

## Gotchas
- EXPLAIN re-run as the app role: `SET LOCAL ROLE echo_backend` in `BEGIN READ ONLY` works from the pooler `postgres` login. `contact` RLS for `echo_backend` is `Backend full access` (`USING true`) in dev, prod and kforce-dev, so tenant isolation on `contact` is app-level (the repository's `tenant_id` filter), not RLS. Index Scan on `contact_tenant_linkedin_uniq_idx`: 0.8 ms for the page, 0.08 ms for the count.
- QA's Tomy Test is stored with a lowercase slug, so TC-22383-A8 passes after the dev → qa promotion.
- Mixed-case rows by env: prod 314 / 59k with linkedin, dev 703 / 66k, kforce-dev 107 / 200k, qa 9 / 1.2k. Most are percent-encoded or member ids. Only about 13–22 per env are genuine mixed-case vanity slugs (e.g. `/in/AbduEndrisM/`).
- kforce-dev has 1.64M contacts, but only 200k have a linkedin.
- The worktree isolation guard blocks `zsh -ic` and heredocs, so the Azure PAT was read by a python dotfile script from `~/.zshrc`. The PAT there is **single-quoted**.
- `ruff format` on test files reformats unrelated pre-existing lines. Lint only covers `app/`, so format tests by hand to keep the diff minimal.

## Pending
- [x] CI green → Pedro APPROVED → squash-merged to dev 2026-09-25 → Bug 22559 Closed.
- [ ] qa promotion + QA re-test of TC-22383-A8.
- [ ] Residual gap, accepted and tracked in [Task 25149](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25149): a stored mixed-case vanity slug searched with different casing still misses. If needed: `CREATE INDEX CONCURRENTLY (tenant_id, lower(linkedin)) WHERE linkedin IS NOT NULL` and switch to `lower()`.
- [ ] Legacy uppercase-section `talent.linkedin_url` rows (dev 2, prod 3, kforce-dev 4): guarded cleanup in [Task 25148](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25148). It must skip the canonical collisions.
- [ ] Not in scope: a decoded slug (`/in/thainá-…`) doesn't match a stored percent-encoded one.

## Related
- [[Map - Kforce]] (KForce-scale query cost) · [[Contact bulk_track IntegrityError (Bug 23251)]] (same `contact_tenant_linkedin_uniq_idx`)
