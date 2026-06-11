---
id: qa-coverage-mcp-tool-inline-reference-source-detection-cross-kb-compare-r2300-follow-ups
title: 'qa coverage: MCP tool + inline-reference source detection + cross-KB compare (r2300 follow-ups)'
type: backlog_item
tags:
- curation
- mcp
- cli
- search
importance: 5
status: proposed
priority: medium
rank: 0
---

Follow-up from r2300 curation-audit-queries, which landed the same-KB stats slice: pyrite qa coverage <kb> command + QAAnalyticsService.coverage_stats returning by_type / by_status / body_coverage / link_coverage / source_coverage. Tests pin the contract in tests/test_qa_coverage_stats.py (9 cases).

Remaining ticket asks:

1. **MCP tool for agent-driven curation planning.** Expose qa_coverage as a read-tier MCP tool so agents (conductor, researcher subagents) can pull KB health numbers without shelling. Shape: {kb_name, entry_type?} -> the same dict the service returns. Add to pyrite/server/mcp_server.py and wire register on the read tier.

2. **Inline-reference source detection.** Ticket distinguishes structured sources (the source: frontmatter field; the source table; what we measure today) from inline references like EFTA IDs, court filing numbers, GAO docket numbers buried in body prose. Proposal:
   - kb.yaml gets source_patterns: [regex1, regex2, ...] config
   - QAAnalyticsService.coverage_stats walks each entry body and counts matches per pattern
   - Output adds inline_source_coverage: {with_inline, by_pattern: {pattern: count}, total, fraction} alongside source_coverage (structured)
   - Design Q: does an inline reference count if it appears once, or N times? Once per entry, once per match? Defer until a real workflow surfaces the call.

3. **Cross-KB compare view.** pyrite qa coverage --all to compare KBs side by side. Useful for the ticket's example: 'this KB is 47% sourced vs cascade-timeline at 99%.' Implementation: iterate config.knowledge_bases, build a table.

4. **TTL cache for large KBs.** Ticket suggests caching stats since they're expensive on large KBs. At HEAD the queries run in <100ms on a 663-entry KB; caching only matters if someone runs coverage in a tight loop. Defer unless observed.

5. **Per-type sourcing rate as a separate display block.** Ticket's example output shows 'Sourced: 47.8% (structured) + 31.2% (inline refs) = 79.0% effective' — that combined view depends on (2) landing first.

Acceptance per cite:
  - MCP tool callable, returns the same shape as the service
  - kb.yaml source_patterns parsed and applied
  - --all cross-KB view
  - End-to-end test for each surface

Effort: M overall; could split into 3 separate fires (MCP plumbing, inline-source detection, cross-KB view).
