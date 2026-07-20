---
type: delivery
status: in-review
env: taller
delivered:
tags: [chore, repo-hygiene, git]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1860"
fe_prs: []
tickets: []
prd: ""
---

# Untrack committed vault directory (PR 1860)

The `echo-backend/vault/` Obsidian notes directory had been accidentally committed to the repo and stayed tracked despite being in `.gitignore`. Untracked it (`git rm --cached`, files kept on disk) so the ignore rule finally applies and Obsidian's constant `workspace.json` churn stops blocking clean `git pull`s. Non-ticketed chore.

## Azure / docs
- No ticket (repo-hygiene chore).

## PRs
- [#1860](https://github.com/taller-projects/echo-backend/pull/1860) → `dev` — open (in review)

## How
- Investigated authorship: across **every ref**, all 7 commits touching `vault/` are the author's; it first entered via deploy-merge PR #1112 (2026-04-15), swept in by accident.
- `git rm -r --cached vault/` on the branch `chore/untrack-vault-directory` — removes the 24 files from the index only; local copies untouched.
- No `.gitignore` edit needed: `vault/` was already ignored (line 6, committed); the rule was simply a no-op for files committed before it existed.

## Decisions
- **`--cached`, not a full delete** — the user wanted to *untrack* and drop it from upstream while keeping the local notes.
- **Left the doc references alone.** `CLAUDE.md`'s "## Vault (`vault/Echo/`)" section, `.claude/skills/pr-review/SKILL.md`, `.claude/agents/pr-reviewer-prd.md`, and code comments (`auth.py`, `session_validation_service.py`, `proposal_builder.py`) still point at `vault/Echo/`. Some already referenced notes that were **never committed** (e.g. `vault/Echo/Security/4.1.3-...md` — no `Security/` folder was ever in the repo), which is itself evidence the checked-in "team vault" was only ever partial/accidental. Cleaning up the convention is a separate documentation decision, flagged to the user, not folded into this chore.

## Gotchas
- Classic git trap: adding a path to `.gitignore` does **not** untrack files already committed — they need `git rm --cached`.
- The real pull friction was `vault/Echo/.obsidian/workspace.json`, which Obsidian rewrites every session → perpetual uncommitted change on a tracked file.
- Note the naming collision: most repo hits for "vault" are the unrelated **HashiCorp Vault** secret manager (`VaultService`, `VAULT_ENABLED`), which must not be touched.

## Pending
- Merge #1860 → `dev`; it then reaches `main` via the normal release flow (removes `vault/` from upstream everywhere).
- Decide whether to strip the now-dangling `vault/Echo/` references from `CLAUDE.md` / pr-review skill / agent files / code comments (separate follow-up).

## Related
- (no Map — standalone repo-hygiene chore)
