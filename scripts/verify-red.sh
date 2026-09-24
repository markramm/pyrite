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
# A review worktree whose .venv is a SYMLINK to another checkout's (instead
# of one built by scripts/new-worktree.sh) resolves every extension package
# -- and sometimes pyrite itself -- to an editable install pointing at that
# OTHER checkout, not this worktree. The interpreter then runs real tests
# against the wrong code and reports a suite number that proves nothing
# (#189). For each reverted production file, resolve its top-level package
# and refuse (exit 2) unless the interpreter's import of that package
# resolves under this worktree.
#
#   VERIFY_RED_BASE    integration ref (default origin/dev, then dev)
#   VERIFY_RED_PYTHON  interpreter (default .venv/bin/python, then python)
#   VERIFY_RED_JUNITXML  also write the reverted run's per-test JUnit report
#                        here (scripts/verify_red_ci.py, the CI job, reads it)
set -euo pipefail
test_id="${1:?usage: $0 <pytest node id> <impl file>...}"; shift
[ $# -gt 0 ] || { echo "name the implementation files to revert" >&2; exit 2; }
py="${VERIFY_RED_PYTHON:-.venv/bin/python}"; [ -x "$py" ] || py=python
base="${VERIFY_RED_BASE:-origin/dev}"
git rev-parse --verify -q "$base^{commit}" >/dev/null || base=dev
mb="$(git merge-base "$base" HEAD)"
worktree_root="$(git rev-parse --show-toplevel)"

if ! git diff --quiet -- "$@" || ! git diff --cached --quiet -- "$@"; then
  echo "verify-red: $* have uncommitted changes; commit them first so the revert is unambiguous" >&2
  exit 2
fi

# Resolve each reverted file's top-level package: pyrite/... -> pyrite;
# extensions/<name>/src/<pkg>/... -> <pkg>. Files outside both shapes (e.g.
# tests/) carry no importable package and are skipped. (Plain space-separated
# "seen" list, not an associative array: the pre-push hook and CI both run
# this under macOS's stock bash 3.2, which has no `declare -A`.)
checked_pkgs=" "
for f in "$@"; do
  pkg=""
  case "$f" in
    pyrite/*) pkg="pyrite" ;;
    extensions/*/src/*)
      # extensions/<name>/src/<pkg>/...  -- take the path segment after src/
      rest="${f#extensions/*/src/}"
      pkg="${rest%%/*}"
      ;;
  esac
  [ -n "$pkg" ] || continue
  case "$checked_pkgs" in *" $pkg "*) continue ;; esac
  checked_pkgs="$checked_pkgs$pkg "

  # PYTHONDONTWRITEBYTECODE: this import runs BEFORE the revert below. A .pyc
  # written here from the fixed source can be same-size/same-second as the
  # merge-base source that replaces it on disk, which fools CPython's mtime
  # check into serving the stale (fixed) bytecode to the pytest run that is
  # supposed to see the reverted (broken) one -- silently defeating the
  # revert this whole script exists to prove happened.
  resolved="$(PYTHONDONTWRITEBYTECODE=1 "$py" -c "import ${pkg}, os; print(os.path.dirname(${pkg}.__file__))" 2>/dev/null || true)"
  if [ -z "$resolved" ]; then
    echo "verify-red: \`$py -c 'import $pkg'\` failed -- cannot confirm which tree this interpreter tests" >&2
    exit 2
  fi
  case "$resolved" in
    "$worktree_root"/*|"$worktree_root")
      ;;
    *)
      echo "verify-red: $pkg resolves outside this worktree ($resolved, not under $worktree_root) -- a suite number from a tree the interpreter is not importing is not evidence" >&2
      exit 2
      ;;
  esac
done

# Drop a file's cached bytecode. A .pyc from one version can be same-size/
# same-second as the other version that replaces it on disk, which fools
# CPython's mtime check into serving stale bytecode -- to the reverted run
# below, or, after the restore, to the next run against the fix.
drop_pyc() {
  local b
  b="$(basename "$1" .py)"
  rm -f "$(dirname "$1")/__pycache__/${b}".cpython-*.pyc 2>/dev/null || true
}

# Restore each file on its own: one `git checkout HEAD -- a b` with a path HEAD
# does not have (the old side of a rename, a deleted file put back for the run)
# fails as a whole and restores nothing.
restore() {
  local f
  for f in "$@"; do
    if git cat-file -e "HEAD:$f" 2>/dev/null; then
      git checkout -q HEAD -- "$f" 2>/dev/null || true
    else
      git rm -q --cached --ignore-unmatch -- "$f" >/dev/null 2>&1 || true
      rm -f -- "$f"
    fi
    drop_pyc "$f"
  done
}
trap 'restore "$@"' EXIT
# A timeout (scripts/verify_red_ci.py) TERMs this script: exit through the EXIT trap.
trap 'exit 143' TERM INT

# Revert each file to its merge-base content; a file that did not exist there is removed.
for f in "$@"; do
  if git cat-file -e "$mb:$f" 2>/dev/null; then
    git checkout -q "$mb" -- "$f"
  else
    rm -f -- "$f"
  fi
  drop_pyc "$f"
done

# `git checkout <rev> -- f` updates the index too, so compare against HEAD, not the index.
if git diff --quiet HEAD -- "$@"; then
  echo "verify-red: $* are identical at the merge base ($mb) -- nothing was reverted, so this proves nothing" >&2
  exit 2
fi

# Bash 3.2 (macOS) treats "${arr[@]}" of an empty array as unbound under set -u.
junit=()
[ -z "${VERIFY_RED_JUNITXML:-}" ] || junit=("--junitxml=$VERIFY_RED_JUNITXML" -o junit_family=xunit1)
if "$py" -m pytest "$test_id" -q -p no:cacheprovider ${junit[@]+"${junit[@]}"} >/dev/null 2>&1; then
  echo "verify-red: $test_id PASSED without the fix -- it does not test the change" >&2
  exit 1
fi
echo "verify-red: $test_id fails without the fix (as it should)"
