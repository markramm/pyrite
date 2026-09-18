---
id: pin-the-test-runner-one-pytest-and-xdist-version-for-every-venv-and-every-ci-leg
title: 'Pin the test runner: one pytest and xdist version for every venv and every CI leg'
type: backlog_item
tags:
- quality
- ci
- testing
kind: tech_debt
status: in_progress
assignee: agent:pyrite-worker
priority: high
effort: S
---

## Problem

CI resolves a different pytest per interpreter: the 3.12 job and every worktree venv got pytest 9.1.1, the 3.13 job and the main checkout's venv got 9.0.2 (#128). #81 stacked `@classmethod` on `@pytest.fixture(scope="class")`; 9.1.1 tolerated it and the PR gate (one interpreter) passed, 9.0.2 did not collect the fixtures and `dev` went red for two pushes — the value chain caught it, but a pinned runner would have made the PR gate and the matrix agree in the first place. Every "it passes here" claim across worktrees carries the same skew.

## Fix

- Pin `pytest`, `pytest-xdist` (and `pytest-asyncio`/`anyio` if present) to exact versions in `pyproject.toml`'s dev extras; `uv`'s cache already keys on `pyproject.toml`, and `scripts/new-worktree.sh` installs from it, so every venv and every CI job resolve the same runner.
- A test in `tests/test_dev_process_config.py` asserting the pins exist and are exact (`==`), so a future loosening is a visible change.
- Recreate the main checkout's and the long-lived worktrees' venvs once (`uv pip install -e ".[all,dev]"`), note it in CHANGELOG.
- Optional, same PR: enable ruff's `PT` rules for `tests/` so a `@classmethod` fixture is a lint error under any runner.

## Acceptance

- `pytest --version` identical in the main venv, a fresh worktree venv, and all three CI matrix legs (read from the job logs).
- The pin test passes; loosening a pin fails it.

Footprint: `pyproject.toml`, `tests/test_dev_process_config.py`, CHANGELOG. Model: sonnet. Not machine-heavy.
