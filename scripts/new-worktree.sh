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
#
# It is cheaper than it looks, and `du` will tell you otherwise. On APFS `uv`
# clones blocks rather than copying them, so a venv `du` reports as 1.0 GB
# costs about 112 MB of real disk -- measured 2026-09-21 from free space
# before and after removing one, and 12 MB to rebuild it (#236).
# `UV_LINK_MODE=hardlink` changes nothing here: 3 MB against 5 MB for a second
# torch. So do not collapse this into a shared venv on the strength of a `du`
# number: the saving is not there, and the isolation is the whole point (#189).
#
# The cost that IS real is worktree *count*. The conductor's health step reaps
# a worktree once its PR merges.
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

# A repo-local config so `pyrite -k pyrite` in this worktree means THIS
# worktree's kb/, not the main checkout's (which is what ~/.pyrite registers).
# pyrite finds ./.pyrite/config.yaml by searching upward from the cwd; an
# explicit PYRITE_CONFIG_DIR still wins. Gitignored.
mkdir -p .pyrite
cat > .pyrite/config.yaml <<CFG
knowledge_bases:
- name: pyrite
  path: $wt_dir/kb
  kb_type: software
  description: "Pyrite project KB (worktree $branch)"
settings:
  index_path: $wt_dir/.pyrite/index.db
  auto_embed: false
CFG
.venv/bin/pyrite index sync >/dev/null 2>&1 || true

# This worktree's Playwright e2e ports, derived from its own path so two
# worktrees can run `npm run test:e2e` at once without colliding (Package
# A.1, #118: kb/backlog/playwright-package-a-1-per-worktree-ports-and-data-dir-118.md).
# Recorded here — not just computed on demand inside playwright.config.ts —
# so a human running the suite by hand (lsof, curl, a stray uvicorn to kill)
# sees the same numbers the config derives. `web/e2e/ports.ts` is the single
# source of truth for the hash; this only prints it. Requires the worktree's
# node_modules for `derivePorts`'s only import (node:crypto, no npm package),
# so it works even before `npm ci` has run in web/.
if command -v node >/dev/null 2>&1 && [ -f "$wt_dir/web/e2e/print-ports.ts" ]; then
  node "$wt_dir/web/e2e/print-ports.ts" "$wt_dir" > "$wt_dir/.pyrite/e2e-ports" \
    || echo "note: could not derive e2e ports (node too old for native TS?) — playwright.config.ts will still derive them at test time" >&2
else
  echo "note: node not found; skipping .pyrite/e2e-ports (playwright.config.ts derives ports itself at test time)" >&2
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
config:   $wt_dir/.pyrite/config.yaml  (pyrite KB -> this worktree's kb/)
e2e ports: $wt_dir/.pyrite/e2e-ports  (this worktree's Playwright ports; cat it before running lsof by hand)

  cd "$wt_dir"
  ... work, commit ...
  git push -u origin "$branch"
  gh pr create --base dev --fill && gh pr merge --auto --rebase
  # if another PR merges first the PR goes BEHIND: gh pr update-branch --rebase

When merged (the branch is deleted on GitHub automatically):
  git -C "$repo_root" worktree remove "$wt_dir" && git -C "$repo_root" branch -d "$branch"
EOF
