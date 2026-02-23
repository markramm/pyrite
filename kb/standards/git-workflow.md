---
type: standard
title: "Git Workflow & Commits"
category: git
enforced: true
tags: [git, workflow]
---

## Pre-commit Hooks
Configured via `.pre-commit-config.yaml`:
- ruff (lint + fix)
- ruff-format (auto-format)
- trailing-whitespace, end-of-file-fixer
- check-yaml, check-large-files, check-merge-conflict
- debug-statements
- pytest (full suite via .venv)

## Commit Messages
Follow conventional commits: feat, fix, docs, test, refactor, chore.
Keep subject line concise, use body for details.

## Important
- Hooks run twice on failure (ruff-format may reformat, requiring re-stage)
- Extensions must be `pip install -e` in the .venv for pytest hook to pass
- Never force-push to main
