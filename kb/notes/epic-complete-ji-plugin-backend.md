---
id: epic-complete-ji-plugin-backend
title: 'Epic: Complete JI Plugin Backend'
type: backlog_item
tags:
- epic
- journalism
- investigation
kind: epic
status: accepted
priority: high
effort: XL
---

## Overview

Complete all remaining backend work for the journalism-investigation plugin across 4 waves.

## Wave 1 — Graph Queries (parallel)
- ji-beneficial-ownership-chains (M): Ownership chain traversal, % calculation, shell detection
- ji-money-flow-queries (M): Transaction chain traversal, aggregate flows, circular detection
- ji-bulk-edge-creation (S): Batch create connections with atomic validation

## Wave 2 — Cross-KB & Interop (parallel)
- ji-cross-kb-entity-dedup (M): Fuzzy matching, same_as links, review mode
- ji-ftm-import-export (L): FollowTheMoney JSON import/export for Aleph
- ji-investigation-pack-export (M): Export investigation as HTML/PDF/JSON/Markdown

## Wave 3 — Cascade Integration (sequential → parallel)
- ji-cascade-entry-type-inheritance (M): Cascade types extend JI base types
- ji-cascade-mcp-tool-delegation (S): Cascade MCP wraps JI tools
- ji-cascade-migration-and-compat (S): Backward compat for existing KBs

## Wave 4 — Agent Skills (parallel)
- ji-fact-checker-skill (L): Claim verification skill
- ji-research-executor-skill (L): Web research skill
- ji-network-mapper-skill (L): Relationship discovery skill

## Status
- 12 items total across 4 waves
