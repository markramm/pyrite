#!/usr/bin/env bash
# Prove a test fails without the fix (review.md checklist; pyrite-dev Iron Law 1).
#
#   scripts/verify-red.sh tests/test_x.py::test_y pyrite/a.py pyrite/b.py
#
# Reverts only the named implementation files to the MERGE BASE with the
# integration branch (origin/dev), runs the test, restores them from HEAD.
# Exit 0 = the test failed without the fix (good). Exit 1 = it passed anyway:
# the test is not testing the fix. Exit 2 = nothing was reverted, so no claim
# can be made (the files are unchanged since the merge base, or dirty).
#
# Why the merge base and not `git stash`: the review lane runs this on
# branches whose fix is already COMMITTED. `git stash push -- <files>` on a
# clean tree saves nothing, exits 0, and the test then runs against the fix --
# twelve "verified" tests on PR #69 had verified nothing (#121). A revert that
# cannot prove it changed the tree is refused.
#
#   VERIFY_RED_BASE    integration ref (default origin/dev, then dev)
#   VERIFY_RED_PYTHON  interpreter (default .venv/bin/python, then python)
set -euo pipefail
test_id="${1:?usage: $0 <pytest node id> <impl file>...}"; shift
[ $# -gt 0 ] || { echo "name the implementation files to revert" >&2; exit 2; }
py="${VERIFY_RED_PYTHON:-.venv/bin/python}"; [ -x "$py" ] || py=python
base="${VERIFY_RED_BASE:-origin/dev}"
git rev-parse --verify -q "$base^{commit}" >/dev/null || base=dev
mb="$(git merge-base "$base" HEAD)"

if ! git diff --quiet -- "$@" || ! git diff --cached --quiet -- "$@"; then
  echo "verify-red: $* have uncommitted changes; commit them first so the revert is unambiguous" >&2
  exit 2
fi

restore() { git checkout -q HEAD -- "$@" 2>/dev/null || true; }
trap 'restore "$@"' EXIT

# Revert each file to its merge-base content; a file that did not exist there is removed.
for f in "$@"; do
  if git cat-file -e "$mb:$f" 2>/dev/null; then
    git checkout -q "$mb" -- "$f"
  else
    rm -f -- "$f"
  fi
done

# `git checkout <rev> -- f` updates the index too, so compare against HEAD, not the index.
if git diff --quiet HEAD -- "$@"; then
  echo "verify-red: $* are identical at the merge base ($mb) -- nothing was reverted, so this proves nothing" >&2
  exit 2
fi

if "$py" -m pytest "$test_id" -q -p no:cacheprovider >/dev/null 2>&1; then
  echo "verify-red: $test_id PASSED without the fix -- it does not test the change" >&2
  exit 1
fi
echo "verify-red: $test_id fails without the fix (as it should)"
