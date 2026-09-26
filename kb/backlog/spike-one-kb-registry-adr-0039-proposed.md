---
id: spike-one-kb-registry-adr-0039-proposed
title: 'Spike: one KB registry (ADR-0039, proposed)'
type: backlog_item
tags:
- architecture
- quality
importance: 5
kind: spike
status: proposed
priority: high
effort: M
rank: 0
---

Retro 14 design theme, approved by the maintainer 2026-09-26. Runs after security batch 3b.

A KB's registration lives in three places: config.yaml, the DB kb table, and the in-memory _db_kb_cache. That is the root of private #61/#69, the characterization-harness leaks (#507, #509) and the 'two rules for public' hardening item. Deliverable: ADR-0039 (proposed) giving one source of truth for KB membership and per-KB policy (default_role, path, source, published), one read path, an explicit invalidation event consumed by the policy, /site, /ws, MCP sessions and the test world, plus an invariant list in the style of ADR-0038's I1-I10.
