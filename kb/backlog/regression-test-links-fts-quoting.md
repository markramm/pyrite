---
id: regression-test-links-fts-quoting
type: backlog_item
title: "Add the missing 40e7a39 regression test: links suggest/orphans with FTS-column-colliding vocabulary"
kind: tech_debt
status: proposed
priority: high
effort: XS
created: "2026-07-03"
tags: [testing, links, fts, audit-2026-07]
links:
- target: search-query-syntax-error-contract
  relation: related
  kb: pyrite
---

## Problem

The `links suggest`/`links orphans` FTS crash fix (40e7a39, quotes
FTS5 terms in `link_discovery_service.py:57-58`) shipped with zero
test changes — the one field-bug fix without a regression lock, and
the one open violation of Iron Law 1. `tests/test_link_suggest.py`
and `test_link_orphans.py` contain no column-collision/quoting case;
test entry titles ("Test Event 0") can never collide with FTS column
names, but the field vocabulary is literally "capture" and
"legalism".

## Fix

Add tests: entries titled/tagged with FTS-colliding and
special-character vocabulary ("capture legalism", "cross-link",
"18:1", dotted versions) run through `links suggest` and
`links orphans` on both backends without OperationalError and return
sane results. Share the adversarial-strings constant with
[[dirty-world-fixtures-and-adversarial-corpus]] if that lands first.

## Acceptance criteria

- A test that fails on pre-40e7a39 code and passes now, covering both
  suggest and orphans paths.
