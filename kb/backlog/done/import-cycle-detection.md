---
id: import-cycle-detection
type: backlog_item
title: "Add import cycle detection to pre-commit hooks"
kind: improvement
status: completed
milestone: "0.17"
priority: low
effort: XS
tags: [developer-experience, ci, code-quality]
---

# Add import cycle detection to pre-commit hooks

## Problem

No circular import cycles exist today, but there's no automated guard preventing them from being introduced. As the codebase grows (especially with more extensions), accidental cycles between models, storage, and services become more likely.

## Solution

Add an import cycle detection step to pre-commit hooks. Options:

1. **`importlab`** — Google's import cycle detector for Python
2. **`pydeps --no-show --reverse`** — detects cycles as part of dependency graphing
3. **Custom script** — parse imports with AST, build graph, detect cycles

Option 1 is simplest. Add as a pre-commit hook alongside ruff.

## Files

- `.pre-commit-config.yaml` — new hook entry
- `pyproject.toml` — dev dependency if needed
