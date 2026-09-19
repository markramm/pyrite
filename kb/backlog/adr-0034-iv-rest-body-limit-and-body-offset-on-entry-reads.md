---
id: adr-0034-iv-rest-body-limit-and-body-offset-on-entry-reads
title: 'ADR-0034 (iv): REST body_limit / body_offset on entry reads, default unbounded'
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

REST entry reads return whole bodies with no way to ask for less. ADR-0034 rule 6: "`GET /api/entries/{id}` and batch reads accept `body_limit`/`body_offset` with the same marker keys, and default to the full body: the web editor round-trips whole bodies, and a default bound there is the data-loss shape rule 2 forbids."

## Acceptance

1. `GET /api/entries/{id}?body_limit=N&body_offset=M` and `POST /api/entries/batch` (`body_limit`, `body_offset` in the request body) return a bounded body with `body_truncated`, `body_length`, `body_offset`, `body_chunk_size` — the same keys, same meanings, as MCP.
2. With neither parameter the response is byte-identical to today's (the web editor's contract).
3. `body_limit` is clamped to `PYRITE_BODY_CHUNK_MAX`; the batch endpoint applies `PYRITE_BODY_RESPONSE_BUDGET` **only when `body_limit` is given**.
4. `EntryResponse` declares the four marker keys as optional so they survive `response_model` filtering; the OpenAPI schema shows them.

## Groom 2026-09-18 (serial)

**Regimes:** `body_limit=0`, negative, non-integer (422 naming the parameter); `body_offset` past the end; `body_limit` with `fields` that excludes `body` (no marker keys); content negotiation (`negotiate_response` returns markdown/YAML for some `Accept` headers — say what a bounded markdown response carries, or refuse the combination with a 400); an entry in a KB the caller cannot read (still 404, no length oracle via `body_length`).

**Touches** — existing: `pyrite/server/endpoints/entries.py` (`get_entry` :614, `batch_read_entries` :335), `pyrite/server/schemas.py` (`EntryResponse` :116), `CHANGELOG.md`. New: `tests/test_rest_body_limit.py`.

**Sequence:** after ADR-0034 is accepted; after (i) (shared helper); after (ii) and after #134's fix (both edit `endpoints/entries.py` / `schemas.py`).

**Model:** sonnet. **heavy:** no. **Cold read:** yes (REST response shape; read-scoping interaction). **Size:** S, ~180 lines.

**Out of scope:** the web UI requesting bounded bodies for read-only views (ADR open question 2); list endpoints.
