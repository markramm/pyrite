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

## Solution

1. Inventory MCP tools (`pyrite/server/mcp_server.py:_build_read_tools`,
   `_build_write_tools`, `_build_admin_tools`) and the REST endpoint list
   (`pyrite/server/endpoints/`). Produce a parity matrix.
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
