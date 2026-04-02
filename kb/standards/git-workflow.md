---
id: git-workflow
type: standard
title: "Git Workflow & Commits"
category: git
enforced: true
tags: [git, workflow]
---

## Branching Model (ADR-0025)

| Branch | Purpose | Deploys to |
|--------|---------|------------|
| `dev` | Daily development (default) | demo.pyrite.wiki |
| `main` | Stable releases only | capturecascade.org, early adopters, PyPI |
| `feature/*` | Large multi-day changes | Merge to `dev` when ready |

All work happens on `dev`. `main` is protected — merge requires passing CI.

## Release Process

1. CI green on `dev`
2. Merge `dev` → `main`
3. Tag with semver: `v0.X.0`
4. Create GitHub release (triggers PyPI publish)
5. Bump pyproject.toml on `dev` to next dev version

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
- `main` has branch protection: `test (3.12)` must pass
