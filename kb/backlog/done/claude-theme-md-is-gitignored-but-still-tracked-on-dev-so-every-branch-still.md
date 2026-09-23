---
id: claude-theme-md-is-gitignored-but-still-tracked-on-dev-so-every-branch-still
title: .claude/THEME.md is gitignored but still tracked on dev, so every branch still carries it
type: backlog_item
tags:
- process
importance: 5
status: done
priority: medium
rank: 0
---

Follow-up to #106. `.gitignore:89` lists `.claude/THEME.md`, which prevents *new* adds, but the file committed in 22619c9 was never `git rm --cached`d. `git ls-tree origin/dev .claude/THEME.md` still returns a blob, so every branch cut from `dev` inherits it and the add/add conflicts #106 describes can still occur between branches that modify it.

Fix is one commit on a `kb/` or `fix/` branch: `git rm --cached .claude/THEME.md`. Noting it rather than doing it inline because it belongs to no theme in flight and would be noise on #69.

Found in tick 5 while checking #106 compliance on PR #69 — the file is present on that branch, but it is inherited from `dev`, not introduced by the worker.

## Triage 2026-09-20 (from GitHub)

**State: still open for a reason — leave open.** (`process` issue; verified, not rewritten.)

Re-checked on `dev` @130f433:

```
$ git ls-tree origin/dev .claude/THEME.md
100644 blob 54224ca45cecd878dfbc72812bb94efc2a461a9b	.claude/THEME.md
$ grep -n THEME .gitignore
101:.claude/THEME.md
```

Exactly the state this issue describes: the ignore rule is in place (so it can never be *re-*added), and the already-tracked blob is still there, so every branch cut from `dev` still inherits it and can still produce the add/add conflict #107 describes.

The fix is unchanged and is one line — `git rm --cached .claude/THEME.md` — riding on the next change that has any reason to touch `.claude/`. It needs no theme of its own and should not get one.


_Migrated from GitHub issue #122 on 2026-09-20 (maintainer: process findings live in the KB)._

## Done 2026-09-23 (retro 8)

Fixed by #206 (merged 2026-09-20); verified on dev at 6e505be. Left `proposed` for three days because nothing moves a KB item when the PR that fixes it merges.
