---
created: "2026-07-02"
body: "## Problem\n\nThe 2026-07-02 docs audit found the docs are excellent wherever an\nagent loop exercises them daily and fictional wherever no one has\nexecuted them since writing (`pip install pyrite` DOA, `--tier` flag\nnonexistent, git-init claim false — see\n[[docs-onboarding-fiction-sweep]]). One-time fixes will re-rot; the\ndurable fix is putting the untested paths under the same discipline as\nthe tested ones.\n\n## Fix\n\nA CI job (weekly + on docs/ changes, not every push) that:\n\n1. Builds a clean container, installs pyrite the way the docs say to\n   (once the fiction sweep settles the install story).\n2. Extracts and executes the code blocks from\n   `docs/getting-started.md` (and the README Quick Start) in order —\n   either via a fenced-block runner script or by maintaining the\n   tutorial as a literate script the doc is generated from.\n3. Asserts each command exits 0 and, where the doc shows output,\n   asserts the shape (e.g. `search` returns count ≥ 1 — which forces\n   the doc's example queries to actually match its example data).\n4. Runs `pyrite index health` on the tutorial KB and fails on\n   `status: warning` — the audit found a fresh tutorial KB failing the\n   tool's own health check via extension type-remapping\n   (person→actor `undeclared_types` warnings).\n\n## Acceptance criteria\n\n- CI fails if any getting-started/Quick Start code block breaks on the\n  current build.\n- The `--tier`-class bug (documented flag that doesn't exist) is\n  structurally impossible to ship again for tutorialized surfaces."
file_path: /Users/markr/pyrite-wt/feature-smoke-e2e/kb/backlog/ci-run-getting-started-tutorial.md
id: ci-run-getting-started-tutorial
title: "CI job that executes the getting-started tutorial in a clean container (docs-as-tests)"
type: backlog_item
tags: [ci, docs, onboarding, quality]
links:
- target: docs-onboarding-fiction-sweep
  relation: related
  kb: pyrite
importance: 5
kind: improvement
status: done
priority: medium
assignee: agent:conductor
effort: S
rank: 0
---

## Problem

The 2026-07-02 docs audit found the docs are excellent wherever an
agent loop exercises them daily and fictional wherever no one has
executed them since writing (`pip install pyrite` DOA, `--tier` flag
nonexistent, git-init claim false — see
[[docs-onboarding-fiction-sweep]]). One-time fixes will re-rot; the
durable fix is putting the untested paths under the same discipline as
the tested ones.

## Fix

A CI job (weekly + on docs/ changes, not every push) that:

1. Builds a clean container, installs pyrite the way the docs say to
   (once the fiction sweep settles the install story).
2. Extracts and executes the code blocks from
   `docs/getting-started.md` (and the README Quick Start) in order —
   either via a fenced-block runner script or by maintaining the
   tutorial as a literate script the doc is generated from.
3. Asserts each command exits 0 and, where the doc shows output,
   asserts the shape (e.g. `search` returns count ≥ 1 — which forces
   the doc's example queries to actually match its example data).
4. Runs `pyrite index health` on the tutorial KB and fails on
   `status: warning` — the audit found a fresh tutorial KB failing the
   tool's own health check via extension type-remapping
   (person→actor `undeclared_types` warnings).

## Acceptance criteria

- CI fails if any getting-started/Quick Start code block breaks on the
  current build.
- The `--tier`-class bug (documented flag that doesn't exist) is
  structurally impossible to ship again for tutorialized surfaces.
