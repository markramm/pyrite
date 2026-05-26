---
id: enforce-mypy-strict
type: backlog_item
title: "Enforce mypy in CI; tighten strictness incrementally"
kind: improvement
status: proposed
priority: medium
effort: M
tags: [ci, type-safety, dx, code-quality]
---

## Problem

`.github/workflows/ci.yml` runs `mypy pyrite/ --ignore-missing-imports` with
`continue-on-error: true`. Type errors do not fail the build.

The codebase is well-annotated (services audit shows ~90–100% return-type
coverage on the core service layer), so the cost of turning enforcement on
is mostly a one-time cleanup, not a slow migration.

Two consequences of not enforcing:

1. New code drifts. Contributors don't see type errors until they read CI
   output (which is buried), and there's no incentive to fix them.
2. Several existing bugs are exactly the kind mypy catches —
   `plugin-registry-silent-failures` and `search-fallback-error-obscured`
   are at root return-type and `Optional` handling issues.

## Solution

1. Run `mypy pyrite/` locally with current config. Capture the error count.
2. Fix or `# type: ignore` (with comments explaining why) the existing
   errors. Aim for zero ignores; accept a small triaged list.
3. Flip `continue-on-error: false` in the workflow.
4. Add a `[tool.mypy]` block in `pyproject.toml` with the current strictness
   level explicit (so the bar is in version control, not implicit on the CI
   runner).
5. Open follow-on tickets for incremental tightening:
   - Per-module `strict = true` for `pyrite/services/`, `pyrite/storage/`
   - Then `pyrite/server/`
   - Then plugins (`extensions/*`)
6. Optional: add `mypy --strict` as a separate non-blocking job so we can
   measure the gap to full strictness.

## Acceptance criteria

- `mypy pyrite/` passes on `dev`.
- CI fails on new mypy errors.
- `pyproject.toml` carries the active mypy config.
- Per-module strict-mode follow-ons created as separate tickets.

## Related

- `plugin-registry-silent-failures` — likely partially caught by stricter
  Optional handling
- `enforce-ruff-stricter` (potential follow-on) — same pattern for lint
