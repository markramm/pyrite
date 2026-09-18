---
id: pin-the-test-runner-one-pytest-and-xdist-version-for-every-venv-and-every-ci-leg
title: 'Pin the test runner: one pytest and xdist version for every venv and every CI leg'
type: backlog_item
tags:
- quality
- ci
- testing
kind: tech_debt
status: done
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

## Closed

`pytest==9.1.1`, `pytest-cov==7.1.0`, `pytest-xdist==3.8.0` pinned exactly in
the `dev` extra; all three are pure-Python (`py3-none-any`) wheels, so one
version installs identically on 3.11/3.12/3.13 — no interpreter-specific
fallback was needed. `TestPinnedTestRunner` in
`tests/test_dev_process_config.py` asserts the pins stay `==`. PT enabled for
`tests/` only (ruff has no per-file *select*, so it's global in `select` and
turned back off for everywhere but `tests/` via per-file-ignores): 14
mechanical findings fixed (7 PT001, 4 PT022, 3 PT006); PT011/PT012/PT018/PT019
(37 findings) ignored with one-line reasons each — all require per-call-site
judgment, none had a ruff autofix even under `--unsafe-fixes`.

**One acceptance criterion not met, with evidence why:** "a `@classmethod`
fixture must be a lint error under any runner." Checked exhaustively — ruff's
`PT` set (all rule names cross-referenced against `flake8_pytest_style`'s
source at the installed 0.15.22), `ruff check --select ALL --preview`, and
pytest's own `filterwarnings` — no rule or warning fires on `@classmethod`
above `@pytest.fixture`. It cannot: pytest's own source
(`_pytest/fixtures.py`, `CLASS_FIXTURE_INSTANCE_METHOD`) treats the *opposite*
ordering (a class-scoped fixture as a plain instance method) as the
deprecated pattern and recommends `@classmethod` as the fix. #133's account
of the #81 break says the same: "the cheapest correct action was simply to
drop it" — `tests/test_api_tiers.py` was fixed forward by removing
`@classmethod`, not by the pattern being wrong. The pin itself closes the
actual risk (everyone always resolves 9.1.1, so the interpreter-dependent
silent-fixture-drop from #81 cannot recur); a lint rule for the pattern would
need a new local check (`scripts/`) + pre-commit hook, which is out of this
theme's declared footprint (`Touches: New: none`). Left for a follow-up if a
static check is still wanted — see the pyrite-dev report on this branch.
Meanwhile `test_api_tiers.py`'s 5 fixtures currently use the *plain*
instance-method pattern, which is the one pytest 10 will remove entirely
(`PytestRemovedIn10Warning`, live in this suite's own warnings) — filed as
#144, out of scope here.
