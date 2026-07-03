---
id: in-band-degradation-signaling
type: backlog_item
title: "In-band degradation signaling: warnings must reach CLI/MCP consumers, not just server logs"
kind: improvement
status: proposed
priority: high
effort: M
created: "2026-07-03"
tags: [agent-dx, errors, warnings, cli, mcp, reliability]
links:
- target: epic-shared-instance-readiness
  relation: related
  kb: pyrite
- target: fail-open-exception-sweep
  relation: related
  kb: pyrite
- target: docs-operational-contracts-travel-with-tool
  relation: related
  kb: pyrite
---

## Problem

Operator decision, 2026-07-03 (from the fail-open sweep): "logs are
not available to agents using the CLI — silent should also think
about user notification."

The fail-open sweep is converting silent swallows into
`logger.warning` — necessary, but for the primary consumers (fleet
agents via CLI/MCP, pilot peers' agents via MCP) a server-side log
line is still functionally silent. Any degradation that changes
user-visible behavior (a check skipped, a plugin disabled for a KB,
an entry dropped from index coverage, a fallback search mode) must
surface **in-band**, in the response the consumer actually reads.

Precedent that works: the stale-index fix (8f97f96) prints a stderr
warning while keeping stdout JSON clean — humans see it, JSON
parsers aren't broken by it. Generalize it.

## Fix

1. **Contract:** add an optional `warnings` array to the JSON
   success envelopes: `warnings: [{code, message, suggestion?}]` —
   same field names as the error contract (`pyrite/utils/errors.py`),
   present only when non-empty. Rich/text mode renders them as
   stderr warning lines (stdout stays parseable).
2. **MCP:** same `warnings` array in tool results (agents see it in
   the tool response; no log access needed). Audit the MCP handlers
   for the same swallow class the CLI sweep found — the dispatch
   boundary currently converts unexpected exceptions to
   INTERNAL/retryable, but mid-handler degradations (partial results,
   skipped KBs) have no channel at all today.
3. **REST + web UI:** REST responses carry the same `warnings`
   array; the web UI grows a notification affordance for them
   (operator note 2026-07-03: "web UI needs a notifications system
   for this kind of warning"). Two tiers: transient warnings render
   via the existing Toast component; STANDING degradations (stale
   index, plugin skipped for a KB, drift detector degraded) get a
   persistent indicator — a small status chip in the sidebar footer
   (next to the existing "v0.9 · synced" affordance) opening a
   notification list, so a degradation that outlives the request
   isn't a toast someone missed. Semantic warn color, never brand
   gold.
4. **Adopt at the sweep sites** where the degradation affects
   results: registry-merge failure (KBs missing from the surface),
   drift-detector degradation (check partially skipped), plugin
   compat-check failure → plugin skipped (see decision in
   [[plugin-type-resolution-scoping]]), parse-path entry drops,
   search silent file-search fallback (this one currently MASKS
   index corruption — it becomes a warning-carrying degraded result
   or an error, never silent).
5. **Document** the field in the JSON-contracts page
   ([[docs-operational-contracts-travel-with-tool]]) and in `orient`
   so agents know to check it.

## Acceptance criteria

- A degraded operation returns exit 0 (when results are still
  usable) with a machine-readable `warnings` array on JSON/MCP and a
  stderr line on human output — verified by the existing
  fault-injection tests extended to assert the in-band signal, not
  just the log.
- No site in the fail-open sweep's list degrades user-visible
  behavior with log-only notification.
