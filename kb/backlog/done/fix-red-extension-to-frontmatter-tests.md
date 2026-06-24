---
id: fix-red-extension-to-frontmatter-tests
title: "9 RED extension tests: to_frontmatter now writes defaults the tests expect omitted"
type: backlog_item
tags: [tests, ci, extensions, to-frontmatter, tech-debt]
importance: 5
kind: bug
status: done
priority: high
effort: M
rank: 0
---

## Problem

Nine tests across five extensions fail on `dev`, all asserting that
`to_frontmatter()` omits default/empty values:

- `extensions/cascade/.../test_cascade_ji_inheritance.py::TestTimelineEventJIFields::test_verification_status_default_not_in_frontmatter`
- `extensions/encyclopedia/.../test_encyclopedia.py::TestArticleEntry::test_to_frontmatter_omits_defaults`
- `extensions/journalism-investigation/.../test_connection_types.py::Test{Ownership,Membership,Funding}Entry::test_to_frontmatter_omits_empty`
- `extensions/journalism-investigation/.../test_event_types.py::Test{InvestigationEvent,Transaction}Entry::test_to_frontmatter_omits_empty`
- `extensions/social/.../test_social.py::TestWriteupEntry::test_to_frontmatter_omits_defaults`
- `extensions/zettelkasten/.../test_zettelkasten.py::TestZettelEntry::test_to_frontmatter_omits_defaults`

Example: `ZettelEntry(id="test", title="Test").to_frontmatter()` now yields
`{'id', 'importance': 5, 'maturity': 'seed', 'title', 'zettel_type': ...}`, but
the test asserts `zettel_type` (and other defaults) are absent.

## Root cause

Base `Entry.to_frontmatter` now writes `importance` unconditionally
(`pyrite/models/base.py:132` — `meta["importance"] = self.importance`), and per-type
`to_frontmatter` overrides similarly write previously-omitted defaults. This is the
intentional "always write meaningful fields" change (the same family as the
daily-capture feature request to always write `importance` for events). The extension
entry types inherit/mirror the new behavior, but their `test_to_frontmatter_omits_*`
tests were written against the old omit-defaults contract and never updated.

So this is stale-test fallout from a deliberate behavior change, not a live data bug —
the same shape as `[[fix-red-backend-capability-tests-on-dev]]`.

## Why it wasn't caught earlier

The documented backend test path is `pytest tests/` (per CLAUDE.md), which does not
collect `extensions/`. These only surface on a `pytest tests/ extensions/` (or full
`pytest`) run. CI *does* run root `pytest` with extensions installed
(`.github/workflows/ci.yml:39,63`), so **CI is likely currently red on `dev`** — worth
confirming and is itself the more important signal here.

## Fix

Decide the contract per field, then make tests and behavior agree:

1. If writing these defaults is intended (likely, matching the `importance` decision),
   update the 9 extension tests to assert the new always-written fields instead of
   asserting omission.
2. If omission is still the contract for *some* fields (e.g. a `zettel_type: fleeting`
   default genuinely shouldn't clutter frontmatter), gate those in the relevant
   `to_frontmatter` overrides.
3. Confirm CI status on `dev` and get it green.

## Provenance

Surfaced 2026-06-23 during the pyrite-dev ticket loop, on the first full
`pytest tests/ extensions/` run (prior loop runs used `tests/` only, per CLAUDE.md, so
the extension suites were never exercised). Filed at high priority because a red
extensions suite — and likely-red CI — masks real regressions.
