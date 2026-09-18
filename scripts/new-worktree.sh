#!/usr/bin/env bash
# One session, one branch, one checkout (ADR-0032).
#
#   scripts/new-worktree.sh fix/what-it-fixes            # branch from origin/dev
#   scripts/new-worktree.sh feature/thing v0.24.1        # branch from a tag/sha
#
# Creates ../pyrite-wt/<branch-with-slashes-as-dashes>/ as a git worktree on a
# new branch, gives it its own .venv with pyrite + every extension installed,
# and installs the git hooks. Prints the directory to cd into. Idempotent for
# an existing branch: reuses it.
#
# Why a worktree per session: two sessions cannot hold different branches in
# one working tree, and a shared tree is how one session's hook stashed
# another's edits, and how a test run replaced the shared .git/index
# (2026-09-17). The unit of isolation is the branch.
set -euo pipefail

branch="${1:?usage: $0 <branch-name> [start-point]}"
start="${2:-origin/dev}"

repo_root="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
wt_parent="$(dirname "$repo_root")/pyrite-wt"
wt_dir="$wt_parent/${branch//\//-}"

cd "$repo_root"
git fetch -q origin dev

mkdir -p "$wt_parent"
if git show-ref --verify --quiet "refs/heads/$branch"; then
  echo "branch $branch exists; checking it out in a worktree"
  git worktree add -q "$wt_dir" "$branch"
else
  git worktree add -q -b "$branch" "$wt_dir" "$start"
fi

cd "$wt_dir"

# A venv per worktree: an editable install points at one checkout, so a
# shared venv would import whichever tree was installed last.
if command -v uv >/dev/null 2>&1; then
  uv venv -q .venv
  uv pip install -q --python .venv/bin/python -e ".[all]"
  for ext in extensions/*/; do
    [ -f "$ext/pyproject.toml" ] && uv pip install -q --python .venv/bin/python -e "$ext"
  done
else
  python3 -m venv .venv
  .venv/bin/pip install -q -e ".[all]"
  for ext in extensions/*/; do
    [ -f "$ext/pyproject.toml" ] && .venv/bin/pip install -q -e "$ext"
  done
fi

# Hooks live in the shared .git and the installed shim embeds the path of the
# Python that installed them. Install from the MAIN checkout's venv, which
# outlives any worktree: hooks installed from a worktree's venv break for
# every checkout the moment that worktree is removed (learned the hard way).
if [ -x "$repo_root/.venv/bin/pre-commit" ]; then
  (cd "$repo_root" && .venv/bin/pre-commit install >/dev/null)
else
  echo "note: $repo_root/.venv has no pre-commit; hooks installed from this worktree's venv" >&2
  .venv/bin/pre-commit install >/dev/null
fi

cat <<EOF

worktree: $wt_dir
branch:   $branch (from $start)
venv:     $wt_dir/.venv

  cd "$wt_dir"
  ... work, commit ...
  git push -u origin "$branch"
  gh pr create --base dev --fill && gh pr merge --auto --rebase
  # if another PR merges first the PR goes BEHIND: gh pr update-branch --rebase

When merged (the branch is deleted on GitHub automatically):
  git -C "$repo_root" worktree remove "$wt_dir" && git -C "$repo_root" branch -d "$branch"
EOF
