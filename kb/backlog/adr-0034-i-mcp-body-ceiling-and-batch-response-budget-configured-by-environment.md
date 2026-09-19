---
id: adr-0034-i-mcp-body-ceiling-and-batch-response-budget-configured-by-environment
title: 'ADR-0034 (i): MCP per-body ceiling 20,000 and a 40,000 per-response budget for kb_batch_read, all three numbers from the environment'
type: backlog_item
tags:
- mcp
- agent-ux
- bounded-reads
- adr-0034
- blocked
importance: 5
kind: improvement
status: proposed
priority: medium
effort: S
rank: 0
---

**BLOCKED — not dispatchable. ADR-0034 ("Agent-facing reads are bounded by default", PR #170) is `proposed`, not accepted.** The numbers in rule 4 are the maintainer's to set. Re-read the ADR as accepted before dispatching: if a number, a variable name or the CLI default changed, this item changes with it.

## Problem

`kb_get` and `kb_batch_read` chunk bodies with two module constants in `pyrite/server/mcp_server.py` (`DEFAULT_BODY_CHUNK = 8000`, `MAX_BODY_CHUNK = 50_000`). The ceiling is per body, not per response: twenty entries at the ceiling is a million characters. Measured on the maintainer's index (18,911 bodies): 8% exceed 20,000 characters, 1.3% exceed 50,000. ADR-0034 rule 4 lowers the ceiling, adds a per-response budget, and makes all three numbers configuration.

## Acceptance (from ADR-0034 rules 3 and 4)

1. Default chunk **8,000**, per-body ceiling **20,000**, per-response budget **40,000** body characters for multi-entry reads. Each reads an environment variable at server start and falls back to the default: `PYRITE_BODY_CHUNK_DEFAULT`, `PYRITE_BODY_CHUNK_MAX`, `PYRITE_BODY_RESPONSE_BUDGET`.
2. "Invalid values (non-integer, ≤ 0, default above max) fail loudly at start rather than silently falling back."
3. `kb_batch_read`: "bodies are filled in request order, the ones that do not fit come back truncated to what remains (possibly zero) with the marker, so the response size is bounded no matter how many entries were asked for."
4. A truncated body always carries `body_truncated`, `body_length`, `body_offset`, `body_chunk_size`, on every path including `fields`; `kb_read_body` continues it.
5. "Tool descriptions report the effective values, not the compiled-in ones" — `kb_get`, `kb_batch_read`, `kb_read_body` descriptions are built from the loaded configuration.
6. CHANGELOG names the two behaviour changes (ceiling 50,000 → 20,000; the batch budget) for MCP clients passing large `body_limit`s.

## Groom 2026-09-18 (serial)

**Regimes:** each variable unset, valid, `"abc"`, `0`, `-1`, and default > max (start fails, message names the variable); a caller's `body_limit` above the ceiling (clamped, marker present); a batch whose first body alone exceeds the budget (first truncated, every later body zero-length **with** the marker and its true `body_length` — not dropped, not reported `not_found`); a batch of 50 empty/None bodies (no marker, no division by zero); a batch where every entry is filtered out by read scoping; `fields` with and without `body`; budget accounting when `body_offset` is passed.

**Touches** — existing: `pyrite/server/mcp_server.py` (`_chunk_body` :96, `_kb_get` :360, `_kb_read_body` :378, `_kb_batch_read` :523), `pyrite/server/tool_schemas.py`, `docs/configuration.md` (the `PYRITE_*` table), `CHANGELOG.md`. New: `pyrite/services/body_bounds.py` (the loaded, validated numbers and `chunk_body`/`fill_budget`, so themes iii and iv import one implementation instead of reaching into the MCP module), `tests/test_body_bounds.py`.

**Sequence:** after ADR-0034 is accepted; **after outside PR #166 (#58) lands or is abandoned** — it edits the same two call sites (`fields` + `body_limit` in `_kb_get`/`_kb_batch_read`) and the ADR declares its fix correct, so this theme builds on it rather than racing it; after #169 (#137, `_project_fields`) for the same reason; after #145 (`mcp_server.py`, `tool_schemas.py`).

**Model:** opus (server; a public MCP contract changes; the budget arithmetic is where the off-by-one lives). **heavy:** no. **Cold read:** yes. **Size:** S–M, ~250 lines.

**Out of scope:** CLI and REST (iii, iv); the write-path refusal (ii); `docs/json-contracts.md` (v); list pagination, which already exists; token-based bounds (ADR alternative, rejected).
