---
id: boundary-test-rest-mcp-and-cli-must-not-reach-past-the-service-layer
title: 'Boundary test: REST, MCP and CLI must not reach past the service layer'
type: backlog_item
tags:
- architecture
- programmatic-validation
importance: 5
kind: improvement
status: proposed
priority: medium
effort: M
rank: 0
---

## Problem

All three surfaces bypass services and touch storage directly:

- REST: `endpoints/blocks.py:33` and `entries.py:407` run the same raw
  `svc.db.session.query(Block)`; `settings_ep.py:33-89` and `reviews.py:142` go
  through `svc.db.*`; `admin.py`, `ai_ep.py`, `daily.py`, `qa.py` inject
  `PyriteDB` directly.
- MCP: `mcp_server.py:151` builds its own `PyriteDB` and calls
  `self.db.find_by_*` / `count_entries` / `list_entries`.
- CLI: `index_commands.py:257` and `repo_commands.py:247` use
  `db._raw_conn.execute`; `admin_cli.py` repeats `PyriteDB(...)` try/close 11
  times and never uses `cli/context.py`.

ADR-0031 makes the API the product surface; that only holds if behaviour lives
in one layer.

## Fix

Add a Settings service and a Block service. Then a grep/AST test bans `.db.` and
`_raw_conn` outside `pyrite/services` and `pyrite/storage`, with today's
offenders in an explicit allowlist that can only shrink.

## Acceptance

- [ ] The test exists, passes, and fails when a new endpoint touches `.db.`.
- [ ] Allowlist is shorter than the list above.

Source: 2026-09-17 project review (three read-only audits: docs/contributor, public-repo, code-health). Related: [[split-mcp-server-module]], [[split-entries-endpoint]], [[mcp-rest-tool-parity]].

## Groom 2026-09-25

**This item is now #380** (0.26: surfaces stop reaching past services, with a boundary test that only ratchets down). #380 carries this item's acceptance and adds two things:
- `Depends(get_db)` appears only in the `api.py` providers, and `_raw_conn` appears nowhere under `pyrite/server`, `pyrite/cli` or `pyrite/ui`.
- The AI-settings precedence (review 2.7): only REST applies the DB override (`api.py:234-237`), while MCP, the CLI and `search_service.py:54` build `LLMService` from config alone. The new `SettingsService` owns that rule. The `api.py` lines themselves move after the patch release.

Dispatch from #380's groom comment, and close this item with it.
