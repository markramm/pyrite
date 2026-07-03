---
id: ci-run-getting-started-tutorial
type: backlog_item
title: "CI job that executes the getting-started tutorial in a clean container (docs-as-tests)"
kind: improvement
status: proposed
priority: medium
effort: S
created: "2026-07-02"
tags: [ci, docs, onboarding, quality]
links:
- target: docs-onboarding-fiction-sweep
  relation: related
  kb: pyrite
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
