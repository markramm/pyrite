---
id: test-infrastructure
title: "Test Infrastructure Improvements"
type: backlog_item
tags:
- improvement
- testing
- code-hardening
- dx
kind: improvement
priority: medium
effort: S
status: done
links:
- roadmap
- test-coverage-gaps
---

# Test Infrastructure Improvements

**Wave 6b of 0.9 Code Hardening.** Improve test runner configuration and add missing test coverage for web clipper.

## Items

| Item | File | Effort | Description |
|------|------|--------|-------------|
| Full clip_url test with mocked HTTP | `tests/test_web_clipper.py` | S | Test `clip_url` with mocked httpx responses, verify markdown conversion and metadata extraction |
| Include extension tests in default run | `pyproject.toml` | XS | Add `extensions/*/tests/` to pytest testpaths so extension tests run by default |
| Add pytest-xdist + exclude slow by default | `pyproject.toml`, dev deps | S | Add `pytest-xdist` for parallel test execution, mark slow tests and exclude by default with `--run-slow` opt-in |

## Definition of Done

- `clip_url` tested with mocked HTTP (no real network calls)
- `pytest` runs extension tests by default
- `pytest -n auto` works for parallel execution
- Slow tests (performance, 1000-entry) excluded unless `--run-slow` passed
