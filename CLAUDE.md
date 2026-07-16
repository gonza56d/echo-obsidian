# CLAUDE.md — echo-obsidian vault conventions

Personal Obsidian vault of **gonza56d** — a delivery memory for Echo work
(echo-backend, echo-frontend, infra). NOT team documentation: domain
rationale for the team lives in `echo-backend/vault/Echo/`; this vault is
the personal, cross-feature "what did we ship, how, and what's still
pending" brain. Read this file before writing anything here.

## Structure

```
Home.md          — dashboard: In flight + Recent activity + Maps index
Deliveries/      — ONE note per delivered feature/bugfix (the atomic unit)
Maps/            — Maps of Content ("Map - <topic>.md") linking deliveries
                   into sagas (Contact Relationships, Kforce, Pentest, …)
Templates/       — Delivery.md (frontmatter schema + section skeleton)
CLAUDE.md        — this file
```

## The atomic unit: a delivery note

- **One note = one delivery** (a feature, a bugfix, an upgrade), NOT one PR.
  A delivery may span many PRs (milestones, kforce twins, qa/main
  cherry-picks) — they all belong in the same note.
- File name: `<Short recognizable title> (<US NNNNN | Bug NNNNN | PR NNNN>).md`.
  The parenthesized ref makes `rg`-by-ticket work.
- Follow `Templates/Delivery.md`: frontmatter (`type/status/env/delivered/
  tags/prs/fe_prs/tickets/prd`) + sections What / Azure / PRs / How /
  Decisions / Gotchas / Pending / Related.
- `status`: `in-progress` → `in-review` → `merged` → `shipped-prod`.
  `env`: `taller | kforce | both | infra`.
- **Link liberally** (`[[...]]`): every delivery links its Map(s) and its
  sibling deliveries (ports, follow-ups, superseded rules). Maps link back.
  A broken `[[link]]` marks a note worth writing, not an error.
- Write for the reader who lost all context: PRD + tickets + PR links first,
  then the *shape* of the implementation, then decisions/gotchas/pending.
  "Pending" is the most valuable section — keep it truthful and update it
  when items close.

## When to update (mandatory triggers)

1. **`gh pr create`** (echo-backend or echo-frontend) → create/update the
   delivery note with the PR link, status `in-review`.
2. **`git push` of new commits to an open PR** → update the note (what
   changed: review fixes, new decisions, new gotchas).
3. **A PR merges / work ships** → flip `status`, set `delivered`, prune
   "Pending".
4. **Touching a shipped feature that has no note** → backfill one as part
   of the task (this vault started 2026-07-16; older work may be missing).
5. After 1–3, **update `Home.md`**: In flight + Recent activity.

## Git

- Commit after every update session:
  `git -C /Users/gonza56d/taller/repos/echo-obsidian add -A && git -C ... commit -m "vault: <what>"`.
- **NEVER push.** The user pushes manually if/when they want the remote
  updated.

## Write mechanics (worktree-guard)

echo-backend has a PreToolUse hook (`.claude/hooks/worktree-guard.py`)
guarding Edit/Write/NotebookEdit:

- **Session in the main echo-backend checkout** (any branch): writes into
  this vault work normally — the guard only blocks paths *inside* the
  echo-backend tree on protected branches.
- **Session inside a worktree**: the guard blocks ANY Edit/Write outside
  that worktree — including this vault. Do NOT disable the guard; write the
  file via Bash instead:

  ```bash
  python3 - <<'EOF'
  from pathlib import Path
  p = Path("/Users/gonza56d/taller/repos/echo-obsidian/Deliveries/<note>.md")
  p.write_text("""<content>""")
  EOF
  ```

  (Bash is not intercepted; this is the sanctioned escape hatch. Same for
  the `git -C` commit commands, which work from anywhere.)

## Consulting the vault (why it exists)

When a task touches previously delivered work — a bug in a shipped feature,
"improve/extend X", a regression, any "we did this before":

1. `rg -il "<ticket>|<pr>|<keywords>" /Users/gonza56d/taller/repos/echo-obsidian --glob '!.git'`
2. Read the matching delivery note(s) and their Map **before** reading code —
   they carry the PRDs, decisions and gotchas the code does not show.
