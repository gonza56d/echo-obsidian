#!/usr/bin/env python3
"""Worktree ownership + branch pinning for concurrent Claude Code sessions.

Why: tmux opens splits/windows in the pane's current path, and Claude chdir()s
into its worktree, so a new `claude` started next to a busy session is born
INSIDE that session's worktree. Two sessions then share one working tree and
one branch: one checks out another PR, stashes, commits or runs lint in the
other's tree.

Rules (only for checkouts of the repo the session belongs to):
  1. One agent per linked worktree. The owner is a session_id stored in
     <worktree git dir>/claude-owner.json. A session becomes owner on its first
     write in an unowned worktree created AFTER the session started (by itself
     or its subagents). Worktrees that predate the session belong to earlier
     agents, including the one a tmux split or /clear drops it into. Ownership
     never expires or transfers; everyone else is read-only there. An agent
     that must continue another agent's work creates its own worktree off that
     worktree's commits.
  2. Every checkout is pinned to its branch: git checkout <ref>, git switch and
     gh pr checkout are blocked; so are bare git stash / stash pop / stash clear
     (the stash stack is shared by all worktrees).
  3. EnterWorktree(name=...) is blocked when HEAD has commits that are not on
     origin/dev (worktree.baseRef=head would silently copy them into the new
     branch); the base must then be given explicitly with `git worktree add`.

User-only escape hatch (the model cannot trigger it): launching with
CLAUDE_OWNER_GUARD_OFF=1 disables the hook for that session.

Fail-open: unexpected errors allow the call and are logged to STATE_DIR/errors.log.
Tests: ~/.claude/hooks/test_echo_worktree_owner.py
"""

import datetime
import json
import os
import re
import shlex
import subprocess
import sys
import traceback

STATE_DIR = os.environ.get("CLAUDE_OWNER_STATE_DIR") or os.path.expanduser(
    "~/.claude/state/claude-owner"
)
BIRTHS_DIR = os.path.join(STATE_DIR, "births")
LOCK_NAME = "claude-owner.json"
PROTECTED_MARKER = "claude-owner"
BASE_REF = "origin/dev"
BIRTH_TTL_DAYS = 30

PUNCT = "();<>|&\n"
SHELL_KEYWORDS = {"if", "then", "else", "elif", "fi", "do", "done", "while",
                  "until", "!", "{", "}", "time", "noglob"}
LOOP_HEADERS = {"for", "case", "select", "function"}
WRAPPERS = {"nohup", "command", "builtin", "exec", "nice"}

READ_CMDS = {
    "cat", "head", "tail", "grep", "egrep", "fgrep", "rg", "ag", "ls", "wc",
    "jq", "yq", "echo", "printf", "pwd", "stat", "file", "diff", "cmp",
    "sort", "uniq", "cut", "tr", "basename", "dirname", "realpath",
    "readlink", "which", "type", "date", "true", "false", "test", "[",
    "column", "nl", "comm", "fold", "od", "xxd", "hexdump", "md5", "shasum",
    "sha256sum", "du", "df", "tree", "awk", "gawk", "bat", "fd", "sleep",
    "whoami", "id", "uname", "hostname", "printenv", "ps", "lsof", "pgrep",
    "less", "more", "man", "cd", "export", "unset", "set", "exit", "return",
    "wait",
}
PATH_WRITERS = {"cp", "mv", "rm", "rmdir", "mkdir", "touch", "tee", "ln",
                "install", "rsync", "chmod", "chown", "truncate", "unlink"}
DEST_ONLY_WRITERS = {"cp", "ln", "install", "rsync"}
GIT_READ_SUBS = {
    "status", "log", "diff", "show", "rev-parse", "rev-list", "ls-files",
    "ls-tree", "ls-remote", "fetch", "blame", "grep", "cat-file",
    "merge-base", "describe", "shortlog", "name-rev", "for-each-ref",
    "show-ref", "count-objects", "help", "version", "var", "check-ignore",
    "range-diff", "whatchanged", "cherry", "difftool", "annotate",
}
PY_WRITE_HINTS = (
    "'w'", '"w"', "'a'", '"a"', "'x'", '"x"', "'wb'", '"wb"', "'ab'", '"ab"',
    "w+", "r+", "a+", ".write", "write_text", "write_bytes", "subprocess",
    "os.system", "popen", "remove(", "unlink", "rmtree", "shutil", "rename(",
    "mkdir", "touch(", "exec(", "eval(", "__import__", "chmod", "symlink",
    "truncate", "json.dump(", "to_csv", "savefig", "sqlite3",
)


# --------------------------------------------------------------------------- #
# git / filesystem helpers
# --------------------------------------------------------------------------- #

def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def git(cwd, *args, timeout=5):
    try:
        out = subprocess.run(["git", "-C", cwd, *args], capture_output=True,
                             text=True, timeout=timeout)
    except Exception:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


class Tree:
    def __init__(self, root, git_dir, common_dir):
        self.root = root
        self.git_dir = git_dir
        self.common_dir = common_dir
        self.linked = git_dir != common_dir

    @property
    def lock_path(self):
        return os.path.join(self.git_dir, LOCK_NAME)

    @property
    def main_root(self):
        if os.path.basename(self.common_dir) == ".git":
            return os.path.dirname(self.common_dir)
        return self.common_dir

    def branch(self):
        return git(self.root, "rev-parse", "--abbrev-ref", "HEAD") or "?"

    def head_ref(self):
        """Branch name, or the short sha when detached."""
        branch = self.branch()
        if branch not in ("HEAD", "?"):
            return branch
        return git(self.root, "rev-parse", "--short", "HEAD") or "<sha>"

    def created_at(self):
        try:
            st = os.stat(self.git_dir)
        except OSError:
            return None
        if getattr(st, "st_birthtime", None):
            return st.st_birthtime
        try:
            return os.stat(os.path.join(self.git_dir, "commondir")).st_mtime
        except OSError:
            return None


_TREES = {}


def tree_of(path):
    """Checkout containing `path` (nearest existing dir), or None."""
    if not path:
        return None
    d = os.path.realpath(os.path.expanduser(path))
    while not os.path.isdir(d):
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent
    if d in _TREES:
        return _TREES[d]
    out = git(d, "rev-parse", "--path-format=absolute", "--show-toplevel",
              "--absolute-git-dir", "--git-common-dir")
    tree = None
    if out:
        lines = out.splitlines()
        if len(lines) == 3:
            tree = Tree(*(os.path.realpath(x) for x in lines))
    _TREES[d] = tree
    return tree


# --------------------------------------------------------------------------- #
# ownership state
# --------------------------------------------------------------------------- #

def read_owner(tree):
    try:
        with open(tree.lock_path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return {"session_id": "?unreadable-lock"}


def claim(tree, session_id):
    data = {"session_id": session_id, "branch": tree.branch(),
            "claimed_at": now(), "via": "first-write"}
    try:
        fd = os.open(tree.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(data, indent=2))


def birth_path(session_id):
    return os.path.join(BIRTHS_DIR, re.sub(r"[^A-Za-z0-9_-]", "_", session_id) + ".json")


def ensure_birth(session_id, cwd, source):
    """Record when this session was first seen; later events only refresh the TTL."""
    path = birth_path(session_id)
    if os.path.exists(path):
        if source:
            os.utime(path)
        return
    os.makedirs(BIRTHS_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"cwd": os.path.realpath(cwd), "source": source or "first-tool-call",
                   "at": now(), "ts": datetime.datetime.now().timestamp()}, f)
    cutoff = datetime.datetime.now().timestamp() - BIRTH_TTL_DAYS * 86400
    for name in os.listdir(BIRTHS_DIR):
        p = os.path.join(BIRTHS_DIR, name)
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
        except OSError:
            pass


def birth_ts(session_id):
    try:
        with open(birth_path(session_id)) as f:
            record = json.load(f)
    except Exception:
        return None
    if "ts" in record:
        return record["ts"]
    try:  # records written before `ts` existed
        return datetime.datetime.fromisoformat(record["at"]).timestamp()
    except Exception:
        return None


def ownership(tree, session_id):
    """('mine' | 'claimable' | 'foreign', owner-dict-or-None)."""
    owner = read_owner(tree)
    if owner:
        return ("mine" if owner.get("session_id") == session_id else "foreign"), owner
    born, created = birth_ts(session_id), tree.created_at()
    if born is not None and created is not None and created >= born:
        return "claimable", None
    return "foreign", None


class Ctx:
    def __init__(self, session_id, cwd):
        self.session_id = session_id
        self.cwd = os.path.realpath(cwd)
        home = tree_of(self.cwd)
        self.repo_common = home.common_dir if home else None
        self.pending = {}

    def same_repo(self, tree):
        return tree is not None and tree.common_dir == self.repo_common

    def governs(self, tree):
        return self.same_repo(tree) and tree.linked

    def writable(self, tree):
        state, owner = ownership(tree, self.session_id)
        if state == "claimable":
            self.pending[tree.root] = tree
        return state != "foreign", owner

    def commit_claims(self):
        for tree in self.pending.values():
            claim(tree, self.session_id)


# --------------------------------------------------------------------------- #
# messages
# --------------------------------------------------------------------------- #

def describe_owner(owner):
    if owner:
        return (f"session {str(owner.get('session_id'))[:8]} "
                f"(claimed {owner.get('claimed_at', '?')} via {owner.get('via', '?')}, "
                f"branch {owner.get('branch', '?')})")
    return "nobody, but it predates this session, so it belongs to an earlier agent"


def own_worktree_help(tree):
    main, ref, branch = tree.main_root, tree.head_ref(), tree.branch()
    pr_branch = branch if branch not in ("HEAD", "?") else "<pr-branch>"
    return (
        "Work in a worktree of your own:\n"
        f"- New ticket: branch off {BASE_REF}:\n"
        f"    git -C {main} fetch origin dev && git -C {main} worktree add -b <ticket>/<name> "
        f"{main}/.claude/worktrees/<dir> {BASE_REF}\n"
        "- Continuing this worktree's work (e.g. improving its PR): branch off its commits:\n"
        f"    git -C {main} worktree add -b <new-branch> {main}/.claude/worktrees/<dir> {ref}\n"
        f"  and publish to its PR with `git push origin HEAD:{pr_branch}` (never force; if\n"
        f"  rejected, fetch and rebase onto origin/{pr_branch}). Uncommitted changes here do\n"
        f"  not carry over; copy them with `git -C {tree.root} diff | git apply`.\n"
        "Then EnterWorktree(path=<that dir>)."
    )


def foreign_msg(tree, owner, what):
    return (
        f"BLOCKED by worktree-owner: {what}\n"
        f"  worktree: {tree.root}\n"
        f"  owner:    {describe_owner(owner)}\n"
        "This worktree is another agent's and READ-ONLY for this session (reading files,\n"
        "git log/diff/show, gh pr view/diff/comment/review all work; edits, commits, tests,\n"
        "lint do not). Ownership never transfers: never edit the lock file or route around\n"
        "this hook.\n"
        + own_worktree_help(tree)
    )


def pin_msg(tree, cmd):
    main = tree.main_root
    return (
        f"BLOCKED by worktree-owner: `{cmd}` would switch the branch of\n  {tree.root}\n"
        "Every checkout is pinned to its branch: other Claude sessions may be working in\n"
        "this tree (new tmux panes start inside the neighbour's worktree).\n"
        "- Rename a fresh worktree-* branch: git branch -m <ticket>/<name>\n"
        "- Discard file changes: git restore <path>   (or git checkout -- <path>)\n"
        "- Review another PR read-only: gh pr diff <N> / gh pr view <N>; for a runnable tree:\n"
        f"    git -C {main} fetch origin pull/<N>/head && "
        f"git -C {main} worktree add --detach {main}/.claude/worktrees/pr-<N> FETCH_HEAD\n"
        "- Another ticket, or continuing another branch's work: a worktree of your own\n"
        f"    git -C {main} worktree add -b <new-branch> {main}/.claude/worktrees/<dir> "
        f"<{BASE_REF} | that branch>\n"
        "  then EnterWorktree(path=<that dir>).\n"
        "If the user explicitly wants this switch, ask them to run it themselves."
    )


STASH_MSG = (
    "BLOCKED by worktree-owner: bare `git stash` / `stash pop` / `stash clear` act on a\n"
    "stash stack shared by every worktree and session; you could pop or wipe another\n"
    "session's work. Use a WIP commit, or `git stash push -u -m <unique-tag>`, capture its\n"
    "sha (`git stash list --format='%H %gs'`) and restore with `git stash apply <sha>`."
)

LOCK_MSG = (
    "BLOCKED by worktree-owner: worktree ownership files (claude-owner*) are managed by\n"
    "the hook alone and ownership never transfers. To continue another agent's work, create\n"
    "your own worktree off its commits (git worktree add -b <new-branch> <dir> <its branch>)."
)


# --------------------------------------------------------------------------- #
# bash parsing
# --------------------------------------------------------------------------- #

HEREDOC_RE = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def strip_heredocs(cmd):
    """Drop heredoc bodies: their text is data, not commands."""
    kept, pending = [], []
    for line in cmd.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        kept.append(line)
        pending.extend(m.group(2) for m in HEREDOC_RE.finditer(line))
    return "\n".join(kept)


def extract_substitutions(s):
    """Replace $(...) and `...` with a placeholder; return (outer, [inner commands])."""
    out, inners = [], []
    i, n = 0, len(s)
    in_single = in_double = False
    while i < n:
        c = s[i]
        if in_single:
            out.append(c)
            in_single = c != "'"
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            out.append(s[i:i + 2])
            i += 2
            continue
        if c == "'" and not in_double:
            in_single = True
        elif c == '"':
            in_double = not in_double
        elif c == "$" and s[i + 1:i + 2] == "(":
            arithmetic = s[i + 2:i + 3] == "("
            depth, j = 1, i + 2
            while j < n and depth:
                if s[j] == "(":
                    depth += 1
                elif s[j] == ")":
                    depth -= 1
                j += 1
            if not arithmetic:
                inners.append(s[i + 2:j - 1])
            out.append("__SUBST__")
            i = j
            continue
        elif c == "`":
            j = s.find("`", i + 1)
            j = n if j == -1 else j
            inners.append(s[i + 1:j])
            out.append("__SUBST__")
            i = j + 1
            continue
        out.append(c)
        i += 1
    return "".join(out), inners


def tokenize(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=PUNCT)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    return list(lex)


def is_op(tok):
    return bool(tok) and all(ch in PUNCT for ch in tok)


def op_kind(tok):
    if ">" in tok:
        return "out"
    if "<" in tok:
        return "in"
    return "sep"


def split_segments(tokens):
    segs, cur = [], []
    for t in tokens:
        if is_op(t) and op_kind(t) == "sep":
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def parse_segment(tokens):
    """-> (words, output redirect targets)."""
    words, outs, i = [], [], 0
    while i < len(tokens):
        t = tokens[i]
        if is_op(t):
            target = tokens[i + 1] if i + 1 < len(tokens) else None
            if words and words[-1].isdigit():
                words.pop()  # fd number: `2>` / `2>&1`
            if op_kind(t) == "out" and target is not None:
                fd_dup = t in (">&", "<&") and (target.isdigit() or target == "-")
                if not fd_dup:
                    outs.append(target)
            i += 2
            continue
        words.append(t)
        i += 1
    return words, outs


def strip_prefix(words):
    """Drop env assignments, shell keywords and wrappers in front of the command."""
    i = 0
    while i < len(words):
        w = words[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w) or w in SHELL_KEYWORDS or w in WRAPPERS:
            i += 1
        elif w in ("timeout", "gtimeout"):
            i += 1
            while i < len(words) and words[i].startswith("-"):
                i += 1
            i += 1  # duration
        elif w == "env":
            i += 1
            while i < len(words) and (words[i].startswith("-") or "=" in words[i]):
                i += 1
        else:
            break
    return words[i:]


def resolve(p, base):
    if not p or p.startswith("$") or p == "__SUBST__" or p == "-":
        return None
    p = os.path.expanduser(p)
    if not os.path.isabs(p):
        p = os.path.join(base, p)
    return os.path.realpath(p)


def parse_git(words):
    """-> (list of -C dirs, subcommand, args)."""
    c_dirs, i = [], 1
    while i < len(words):
        w = words[i]
        if w == "-C" and i + 1 < len(words):
            c_dirs.append(words[i + 1])
            i += 2
        elif w in ("-c", "--git-dir", "--work-tree", "--namespace") and i + 1 < len(words):
            i += 2
        elif w.startswith("-"):
            i += 1
        else:
            break
    sub = words[i] if i < len(words) else None
    return c_dirs, sub, words[i + 1:]


def has_stash_message(args):
    return any(a in ("-m", "--message") or a.startswith("--message=")
               or (a.startswith("-m") and len(a) > 2) for a in args)


def git_pin_violation(sub, args):
    if sub == "switch":
        return "branch"
    if sub == "checkout":
        if "--" in args or any(a in ("-p", "--patch") for a in args):
            return None
        return "branch"
    if sub == "stash":
        if not args:
            return "stash"
        a0 = args[0]
        if a0 in ("pop", "clear"):
            return "stash"
        if a0 == "save":
            return None if any(not a.startswith("-") for a in args[1:]) or has_stash_message(args) else "stash"
        if a0 == "push" or a0.startswith("-"):
            return None if has_stash_message(args) else "stash"
    return None


def git_is_readonly(sub, args):
    if sub is None or sub in GIT_READ_SUBS:
        return True
    first = args[0] if args else None
    if sub == "reflog":
        return first in (None, "show") or (first or "").startswith("-")
    if sub == "remote":
        return first in (None, "-v", "show", "get-url")
    if sub == "config":
        return any(a.startswith("--get") or a in ("--list", "-l") for a in args)
    if sub == "worktree":
        return first in ("list", "add")  # add only writes the new dir, checked as a target
    if sub == "stash":
        return first in ("list", "show")
    if sub == "tag":
        return not args or first in ("-l", "--list")
    if sub == "notes":
        return first in ("show", "list")
    if sub == "branch":
        listing = {"--show-current", "-a", "-r", "-v", "-vv", "--list", "-l",
                   "--all", "--remotes", "--no-color", "--color"}
        valued = {"--contains", "--no-contains", "--merged", "--no-merged",
                  "--points-at", "--sort", "--format"}
        i = 0
        while i < len(args):
            a = args[i]
            if a in valued:
                i += 2
                continue
            if a in listing or (a.startswith("--") and "=" in a
                                and a.split("=")[0] in valued):
                i += 1
                continue
            return False
        return True
    return False


def worktree_add_path(args):
    i = 1
    while i < len(args):
        a = args[i]
        if a in ("-b", "-B", "--reason"):
            i += 2
        elif a.startswith("-"):
            i += 1
        else:
            return a
    return None


def gh_is_readonly(words):
    return not any(w in ("checkout", "clone", "download") for w in words[1:3])


def python_is_readonly(words):
    if "-m" in words:
        return words[words.index("-m") + 1:words.index("-m") + 2] == ["json.tool"]
    if "-c" not in words:
        return False
    code = (words[words.index("-c") + 1] if words.index("-c") + 1 < len(words) else "").lower()
    return not any(h in code for h in PY_WRITE_HINTS)


def curl_targets(words):
    """Output files of curl, or None when it writes to an unknown name (-O)."""
    targets = []
    for i, w in enumerate(words[1:], 1):
        if w in ("-O", "--remote-name", "--remote-name-all") or (
                w.startswith("-") and not w.startswith("--") and "O" in w):
            return None
        if w in ("-o", "--output") and i + 1 < len(words):
            targets.append(words[i + 1])
        elif w.startswith("--output="):
            targets.append(w.split("=", 1)[1])
    return targets


def writer_targets(cmd, args):
    paths = [a for a in args if not a.startswith("-")]
    if cmd in ("chmod", "chown") and paths:
        paths = paths[1:]
    if cmd in DEST_ONLY_WRITERS:
        return paths[-1:]
    return paths


def segment_is_readonly(cmd, words):
    if cmd in READ_CMDS or cmd in PATH_WRITERS or cmd == "__SUBST__":
        return True
    if cmd == "sed":
        return not any(w.startswith("--in-place") or re.match(r"^-[a-zA-Z]*i", w)
                       for w in words[1:])
    if cmd == "find":
        return not any(w in ("-delete", "-exec", "-execdir", "-ok", "-okdir",
                             "-fprint", "-fprintf", "-fls") for w in words)
    if cmd == "gh":
        return gh_is_readonly(words)
    if cmd == "curl":
        return curl_targets(words) is not None
    if cmd in ("python", "python3"):
        return python_is_readonly(words)
    return False


def analyze(command, eff_dir, ctx, problems, depth=0):
    if depth > 5:
        return
    outer, inners = extract_substitutions(strip_heredocs(command))
    for inner in inners:
        analyze(inner, eff_dir, ctx, problems, depth + 1)
    for seg in split_segments(tokenize(outer)):
        words, outs = parse_segment(seg)
        eff_dir = check_segment(strip_prefix(words), outs, eff_dir, ctx, problems, depth)


def check_segment(words, outs, eff_dir, ctx, problems, depth):
    if words and words[0] in LOOP_HEADERS:
        return eff_dir
    raw = " ".join(words)
    cmd = os.path.basename(words[0]) if words else ""
    if any(PROTECTED_MARKER in o for o in outs) or (
            PROTECTED_MARKER in raw and cmd not in READ_CMDS):
        problems.append(LOCK_MSG)
        return eff_dir

    if cmd == "cd":
        target = words[1] if len(words) > 1 else "~"
        return resolve(target, eff_dir) or eff_dir
    if cmd in ("bash", "sh", "zsh") and "-c" in words:
        idx = words.index("-c") + 1
        if idx < len(words):
            analyze(words[idx], eff_dir, ctx, problems, depth + 1)
        return eff_dir

    work_dir, write_targets = eff_dir, list(outs)
    if cmd == "git":
        c_dirs, sub, args = parse_git(words)
        for c in c_dirs:
            work_dir = resolve(c, work_dir) or work_dir
        tree = tree_of(work_dir)
        if ctx.same_repo(tree):
            pin = git_pin_violation(sub, args)
            if pin == "stash":
                problems.append(STASH_MSG)
                return eff_dir
            if pin:
                problems.append(pin_msg(tree, raw))
                return eff_dir
        if sub == "worktree" and args[:1] in (["remove"], ["move"]):
            write_targets += [a for a in args[1:] if not a.startswith("-")][:1]
        if sub == "worktree" and args[:1] == ["add"]:
            write_targets += [p for p in [worktree_add_path(args)] if p]
        readonly = git_is_readonly(sub, args)
    else:
        tree = tree_of(work_dir)
        if cmd == "gh" and words[1:3] == ["pr", "checkout"] and ctx.same_repo(tree):
            problems.append(pin_msg(tree, raw))
            return eff_dir
        if cmd in PATH_WRITERS:
            write_targets += writer_targets(cmd, words[1:])
        if cmd == "sed" and not segment_is_readonly(cmd, words):
            write_targets += [w for w in words[2:] if not w.startswith("-")]
        if cmd == "curl":
            write_targets += curl_targets(words) or []
        readonly = segment_is_readonly(cmd, words) if words else True

    for t in write_targets:
        path = resolve(t, work_dir)
        target_tree = tree_of(path) if path and not path.startswith("/dev/") else None
        if ctx.governs(target_tree):
            ok, owner = ctx.writable(target_tree)
            if not ok:
                problems.append(foreign_msg(target_tree, owner, f"`{raw}` writes into {path}"))
                return eff_dir

    if ctx.governs(tree) and not readonly:
        ok, owner = ctx.writable(tree)
        if not ok:
            problems.append(foreign_msg(tree, owner, f"`{raw}` would modify this worktree"))
    return eff_dir


PIN_FALLBACK_RE = re.compile(
    r"\bgit\b[^;&|\n]*\b(switch|checkout)\b(?![^;&|\n]*\s--(\s|$))|\bgh\s+pr\s+checkout\b")


def check_bash(command, ctx):
    problems = []
    try:
        analyze(command, ctx.cwd, ctx, problems)
    except ValueError:  # unbalanced quotes etc.
        tree = tree_of(ctx.cwd)
        if PIN_FALLBACK_RE.search(command) and ctx.same_repo(tree):
            return pin_msg(tree, command.strip()[:120])
        if ctx.governs(tree):
            ok, owner = ctx.writable(tree)
            if not ok:
                return foreign_msg(tree, owner, "command could not be parsed, so it is treated as a write")
        return None
    return problems[0] if problems else None


# --------------------------------------------------------------------------- #
# event handlers
# --------------------------------------------------------------------------- #

def check_file_write(tool_input, ctx):
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path:
        return None
    if PROTECTED_MARKER in os.path.basename(path):
        return LOCK_MSG
    tree = tree_of(os.path.dirname(os.path.realpath(path)))
    if not ctx.governs(tree):
        return None
    ok, owner = ctx.writable(tree)
    return None if ok else foreign_msg(tree, owner, f"editing {path}")


def check_enter_worktree(tool_input, ctx):
    if tool_input.get("path"):
        return None
    tree = tree_of(ctx.cwd)
    if tree is None:
        return None
    git(tree.root, "fetch", "--quiet", "origin", BASE_REF.split("/", 1)[1], timeout=20)
    ahead = git(tree.root, "rev-list", "--count", f"{BASE_REF}..HEAD")
    if not ahead or int(ahead) == 0:
        return None
    return (
        f"BLOCKED by worktree-owner: HEAD of {tree.root} ({tree.branch()}) has {ahead}\n"
        f"commit(s) that are not on {BASE_REF}. With worktree.baseRef=head the new worktree\n"
        "would silently start from them, so choose the base explicitly.\n"
        + own_worktree_help(tree)
    )


def on_pre_tool(data, ctx):
    tool = data.get("tool_name")
    tool_input = data.get("tool_input") or {}
    if tool == "EnterWorktree":
        msg = check_enter_worktree(tool_input, ctx)
    elif tool in ("Edit", "Write", "NotebookEdit"):
        msg = check_file_write(tool_input, ctx)
    elif tool == "Bash":
        msg = check_bash(tool_input.get("command") or "", ctx)
    else:
        msg = None
    if msg:
        sys.stderr.write(msg + "\n")
        return 2
    ctx.commit_claims()
    return 0


def on_session_start(data, ctx):
    tree = tree_of(ctx.cwd)
    if not ctx.governs(tree):
        return 0
    state, owner = ownership(tree, ctx.session_id)
    if state == "mine":
        return 0
    if state == "claimable":
        print(f"[worktree-owner] This session is inside the worktree {tree.root} "
              f"(branch {tree.branch()}), created after it started. Nobody owns it yet; "
              "the first write claims it.")
        return 0
    print(
        f"[worktree-owner] This session STARTED inside the worktree {tree.root} "
        f"(branch {tree.branch()}); owner: {describe_owner(owner)}.\n"
        "It is READ-ONLY for this session: reading, git log/diff/show and gh pr view/diff/"
        "comment/review work; edits, commits, tests, lint and branch switches are blocked.\n"
        + own_worktree_help(tree)
    )
    return 0


def main():
    if os.environ.get("CLAUDE_OWNER_GUARD_OFF") == "1":
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        event = data.get("hook_event_name")
        session_id = data.get("session_id") or ""
        cwd = data.get("cwd") or os.getcwd()
        if session_id:
            ensure_birth(session_id, cwd, data.get("source") if event == "SessionStart" else None)
        ctx = Ctx(session_id, cwd)
        if ctx.repo_common is None:
            return 0
        handler = {"PreToolUse": on_pre_tool,
                   "SessionStart": on_session_start}.get(event)
        return handler(data, ctx) if handler else 0
    except Exception:
        try:
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(os.path.join(STATE_DIR, "errors.log"), "a") as f:
                f.write(f"--- {now()}\n{traceback.format_exc()}\n")
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
