#!/usr/bin/env python3
"""Scenario tests for echo-worktree-owner.py against a throwaway repo.

Run: python3 ~/.claude/hooks/test_echo_worktree_owner.py
"""

import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "echo-worktree-owner.py")
TMP = os.path.realpath(tempfile.mkdtemp(prefix="owner-hook-"))
STATE = os.path.join(TMP, "state")
REMOTE = os.path.join(TMP, "remote.git")
REPO = os.path.join(TMP, "repo")
WT_A = os.path.join(REPO, ".claude", "worktrees", "A")
WT_B = os.path.join(REPO, ".claude", "worktrees", "B")
WT_C = os.path.join(REPO, ".claude", "worktrees", "C")
OTHER = os.path.join(TMP, "other-repo")
OUTSIDE = os.path.join(TMP, "scratch")

results = []


def sh(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def setup():
    os.makedirs(OUTSIDE)
    sh("git", "init", "-q", "--bare", REMOTE)
    sh("git", "init", "-q", "-b", "dev", REPO)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        sh("git", "-C", REPO, "config", k, v)
    open(os.path.join(REPO, "f.txt"), "w").write("x\n")
    sh("git", "-C", REPO, "add", ".")
    sh("git", "-C", REPO, "commit", "-qm", "init")
    sh("git", "-C", REPO, "remote", "add", "origin", REMOTE)
    sh("git", "-C", REPO, "push", "-q", "origin", "dev")
    sh("git", "-C", REPO, "fetch", "-q", "origin")
    sh("git", "-C", REPO, "worktree", "add", "-q", "-b", "A/x", WT_A, "origin/dev")
    sh("git", "-C", REPO, "worktree", "add", "-q", "-b", "B/y", WT_B, "origin/dev")
    sh("git", "-C", REPO, "worktree", "add", "-q", "-b", "C/z", WT_C, "origin/dev")
    open(os.path.join(WT_A, "a.txt"), "w").write("a\n")
    sh("git", "-C", WT_A, "add", ".")
    sh("git", "-C", WT_A, "commit", "-qm", "ticket A work")
    sh("git", "init", "-q", "-b", "main", OTHER)


def hook(payload, env_extra=None):
    env = dict(os.environ, CLAUDE_OWNER_STATE_DIR=STATE)
    env.pop("CLAUDE_OWNER_GUARD_OFF", None)
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def start(sid, cwd, source="startup"):
    return hook({"hook_event_name": "SessionStart", "session_id": sid,
                 "cwd": cwd, "source": source})


def bash(sid, cwd, command, **kw):
    return hook({"hook_event_name": "PreToolUse", "session_id": sid, "cwd": cwd,
                 "tool_name": "Bash", "tool_input": {"command": command}}, **kw)


def write(sid, cwd, path):
    return hook({"hook_event_name": "PreToolUse", "session_id": sid, "cwd": cwd,
                 "tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}})


def enter(sid, cwd, **tool_input):
    return hook({"hook_event_name": "PreToolUse", "session_id": sid, "cwd": cwd,
                 "tool_name": "EnterWorktree", "tool_input": tool_input})


def prompt(sid, cwd, text):
    return hook({"hook_event_name": "UserPromptSubmit", "session_id": sid,
                 "cwd": cwd, "prompt": text})


def owner_of(wt):
    name = os.path.basename(wt)
    try:
        with open(os.path.join(REPO, ".git", "worktrees", name, "claude-owner.json")) as f:
            return json.load(f)["session_id"]
    except FileNotFoundError:
        return None


def expect(name, result, allowed, contains=None):
    code, out, err = result
    ok = (code == 0) == allowed and (contains is None or contains in (out + err))
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"      exit={code}\n      stdout={out.strip()[:400]}\n      stderr={err.strip()[:600]}")


def check(name, cond):
    results.append(cond)
    print(f"{'PASS' if cond else 'FAIL'}  {name}")


def main():
    setup()
    s1, s2, s3 = "sess-one-1111", "sess-two-2222", "sess-three-3333"

    # --- ownership -----------------------------------------------------------
    expect("s1 born in main: no context", start(s1, REPO), True)
    expect("s1 first write in unowned A (not born there) is allowed",
           bash(s1, WT_A, "echo hi > notes.txt"), True)
    check("s1 now owns A", owner_of(WT_A) == s1)

    expect("s2 born inside A gets a READ-ONLY notice", start(s2, WT_A), True, "READ-ONLY")
    expect("s2 read-only git/gh pipeline allowed",
           bash(s2, WT_A, "git log --oneline | head -3 && gh pr diff 12 2>&1 | head"), True)
    expect("s2 review file in scratch via heredoc allowed (body mentions checkout)",
           bash(s2, WT_A, f"cat > {OUTSIDE}/review.md <<'EOF'\nrun git checkout foo\nEOF\n"
                          "gh pr comment 12 --body-file " + f"{OUTSIDE}/review.md"), True)
    expect("s2 python -c json reader allowed",
           bash(s2, WT_A, "gh pr view 1 --json x | python3 -c \"import json,sys; print(json.load(sys.stdin))\""),
           True)
    expect("s2 python -c writer blocked",
           bash(s2, WT_A, "python3 -c \"open('z','w').write('x')\""), False, "READ-ONLY")
    expect("s2 lint blocked", bash(s2, WT_A, "./scripts/lint.sh"), False, "owner:    session sess-one")
    expect("s2 sed -i blocked", bash(s2, WT_A, "sed -i '' 's/a/b/' f.txt"), False)
    expect("s2 sed -n allowed", bash(s2, WT_A, "sed -n '1,5p' f.txt"), True)
    expect("s2 redirect into A blocked", bash(s2, WT_A, "echo x > f.txt"), False)
    expect("s2 git commit blocked", bash(s2, WT_A, "git commit -am wip"), False)
    expect("s2 Write into A blocked", write(s2, WT_A, os.path.join(WT_A, "f.txt")), False, "claim-worktree")
    expect("s2 Write outside repo allowed", write(s2, WT_A, os.path.join(OUTSIDE, "n.md")), True)
    expect("s2 cd main && git log allowed", bash(s2, WT_A, f"cd {REPO} && git log -1"), True)
    expect("s1 Write into own A allowed", write(s1, REPO, os.path.join(WT_A, "f.txt")), True)

    # --- pinning (applies to owners too) ---------------------------------------
    expect("owner git checkout <branch> blocked", bash(s1, WT_A, "git checkout B/y"), False, "pinned")
    expect("the 2331 incident command blocked",
           bash(s2, WT_A, f"cd {WT_A} && git fetch origin pull/2331/head:pr2331 -q; git checkout pr2331 -q"),
           False, "pinned")
    expect("owner git switch -c blocked", bash(s1, WT_A, "git switch -c other"), False, "branch -m")
    expect("owner checkout -b blocked", bash(s1, WT_A, "git checkout -b other"), False)
    expect("gh pr checkout blocked", bash(s1, WT_A, "gh pr checkout 12"), False)
    expect("main checkout switch blocked", bash(s3, REPO, "git checkout A/x"), False)
    expect("git -C <wt> checkout from main blocked", bash(s3, REPO, f"git -C {WT_A} checkout dev"), False)
    expect("nested bash -c checkout blocked", bash(s1, WT_A, "bash -c 'git checkout dev'"), False)
    expect("$(git switch) substitution blocked", bash(s1, WT_A, "echo $(git switch dev)"), False)
    expect("checkout -- <path> allowed for owner", bash(s1, WT_A, "git checkout -- f.txt"), True)
    expect("git restore allowed for owner", bash(s1, WT_A, "git restore f.txt"), True)
    expect("git branch -m allowed for owner", bash(s1, WT_A, "git branch -m A/renamed"), True)
    expect("commit message mentioning checkout allowed",
           bash(s1, WT_A, "git commit -m 'do not git checkout here'"), True)
    expect("bare git stash blocked", bash(s1, WT_A, "git stash"), False, "stash")
    expect("git stash -u blocked", bash(s1, WT_A, "git stash -u"), False)
    expect("git stash pop blocked", bash(s1, WT_A, "git stash pop"), False)
    expect("git stash clear blocked", bash(s1, WT_A, "git stash clear"), False)
    expect("git stash push -u -m tag allowed", bash(s1, WT_A, "git stash push -u -m tag-123"), True)
    expect("git stash apply <sha> allowed", bash(s1, WT_A, "git stash apply abc123"), True)
    expect("worktree add from main allowed",
           bash(s2, WT_A, f"git -C {REPO} worktree add -b D/w {REPO}/.claude/worktrees/D origin/dev"), True)

    # --- cross-tree writes ---------------------------------------------------------
    expect("rm -rf into A (owned by s1) from main blocked for s3",
           bash(s3, REPO, "rm -rf .claude/worktrees/A/app"), False)
    expect("git worktree remove A blocked for s3",
           bash(s3, REPO, "git worktree remove .claude/worktrees/A"), False)
    expect("lock file tamper blocked",
           bash(s1, REPO, "rm .git/worktrees/A/claude-owner.json"), False, "claim-worktree")
    expect("lock file read allowed", bash(s1, REPO, "cat .git/worktrees/A/claude-owner.json"), True)
    expect("Write to lock file blocked",
           write(s1, REPO, os.path.join(REPO, ".git", "worktrees", "A", "claude-owner.json")), False)

    # --- claim-worktree (user-only handoff) ------------------------------------------
    expect("other prompts untouched", prompt(s2, WT_A, "fix the nits"), True)
    check("...and ownership unchanged", owner_of(WT_A) == s1)
    code, out, _ = prompt(s2, WT_A, "claim-worktree")
    check("claim-worktree returns context", code == 0 and "now OWNS" in out)
    check("s2 now owns A", owner_of(WT_A) == s2)
    expect("s2 can write after claim", write(s2, WT_A, os.path.join(WT_A, "f.txt")), True)
    expect("former owner s1 is now read-only", write(s1, WT_A, os.path.join(WT_A, "f.txt")), False,
           "sess-two")
    code, out, _ = prompt(s3, REPO, "claim-worktree")
    check("claim-worktree in main checkout is a no-op", code == 0 and "nothing claimed" in out)

    # --- born inside an unowned worktree -----------------------------------------------
    start(s3, WT_B)
    expect("s3 born in unowned B cannot adopt it", bash(s3, WT_B, "touch x"), False, "STARTED inside")
    check("B still unowned", owner_of(WT_B) is None)
    expect("s1 (born elsewhere) claims B on first write", bash(s1, WT_B, "touch x"), True)
    check("s1 owns B", owner_of(WT_B) == s1)
    expect("blocked command does not claim", bash("sess-four", REPO, "echo > .claude/worktrees/C/x; git switch dev"),
           False)
    check("C still unowned after blocked command", owner_of(WT_C) is None)

    # --- /clear and resume ---------------------------------------------------------------
    start("sess-two-cleared", WT_A, source="clear")
    expect("after /clear the new session id is read-only in A",
           write("sess-two-cleared", WT_A, os.path.join(WT_A, "f.txt")), False)
    start(s2, WT_B, source="resume")
    expect("resume keeps birth record (s2 still owner of A)", write(s2, WT_A, os.path.join(WT_A, "f.txt")), True)

    # --- EnterWorktree clean base -----------------------------------------------------------
    expect("EnterWorktree(name) from A (ahead of origin/dev) blocked", enter(s2, WT_A, name="new"), False,
           "not on origin/dev")
    expect("EnterWorktree(name) from main on dev allowed", enter(s2, REPO, name="new"), True)
    expect("EnterWorktree(path) allowed", enter(s2, WT_A, path=WT_B), True)

    # --- scope / escape hatches ----------------------------------------------------------------
    expect("other repo (git -C) untouched", bash(s2, REPO, f"git -C {OTHER} checkout -b whatever"), True)
    expect("cwd outside any repo untouched", bash(s2, OUTSIDE, "git checkout x"), True)
    expect("CLAUDE_OWNER_GUARD_OFF=1 disables", bash(s2, WT_A, "git switch dev",
                                                     env_extra={"CLAUDE_OWNER_GUARD_OFF": "1"}), True)
    expect("unparseable command in foreign tree blocked", bash(s1, WT_A, "echo 'unbalanced"), False)
    expect("unparseable pin command blocked", bash(s2, WT_A, "git checkout dev 'oops"), False)

    errors = os.path.join(STATE, "errors.log")
    check("no hook exceptions logged", not os.path.exists(errors))
    if os.path.exists(errors):
        print(open(errors).read())

    subprocess.run(["rm", "-rf", TMP])
    print(f"\n{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
