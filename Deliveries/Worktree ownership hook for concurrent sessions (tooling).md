---
type: delivery
status: in-progress
env: infra
delivered:
tags: [chore, tooling, claude, worktrees, hooks]
prs: []
fe_prs: []
tickets: []
prd: ""
---

# Worktree ownership hook for concurrent Claude sessions (tooling)

Running several Claude sessions on echo-backend at once (one per ticket/PR) kept corrupting each other's worktrees, branches and commits, even though "new ticket = new worktree" was the rule. Root cause: sessions were not isolated at all. A new session was **born inside another session's worktree** (tmux inherits the pane's cwd, and Claude chdir()s into its worktree), so two sessions shared one working tree and one branch. Built a **personal PreToolUse/SessionStart/UserPromptSubmit hook** (not in the repo yet) enforcing one writer per worktree, branch pinning, and a clean base for new worktrees. **On trial since 2026-09-23**; if it holds up, upstream it to echo-backend for the team. **Reworked 2026-09-25**: `claim-worktree` removed; every agent works in its own worktree, and an agent continuing another agent's work branches a new worktree off it (see *2026-09-25 rework*).

## Azure / docs
- No ticket (personal Claude Code tooling).
- Claude Code docs: [hooks reference](https://code.claude.com/docs/en/hooks.md) · [worktrees](https://code.claude.com/docs/en/worktrees.md) · [settings: worktree](https://code.claude.com/docs/en/settings-reference.md#worktree)

## PRs
- None yet. Lives outside git:
  - `~/.claude/hooks/echo-worktree-owner.py`: the hook (one script, dispatches on `hook_event_name`)
  - `~/.claude/hooks/test_echo_worktree_owner.py`: 76 scenario tests
  - **versioned snapshot in this vault**: `Tooling/worktree-owner-hook/` (same two files; re-copy after editing the live ones)
  - registered in `echo-backend/.claude/settings.local.json` (2 entries: `PreToolUse` matcher `Bash|Edit|Write|NotebookEdit|EnterWorktree`, `SessionStart`; command `python3 "$HOME/.claude/hooks/echo-worktree-owner.py"`). The `UserPromptSubmit` entry was dropped with `claim-worktree`.

## Root cause (2026-09-23 incident)
- **Mechanism**: on `EnterWorktree` Claude `chdir()`s its process into `.claude/worktrees/<name>` (the `lsof` cwd of every live `claude` PID = its worktree). `~/.tmux.conf` binds `split-window` / `new-window` with `-c "#{pane_current_path}"`, so a pane opened next to a busy session starts **inside its worktree**, and the `claude` launched there shares it.
- **Evidence**: the `/pr-review 2329` and `/pr-review 2330` sessions and the /pr-review-fix session were fresh launches (`parentUuid: null`) whose first cwd was already the 24242 / 25063 worktree.
- **Damage**: `/pr-review` with no id picked [#2331](https://github.com/taller-projects/echo-backend/pull/2331) and ran `git fetch origin pull/2331/head:pr2331; git checkout pr2331` **inside the 25063 worktree** (11:31) while the [#2330](https://github.com/taller-projects/echo-backend/pull/2330) review session was fixing nits there. Its tree switched under it, and the blocker fixes had to go through a throwaway worktree (`584b45a3`). The 25063 worktree is still checked out on `pr2331`.
- **History**: the main checkout also hosted feature-branch commits (24772/24774 on 2026-09-07, 25002 on 2026-09-17). Any session starting in the "lobby" meanwhile shared that branch.
- **Latent**: `worktree.baseRef: head` means `EnterWorktree(name)` from inside worktree A bases the new branch on A's HEAD, so the new PR carries A's commits. Not hit yet (recent branches checked against `origin/dev`).
- **Why config alone can't fix it**: `baseRef` only accepts `fresh` (bases on `origin/<default>` = `main` here) or `head`. The `WorktreeCreate` hook is documented only for `--worktree`, subagent `isolation: worktree` and background sessions, not `EnterWorktree`. There is no built-in cross-session worktree lock (Claude's `git worktree lock` is cleanup protection only).

## How
- **1. One agent per linked worktree.** Owner = `session_id` in `<worktree git dir>/claude-owner.json` (e.g. `.git/worktrees/<name>/`, outside the working tree, removed with the worktree). A session's first write in an unowned worktree claims it **only if the worktree was created after the session started** (git-dir birth time vs the session's birth time in `~/.claude/state/claude-owner/births/`, recorded at `SessionStart` or, failing that, at the first tool call). This covers `EnterWorktree(name)`, `git worktree add` + `EnterWorktree(path)` and subagent isolation worktrees (they share the parent's `session_id`). Worktrees that predate the session are another agent's, including the one a tmux split or `/clear` drops it into. Ownership never expires and never transfers.
  - Non-owners are **read-only** there. These work: reads, `git log/diff/show/fetch/status`, `gh pr view/diff/comment/review`, `gh api`, `python3 -c` readers, `sed -n`, and writes *outside* the tree (scratchpad review files). Blocked: edits, commits, tests, lint, `sed -i`, redirects into the tree.
  - A command that gets blocked claims nothing (claims are committed only when the whole call is allowed).
  - Cross-tree writes into someone else's worktree are blocked too (`rm -rf .claude/worktrees/X`, `git worktree remove X`). Lock/birth files are write-protected (`claude-owner` marker).
- **2. Branch pinning** (owners too; every checkout incl. the main one).
  - Blocked: `git checkout <ref>` (incl. `-b`), `git switch`, `gh pr checkout`. Allowed: `git checkout -- <path>`, `git restore`, `git branch -m` (rename the fresh `worktree-*` branch).
  - Stash: bare `git stash`, `stash -u`, `stash pop` and `stash clear` are blocked (the stack is shared by all worktrees). `stash push -m <tag>` and `stash apply <sha>` are allowed.
  - The block message gives alternatives: `gh pr diff`, a detached PR worktree (`git -C <main> fetch origin pull/<N>/head && git -C <main> worktree add --detach <main>/.claude/worktrees/pr-<N> FETCH_HEAD`), or `EnterWorktree(name)`.
- **3. Clean base.** `EnterWorktree(name)` is denied when `origin/dev..HEAD` is non-empty (after a quick `git fetch origin dev`). The message gives `git -C <main> worktree add -b <ticket>/<name> <dir> origin/dev` + `EnterWorktree(path)`.
- **Bash parsing**:
  - `shlex` with operator punctuation, including newlines.
  - Heredoc bodies stripped, so PR bodies mentioning "git checkout" pass.
  - `$(...)`, backticks and `bash -c` are analyzed recursively.
  - `cd` / `git -C` tracked per segment.
  - Unparseable input: the pin regex applies, and in a foreign tree it's treated as a write.
- **No handoff.** An agent that must continue another agent's work creates its own worktree off that worktree's commits (`git -C <main> worktree add -b <new-branch> <main>/.claude/worktrees/<dir> <its branch>` + `EnterWorktree(path)`) and publishes with `git push origin HEAD:<its branch>`. Every block message prints both recipes (new ticket off `origin/dev`, continuation off the current worktree). `git worktree add` is allowed from inside a foreign worktree; only its target path is checked. Kill switch: launch with `CLAUDE_OWNER_GUARD_OFF=1 claude` (hook env = the Claude process env, which the model can't change).
- **Scope**: only checkouts sharing the session's git common dir (echo-frontend via `git -C` is untouched). The hook fails open on exceptions, logged to `~/.claude/state/claude-owner/errors.log`.
- **Verified**: `python3 ~/.claude/hooks/test_echo_worktree_owner.py` passes 76/76 (66/66 before the rework) on a throwaway repo + bare origin (incl. the literal #2331 command). About 40 ms per hook call. Live-verified in a worktree-born session: the main checkout's `settings.local.json` applies to worktree sessions and hot-reloads without restart.

## Decisions
- **No handoff at all (2026-09-25).** Your call: `claim-worktree` was removed ("it is stupid"). Each agent isolates its task in its own worktree off `dev`; continuing a previous agent's work = a new worktree off that agent's worktree. Ownership = `session_id`, not PID: `--resume` keeps it, `/clear` does **not** (new session id, so it branches off the old worktree like any other agent).
- **tmux left as is** (your choice). Optional root-cause fix if handoffs get annoying: bind `-c "#{s|/\.claude/worktrees/[^/]*.*$||:pane_current_path}"` (tested on tmux 3.5a), so new panes open at the repo root and other paths still inherit.
- **Personal first** (`~/.claude/hooks`, absolute path) rather than tracked: it applies to every worktree immediately, whatever branch it's on. Team rollout after the trial.
- **Main checkout = lobby**: no ownership lock (every session starts there), but pinned to `dev`.
- **Legacy worktrees** (unowned, created before the session started) are read-only for every session since 2026-09-25. Before the rework, any session not born inside one could claim it by writing.

## Gotchas
- `$CLAUDE_PROJECT_DIR` in a worktree-born session is the **worktree**, so a hook referenced as `$CLAUDE_PROJECT_DIR/.claude/hooks/...` runs the copy from that worktree's branch. When upstreaming, a tracked hook only takes effect in worktrees whose branch contains it.
- The tracked `worktree-guard.py` main-checkout message still says "or switch to a feature branch", which contradicts pinning (the pin message corrects course). Fix the text when upstreaming.
- The tracked guard's rule (B) blocks Write/Edit to **any** path outside the worktree (memory dir, scratchpad, this vault), hence the Bash/python heredoc workaround. It could be narrowed to "paths inside another checkout of the same repo".
- The parser is heuristic. The read-only allowlist can false-block exotic reads (then: own worktree off it). It's a guardrail against accidents, not a sandbox against an adversarial model.
- Run the hook's own tests / helper commands with `cd /tmp && ...`. Anything non-read-only run from inside a worktree claims it for the current session.

## Pending
- **Trial**: watch for false blocks and friction (post-`/clear` branch-offs; review-then-fix flows). Check `~/.claude/state/claude-owner/errors.log`.
- `claude --worktree <name>` sessions are born inside a worktree created just before them, so they are read-only there (same as before the rework). Add a grace window if that launch mode gets used.
- **25063 worktree** is still checked out on `pr2331`: restore `25063/candidate_selected_placement_status` (user-run; the hook blocks agents from switching).
- **Upstream for the team**:
  - move script + tests into `.claude/hooks/` and register them in tracked `.claude/settings.json` (see the `$CLAUDE_PROJECT_DIR` caveat)
  - make `BASE_REF` / repo scope configurable
  - fix the worktree-guard message
  - document the worktree-per-agent rule in CLAUDE.md
  - Source of truth is `~/.claude/hooks`; the vault copy in `Tooling/worktree-owner-hook/` is a backup snapshot. Re-copy after any edit: `cp ~/.claude/hooks/{echo-worktree-owner.py,test_echo_worktree_owner.py} /Users/gonza56d/taller/repos/echo-obsidian/Tooling/worktree-owner-hook/`
- Optional: the tmux bind rewrite above.

## 2026-09-25 rework
- **Ask**: drop `claim-worktree`; each agent isolates its task in its own worktree off `dev`; an agent asked to change a previous agent's work (A codes + opens the PR, B reviews, B is asked to improve the PR) creates its own worktree with A's commits.
- **Changes**: `UserPromptSubmit` handler + registration removed. The claim rule became "worktree created after the session started" (replaces the born-there check and makes the ~130 unowned legacy worktrees read-only). Block messages print both recipes. `git worktree add` is allowed inside foreign worktrees (target path checked). `EnterWorktree(name)` off a dirty base still blocks, since the base must now be chosen explicitly.
- **Memory**: `feedback_worktree_per_agent.md` (new), `reference_worktree_owner_hook.md` (rewritten), `feedback_no_git_without_asking.md` (task worktree exception).

## Related
- [[Require explicit PR id for pr-review (PR 2332)]]: the no-id `/pr-review` that triggered the incident
- [[Candidate Selected placement status (US 25063)]]: the worktree that got switched mid-task
- [[Candidates Stage filter divergence (Bug 24242)]]: worktree shared by the #2329 review session
