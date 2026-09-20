---
id: adr-0034-ii-write-paths-refuse-a-body-marked-body-truncated
title: 'ADR-0034 (ii): write paths refuse a body marked body_truncated'
type: backlog_item
tags:
- mcp
- agent-ux
- bounded-reads
- adr-0034
importance: 5
kind: improvement
status: done
priority: medium
effort: S
rank: 0
---

**DONE 2026-09-20** on `fix/adr-0034-ii-refuse-truncated-writes`. ADR-0034 was accepted 2026-09-18; the numbers in rule 4 were untouched by this theme (themes i/iii/iv/v still own them).

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

## Done 2026-09-20

The rule lives once, in `pyrite/services/body_bounds.py`
(`refuse_truncated_body`), and runs on the **raw** request per surface --
not in `KBService`, which takes an `Entry` plus keyword frontmatter and
cannot carry the marker, and not after REST's pydantic models, which drop
the undeclared key.

- **MCP**: the guard is in `_dispatch_tool`, so it covers every write-tier
  and admin-tier tool by construction -- `kb_create`, `kb_update`,
  `task_create`, `task_decompose` and any plugin write tool -- rather than
  by enumerating handlers. Reads are never guarded.
- **`kb_bulk_create`**: per-item refusal per its existing
  `{"created": false, "error": ...}` contract; clean siblings are created
  and result indices stay aligned to the request's `entries` array.
- **REST**: a FastAPI dependency (`refuses_truncated_body`) on
  `POST`/`PUT`/`PATCH /api/entries` reads the raw JSON before pydantic;
  `POST /api/entries/import` refuses per record, and the JSON importer now
  carries the truncation keys through its whitelist so the endpoint can see
  a marker saved to a file.
- **Refusal rule**: a truthy `body_truncated` (including the strings
  `"true"`/`"yes"`/`"1"`) arriving alongside a body, at the top level or
  nested (`metadata`, a child-spec list). Allowed: `false`, the marker with
  no body (a metadata-only update), and a body exactly `body_chunk_size`
  long with no marker.
- **Also fixed**: an allowed `body_truncated: false` was being persisted as
  frontmatter by the three paths that forward unrecognised keys into the
  entry (MCP `kb_create`, `KBService.bulk_create_entries`, the REST import
  endpoint, and `pyrite create`'s `--field`/frontmatter path). The
  truncation keys are read transport, never entry content.

- **CLI** (#230, the third untrusted input surface -- ADR-0034 rule 5
  records that most CLI callers today are agents): `pyrite import` refuses
  per record and exits 1; `pyrite create` refuses the marker from
  `--field` *or* from the YAML frontmatter of a `--body-file`/`--stdin`
  read, which is the saved-scratch-file path by which a marker is most
  likely to be persisted and replayed; `pyrite update` refuses the marker
  from `--field`. `pyrite update --body-file` is deliberately unchanged:
  it does not parse frontmatter, so a marker there is body content, and
  refusing on it would be the heuristic detection ADR-0034 rules out.

**Importer audit** (asked for by #230): `json` and `markdown` carry the
marker through to the caller -- markdown always has, via
`_parse_single_md`'s frontmatter splat, so REST's `/entries/import` could
receive one before this branch -- while `yaml` and `csv` strip it through
their key whitelists. Both import endpoints check every record regardless
of format, so a whitelist that gains the key later is already covered.

Tests: `tests/test_truncated_body_refused_on_write.py` (21),
`tests/test_truncated_body_refused_on_cli_write.py` (13).
