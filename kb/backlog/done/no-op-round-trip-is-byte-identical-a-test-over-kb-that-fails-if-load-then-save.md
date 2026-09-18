---
id: no-op-round-trip-is-byte-identical-a-test-over-kb-that-fails-if-load-then-save
title: 'No-op round trip is byte-identical: a test over kb/ that fails if load then save rewrites any file'
type: backlog_item
tags:
- quality
- testing
- write-path
kind: tech_debt
status: done
priority: high
effort: S
assignee: agent:pyrite-worker
---

## Problem

Loading every entry in `kb/` and saving it back with no edit should change nothing. On `dev` (2026-09-18) it rewrote **768 of 768** files; PR #69's branch brought that to 148 of 766, the residual all inside `links:` (bare-string links expanded to mappings). Every write-path bug of this week — #46 (`--tags`), #86 (`create`), #87 (`link`/`update` folding the body into a `body:` scalar that then fails to parse), #15 before them — is a special case of "save wrote something load did not read". The conductor measured this by hand during #69's review; it should be a test nobody can skip.

## Fix

- A test (in the default suite, seconds) that walks `kb/` — the real corpus, 766 entries with every frontmatter style in use — loads each entry through the repository, saves it to a temp copy, and asserts the bytes are identical. Report the first ten diffs on failure, unified, so the fix is obvious.
- A second, smaller fixture set under `tests/fixtures/roundtrip/` with the adversarial shapes: inline vs block lists, quoted scalars, a body with `|---|---|` and `---` lines, YAML anchors and merge keys, CRLF, a file without a trailing newline, `created` as a date vs a string.
- Fix whatever the test finds in the `links:` residual if it is small; otherwise file it with the diff and leave the test `xfail(strict=True)` on exactly those ids so the gate is live for everything else.

## Acceptance

- `pytest tests/test_roundtrip_identity.py` passes on `dev` after #69 (or xfails a named, shrinking list).
- Reintroducing #46's `--tags` rewrite, #86's `create` leak, or #87's `body:` fold makes it fail.
- Runs in under 10 s in the default suite.

Footprint: new `tests/test_roundtrip_identity.py`, `tests/fixtures/roundtrip/`; possibly `pyrite/models/base.py` / `pyrite/storage/` for the links residual (coordinate with #69 — dispatch after it merges). Model: sonnet (opus if the residual fix is taken in the same theme).
