---
id: mcp-rest-tool-parity
title: "Audit MCP/REST parity: port missing tools so the web UI matches agent capability"
type: backlog_item
tags: [api, mcp, parity, web-ui, refactor]
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
importance: 5
kind: improvement
status: proposed
priority: medium
effort: M
rank: 0
---

## Problem

ADR-0007 promises three surfaces — CLI, REST, MCP — with parity. In
practice MCP and REST have drifted because tools were added directly to
`pyrite/server/mcp_server.py` (1790 lines) without a matching REST endpoint.

Examples found during the May 2026 audit:

- `kb_batch_suggest` — finds cross-KB link candidates. MCP only.
- `kb_discover_neighbors` — semantic neighbor discovery with unlinked-only
  filtering. MCP only.
- `task_claim` — atomic task claim used by the conductor pattern. MCP only.
- `kb_batch_read` — multi-entry fetch. MCP only.
- `kb_orient`, `kb_recent`, `kb_stats` — overview tools. MCP only.

The web UI cannot consume these because the REST surface lacks them. Each
new MCP tool added without REST coverage widens the gap.

## CLI axis (added from the 2026-07-03 audit — third leg of the matrix)

Concrete inventory at v0.24: MCP = 29 read + 11 write + 8 admin = 48
tools; CLI ≈ 40 top-level commands + 8 subcommand groups. Gaps run in
BOTH directions:

**MCP-only (CLI has no equivalent):**
- Task-DAG introspection: `task_subtree`, `task_ancestors`,
  `task_blocked_by`, `task_critical_path` — the CLI task group stops
  at get/list/claim/decompose/checkpoint. Humans grooming epics can't
  see the DAG the agents can.
- Specialized finders: `kb_find_by_assignee`, `kb_find_overdue`,
  `kb_find_by_status`, `kb_find_by_location`.
- `kb_bulk_create` — CLI has no bulk create (see
  [[bulk-import-from-directory]], still open).

**CLI-only (agents over MCP cannot):**
- `rename` (with wikilink rewrite) — the dangerous one: an MCP agent
  that wants to rename must delete+create, breaking every wikilink;
  the safe implementation exists (r1700) but isn't exposed.
- Link-integrity audit: `links check/orphans/asymmetric` (MCP has
  only batch_suggest + discover_neighbors).
- QA depth: `qa fix/gaps/checkers/stale/compact/check-urls/coverage`
  (MCP has validate/status/assess only).
- `export`, `schema diff/migrate`, `collections`, `db backup/restore`,
  `kb discover`, search's `--trace` debug and fips/state filters.

**Behavioral divergences (same operation, different answers):**
- Default search mode: MCP hardcodes hybrid; REST defaults keyword;
  CLI uses config-or-keyword.
- MCP `_kb_search` doesn't clamp `limit`; sibling handlers do.
- Task CLI's bespoke `_get_service()` skips `_register_db_kbs` — DB-
  registered KBs invisible to task CLI while MCP sees them.
- `pyrite mcp --help` claims 11 tools; actual is 48.

Tier-placement question to settle while in here: `kb_index_sync` is
ADMIN-tier — verify write-tier `kb_create` reliably auto-indexes,
else a write-tier agent can create entries it can then never find.

## Solution

1. Inventory MCP tools (`pyrite/server/mcp_server.py:_build_read_tools`,
   `_build_write_tools`, `_build_admin_tools`), the REST endpoint list
   (`pyrite/server/endpoints/`), AND the CLI command tree. Produce a
   three-surface parity matrix (the CLI-axis section above is the seed).
2. For each MCP-only tool, decide: port to REST, or document as MCP-only
   with rationale (e.g., bulk operations that don't fit HTTP idioms).
3. Port the agreed set as REST endpoints. Share the underlying service-
   layer call — both surfaces should delegate to the same service method.
4. Add a CI check that flags MCP tools without a corresponding REST entry
   in a small registry, so this gap can't reopen silently.

## Out of scope

Full code-generation from a unified tool schema (proposed in earlier ADR
sketches). That's a larger project; this ticket is the pragmatic step.

## Progress

- [x] **Tier-placement question settled** (2026-07-04) — verified
  `kb_create` (both MCP `_kb_create` and any future REST caller) goes
  through the shared `KBService.create_entry`, which calls
  `DocumentManager.save_entry` — confirmed (existing code comment +
  `test_document_manager.py::test_save_entry_writes_file_and_indexes`)
  that `save_entry` always indexes on write. A write-tier agent's
  created entries ARE immediately findable; no bug here. `kb_index_sync`
  staying admin-tier is correct — it's for *rebuilding* the index
  (`index sync`/`index build` semantics), not a prerequisite for a
  single create to be searchable.
- [x] **`kb_batch_read` — discovered already ported, ticket claim was
  stale** (2026-07-04) — `POST /api/entries/batch`
  (`pyrite/server/endpoints/entries.py:316`) already exists and calls
  the exact same `KBService.get_entries(ids)` method the MCP
  `_kb_batch_read` handler uses. No web UI consumer wired up yet (see
  remaining acceptance criteria below), but the REST/MCP parity gap
  itself is already closed for this tool.
- [x] **`kb_discover_neighbors` ported to REST** (2026-07-04) — new
  `GET /api/links/discover-neighbors` in new
  `pyrite/server/endpoints/links.py`, calling the same
  `LinkDiscoveryService.discover_neighbors()` the MCP handler uses (no
  service-layer duplication). New DI factory `get_link_discovery_service`
  in `api.py`. 3 tests in new `tests/test_link_discovery_endpoints.py`
  (happy path with real cross-KB shared-tag data from existing
  `sample_events`/`sample_person` fixtures, missing `entry_id` →422,
  missing `kb` →422 — FastAPI's own required-Query validation, correct
  REST semantics, not a custom 400).
- [x] **`kb_batch_suggest` ported to REST** (2026-07-04) — new
  `GET /api/links/batch-suggest` in the same `links.py`, calling
  `LinkDiscoveryService.batch_suggest()`. Same test file, 3 more
  tests.
- [x] **`task_claim` ported to REST** (2026-07-04) — new
  `POST /api/tasks/{task_id}/claim` in new
  `pyrite/server/endpoints/tasks.py`, calling the same
  `TaskService.claim_task()` the MCP `_task_claim` handler uses. Gated
  `requires_kb_tier("write")` (a claim mutates entry status/assignee).
  New DI factory `get_task_service`. Returns `claimed: false` (HTTP
  200, not an error status) for already-claimed/not-found — matching
  the underlying CAS's own contract (`KBService.claim_entry` never
  raises for these expected outcomes). 3 tests in new
  `tests/test_task_claim_endpoint.py` (claim succeeds, second claim on
  an already-claimed task reports the conflict, claiming a
  nonexistent task reports not-found — none as HTTP errors, all as
  200 + structured body, matching MCP's own behavior).
- [ ] **Parity matrix doc** (`kb/components/api-mcp-parity.md`) — not
  written this pass. The CLI-axis section above (already in this
  ticket body) is a reasonable seed; formalizing it as a standalone,
  maintained doc is separate work.
- [ ] **Web UI consumer for each newly-ported endpoint** — not wired
  up. This is a `web/` frontend task; per this epic's file-footprint
  discipline (a concurrent session may own `web/*` work), left
  unstarted rather than touching frontend code without coordinating.
- [ ] **CI check flagging new MCP-only tools without a REST match** —
  not implemented. Needs a small registry/manifest design (which MCP
  tools are *intentionally* MCP-only, e.g. bulk operations that don't
  fit HTTP idioms, vs. which need porting) before a CI check can
  distinguish "expected gap" from "regression" — that registry design
  is itself nontrivial and deserves its own pass.

Scope note: this session ported the 3 concrete tool gaps named in the
ticket's own acceptance criteria (`kb_batch_suggest`,
`kb_discover_neighbors`, `task_claim`) plus discovered `kb_batch_read`
was already done. Deliberately did NOT attempt the matrix doc, web UI
wiring, or CI check in this pass — each is a separate, non-trivial
piece of work in its own right, and bundling them into an unattended
sweep risked shallow, unreviewed output on the parts that need real
design judgment (especially the CI-check registry).

## Acceptance criteria

- Parity matrix in `kb/components/api-mcp-parity.md` (or as ADR
  appendix). **Not done.**
- At least `kb_batch_suggest`, `kb_discover_neighbors`, `task_claim`,
  and `kb_batch_read` ported to REST. **Met** — all 4 now have REST
  endpoints (`kb_batch_read` was already done; the other 3 ported this
  session), verified live (endpoints appear in `app.openapi()["paths"]`,
  9 new/confirmed passing tests).
- Web UI uses the new REST endpoints (verify one consumer for each).
  **Not done** — no web UI wiring in this pass.
- Service-layer dedup: both surfaces call the same method. **Met** —
  every new endpoint calls the identical service method the MCP
  handler already uses; zero service-layer duplication introduced.
- CI flag for new MCP-only tools (basic registry check). **Not done.**

## Related

- `epic-investigation-ui-views` — many of those views need these tools
- `epic-web-ui-task-management` — needs `task_claim` over REST
