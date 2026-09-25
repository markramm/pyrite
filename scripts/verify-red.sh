#!/usr/bin/env bash
# Prove a test fails without the fix (review.md checklist; pyrite-dev Iron Law 1).
#
#   scripts/verify-red.sh tests/test_x.py::test_y pyrite/a.py pyrite/b.py
#
# Reverts only the named implementation files to the MERGE BASE with the
# integration branch (origin/dev), runs the test, puts the files back.
# Exit 0 = the test failed without the fix (good). Exit 1 = it passed anyway:
# the test is not testing the fix. Exit 2 = no claim can be made: nothing was
# reverted (the files are unchanged since the merge base), they have
# uncommitted changes, the interpreter imports another tree (#189), pytest
# found no such test, or a file could not be put back (each one is named).
#
# A thin wrapper: scripts/verify_red_ci.py --test does the work, and is the
# only thing that reverts and restores (retro 10, #368). It writes the files
# itself -- never `git checkout`, so the index is not touched -- and restores
# them in one `finally`, after a verdict, a refusal, Ctrl-C or SIGTERM alike.
#
# Why the merge base and not `git stash`: the review lane runs this on
# branches whose fix is already COMMITTED. `git stash push -- <files>` on a
# clean tree saves nothing, exits 0, and the test then runs against the fix --
# twelve "verified" tests on PR #69 had verified nothing (#121).
#
#   VERIFY_RED_BASE    integration ref (default origin/dev, then dev)
#   VERIFY_RED_PYTHON  interpreter (default .venv/bin/python, then python)
set -euo pipefail
test_id="${1:?usage: $0 <pytest node id> <impl file>...}"; shift
[ $# -gt 0 ] || { echo "name the implementation files to revert" >&2; exit 2; }
py="${VERIFY_RED_PYTHON:-.venv/bin/python}"; [ -x "$py" ] || py=python
# exec: Ctrl-C and SIGTERM reach the driver itself, which restores the tree.
exec "$py" "$(dirname "$0")/verify_red_ci.py" --python "$py" --test "$test_id" -- "$@"
