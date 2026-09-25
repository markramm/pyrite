---
id: verify-red-one-owner-for-revert-and-restore
title: "verify-red: one owner for reverting and restoring the implementation"
type: backlog_item
tags:
- quality
- refactor
importance: 5
kind: tech_debt
status: wont_do
priority: medium
effort: M
rank: 0
---

## Superseded 2026-09-25
The maintainer closed this approach (PR #374). The in-place revert-and-restore design is replaced by `test-evidence-diff-coverage-and-red-green-on-a-throwaway-tree`, which never modifies the developer's tree, so there is nothing to restore.

## Problem
Two mechanisms own one invariant: `scripts/verify-red.sh` reverts the implementation files and restores them in an EXIT trap (`git checkout ... || true`), and `scripts/verify_red_ci.py` (the CI driver, #357) runs a second, content-based restore as a fallback. Every disagreement between them is a data-loss or wrong-verdict path: #357 took three fix-at-review rounds, each introducing the next defect (retro 10). #368 lists what is still open: `unittest.mock` patch forms counted as strong reds, a restore that stops at the first refused file, checkout conversion (`eol=crlf`/autocrlf) defeating the byte compare, an interrupt that can strand `.git/index.lock`, index-only state.

## Groom 2026-09-24
**Acceptance**
- Exactly one component reverts and restores. Recommended: the Python driver owns both (reads merge-base content with `git cat-file --filters`, writes the files itself, restores in one `try/finally`, never through `git checkout`), and `verify-red.sh` becomes a thin wrapper that calls it for the single-file local case. The other design is acceptable if the spec's properties hold; say which and why in the report.
- Properties, each pinned by a medium test (a real git repo in tmp, the real scripts):
  1. After any exit (normal, refusal, SIGINT/SIGTERM to the driver, a killed child, a timeout) the implementation files hold exactly their HEAD content and the index is unchanged from before the run.
  2. An edit made before or during the run that is not a file the run reverted is never overwritten.
  3. A restore that cannot complete is reported by file, every file is attempted, and the exit code is non-zero.
  4. Checkout conversion (`*.py text eol=crlf`) and non-UTF-8 files verify and restore correctly.
- Weak-red classification covers `unittest.mock.patch`/`patch.object` misses and `monkeypatch.delattr`, and matches only the exception line, not text embedded in an assertion message.
- Every item in #368 is fixed or explicitly closed with a reason; `tests/test_verify_red_ci.py` and `tests/test_verify_red.py` keep passing (tests may move, none may be deleted without a replacement).
- Each guard: deleting it alone fails a test (pyrite-dev "Guards").

**Touches:** `scripts/verify_red_ci.py`, `scripts/verify-red.sh`, `tests/test_verify_red_ci.py`, `tests/test_verify_red.py`, CONTRIBUTING's verify-red paragraph. **Model:** opus (design). **Heavy:** no. **Cold read:** yes.
**Out of scope:** the CI workflow job shape (stays advisory, `contents: read`), the review.md policy.
**Sequence:** after the lifespan quality theme (retro 9).
