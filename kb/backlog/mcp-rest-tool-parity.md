---
id: mcp-rest-tool-parity
type: backlog_item
title: "Audit MCP/REST parity: port missing tools so the web UI matches agent capability"
kind: improvement
status: proposed
priority: medium
effort: M
tags: [api, mcp, parity, web-ui, refactor]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
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

## Acceptance criteria

- Parity matrix in `kb/components/api-mcp-parity.md` (or as ADR appendix).
- At least `kb_batch_suggest`, `kb_discover_neighbors`, `task_claim`, and
  `kb_batch_read` ported to REST.
- Web UI uses the new REST endpoints (verify one consumer for each).
- Service-layer dedup: both surfaces call the same method.
- CI flag for new MCP-only tools (basic registry check).

## Related

- `epic-investigation-ui-views` — many of those views need these tools
- `epic-web-ui-task-management` — needs `task_claim` over REST
