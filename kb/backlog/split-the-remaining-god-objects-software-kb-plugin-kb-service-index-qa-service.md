---
id: split-the-remaining-god-objects-software-kb-plugin-kb-service-index-qa-service
title: 'Split the remaining god objects: software-kb plugin, kb_service, index, qa_service'
type: backlog_item
tags:
- architecture
- refactor
- quality
importance: 5
kind: improvement
status: proposed
priority: low
effort: L
rank: 0
---

## Problem

From an AST scan (2026-09-17). `mcp_server.py` (1680-line class) and the entries
endpoint already have tickets; these do not:

- `extensions/software-kb/.../plugin.py`: a 2851-line class with a 457-line
  `get_mcp_tools`. Split into `tools/` schemas, handlers, workflows.
- `pyrite/services/kb_service.py`: 1453 lines. Seams: CRUD, the claim/CAS
  workflow (`:1186`), git (`:1386-1470`).
- `pyrite/storage/index.py`: `_entry_to_dict` is 320 lines, `check_health` 231.
- `pyrite/cli/entry_commands.py:84`, `browse_commands.py:33`: ~430-line
  "register" closures; move to module-level commands.
- `pyrite/services/qa_service.py`: 1306 lines; split per rule family.

No rush — do each when next working in that file, behind its existing tests.
Also noted: 211 `except Exception` clauses, 25 of which swallow silently
(tracked by [[add-ruff-ble001-blind-except-lint-gate-for-fail-open-prevention]]);
`auth_endpoints.py:436` and `endpoints/worktree.py:105,248` swallow with no log
line. Test markers are inconsistent (`cli` 99 uses, `api` 9, `mcp` 1), and
collection emits a `PytestCollectionWarning` for `test_app`.

Source: 2026-09-17 project review (three read-only audits: docs/contributor, public-repo, code-health). Related: [[split-mcp-server-module]], [[split-entries-endpoint]].
