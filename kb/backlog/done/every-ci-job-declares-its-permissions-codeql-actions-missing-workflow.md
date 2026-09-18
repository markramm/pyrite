---
id: every-ci-job-declares-its-permissions-codeql-actions-missing-workflow
title: Every CI job declares its permissions (CodeQL actions/missing-workflow-permissions x8)
type: backlog_item
tags:
- ci
- security
- codeql
kind: tech_debt
status: done
priority: medium
assignee: agent:pyrite-worker
effort: S
---

## Theme: every CI job declares its permissions (CodeQL `actions/missing-workflow-permissions` ×8)

Closes the eight `actions/missing-workflow-permissions` CodeQL alerts (`.github/workflows/ci.yml` lines 28, 57, 78, 199, 232, 271, 366, 424). `heavy: no`. Model: sonnet.

### Why

Jobs without a `permissions:` block get the repository's default `GITHUB_TOKEN` scope, which is broader than any of them needs; CodeQL flags each job. `publish.yml` already declares permissions at the top; `ci.yml` does not. Least privilege costs eight small blocks.

### Acceptance

1. A workflow-level `permissions: { contents: read }` in `ci.yml`, plus a job-level block only where a job needs more (check each job's steps: does anything write a check, upload an artifact — `actions/upload-artifact` needs no extra permission — comment on a PR, or write packages? For the `changes` job using `dorny/paths-filter`, `pull-requests: read` is required on `pull_request` events; state each grant with a one-line reason in a comment).
2. `tests/test_dev_process_config.py` asserts every job in `ci.yml` is covered by a `permissions:` block (workflow-level or its own) — so a future job cannot be added without one.
3. A PR run of the whole gate must still pass with the narrowed token (the PR itself is the proof); `gh api repos/markramm/pyrite/code-scanning/alerts?state=open` after merge shows the eight closed — the conductor checks.
4. CHANGELOG line under `[Unreleased] ### Security`; the backlog item done via `pyrite update`, moved to `kb/backlog/done/`.

### Touches

Existing: `.github/workflows/ci.yml`, `tests/test_dev_process_config.py`, `CHANGELOG.md`, the backlog item. New: none.
Out of scope: any other change to `ci.yml` (Playwright package H owns the `e2e` job; do not touch it), `publish.yml`, the 48 Python CodeQL alerts (their own item).
