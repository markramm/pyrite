---
id: adr-0034-ii-write-paths-refuse-a-body-marked-body-truncated
title: 'ADR-0034 (ii): write paths refuse a body marked body_truncated'
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

A bounded read hands an agent part of a body plus `body_truncated: true`. An agent that edits what it received and writes the entry back replaces a 170,000-character body with its first 8,000 — silent data loss, produced by the safety feature. ADR-0034 rule 2: "A truncated body is never valid input to a write: a write path that receives `body_truncated` refuses."

## Acceptance

1. `kb_create`, `kb_update`, `kb_bulk_create` (MCP), `POST /api/entries`, `PUT /api/entries/{id}`, `POST /api/entries/import` (REST) refuse an input that carries `body_truncated: true` (or any of the marker keys alongside a `body`), with `VALIDATION_FAILED`, `retryable: false`, and a message naming `kb_read_body` / `--body-offset` as how to get the rest.
2. The check lives once — one function in `pyrite/services/body_bounds.py`, called by the MCP and REST handlers on the raw request before the service call (`KBService._validate_write` receives an `Entry`, which cannot carry the marker) — not re-implemented per surface. REST's pydantic request models must not silently drop the key before the check sees it.
3. A write **without** the marker is unaffected, including a body that happens to be exactly the chunk size.
4. `kb_bulk_create` reports the refused item per its existing per-item contract and does not write it.

## Groom 2026-09-18 (serial)

**Regimes:** marker `true`, `false`, absent, and the string `"true"`; marker present with no `body` (a metadata-only update — allowed: nothing truncated is being written); a bulk create where one of N items is marked (the others' fate follows #95's outcome — state which); REST request models with `extra="ignore"` (the key never reaches the service unless the model declares it — the test must go through `TestClient`, not call the service); a body whose length equals `body_chunk_size` with no marker.

**Touches** — existing: `pyrite/services/body_bounds.py` (from theme i), `pyrite/server/mcp_server.py` (`_kb_create` :765, `_kb_bulk_create` :847, `_kb_update` :891), `pyrite/server/schemas.py` (`CreateEntryRequest` :359, `UpdateEntryRequest` :374), `pyrite/server/endpoints/entries.py` (:674, :736, import :524), `CHANGELOG.md`. New: `tests/test_truncated_body_refused_on_write.py`.

**Sequence:** after ADR-0034 is accepted; after (i) (`mcp_server.py`); after #166 lands or is abandoned (it also carries #95's `kb_bulk_create` change in the same function).

**Model:** opus (write path, two surfaces, one rule). **heavy:** no. **Cold read:** yes. **Size:** S, ~200 lines, mostly tests.

**Out of scope:** the CLI — `pyrite create`/`update` take the body as text (`--body`, `--body-file`, `--stdin`), so there is no marker to receive; theme (iii)'s stderr notice is its protection. Detecting truncation heuristically (a body that "looks cut off") — the marker is the contract; the web editor (it requests whole bodies, rule 6).
