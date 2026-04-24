---
id: broken-wikilinks-are-wanted-pages-not-errors-severity-downgrade
title: Broken wikilinks are wanted-pages, not errors (severity downgrade)
type: backlog_item
tags:
- qa
- validation
- wiki
- decision
importance: 5
kind: chore
status: completed
priority: medium
effort: S
rank: 0
---

## Decision

Broken wikilinks — links whose target entry does not exist — represent
wiki-style 'wanted pages' (aspirational forward references), not data
integrity errors. Classify them as `severity: warning` rather than
`severity: error` so they surface for review but don't fail CI.

## Before

- `pyrite/services/qa_service.py::_check_broken_links` emitted
  `severity: error` for every broken target.
- `pyrite/services/qa_service.py::_check_entry_links` (the per-entry
  variant) did the same.
- On the pyrite KB today, that produced 10 broken_link errors alongside
  102 legitimate schema_violation errors — mixing intentional forward
  references with real data corruption.
- `pyrite qa validate` (rich output path) exits 1 on any error, so
  a fully-valid KB with a few wanted pages failed CI.

## After

- Both broken_link emit points produce `severity: warning`.
- `pyrite qa validate` still surfaces them in output and summary, but
  does not exit 1 when broken links are the only issue.
- `pyrite index health` already treated broken links as warning — now
  consistent across the three surfaces (index health, qa validate, links
  check).

## Lock-in tests

- tests/test_qa_service.py::test_validate_detects_broken_link — asserts
  warning severity.
- tests/test_qa_rules.py::TestCheckBrokenLinks::test_flags_link_to_nonexistent_target
  and ::TestCheckEntryLinks::test_flags_broken_outlink — same.
- tests/test_ci_command.py::TestQAValidateBrokenLinkExitCode — two
  CLI-level tests: rich output exits 0 when broken links are the only
  issue; JSON output reports severity=warning. Verified as
  regression-catching: flipping production back to 'error' makes the
  rich-output test fail with exit_code=1.

## Commit

See commit message for full rationale.
