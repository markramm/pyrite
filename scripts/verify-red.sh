#!/usr/bin/env bash
# Prove a test fails without the fix (review.md checklist; pyrite-dev Iron Law 1).
#
#   scripts/verify-red.sh tests/test_x.py::test_y pyrite/a.py pyrite/b.py
#
# Stashes only the named implementation files, runs the test, restores them.
# Exit 0 = the test failed without the fix (good). Exit 1 = it passed anyway:
# the test is not testing the fix.
set -euo pipefail
test_id="${1:?usage: $0 <pytest node id> <impl file>...}"; shift
[ $# -gt 0 ] || { echo "name the implementation files to stash" >&2; exit 2; }
py=.venv/bin/python; [ -x "$py" ] || py=python
git stash push -q -- "$@"
trap 'git stash pop -q' EXIT
if "$py" -m pytest "$test_id" -q -p no:cacheprovider >/dev/null 2>&1; then
  echo "verify-red: $test_id PASSED without the fix -- it does not test the change" >&2
  exit 1
fi
echo "verify-red: $test_id fails without the fix (as it should)"
