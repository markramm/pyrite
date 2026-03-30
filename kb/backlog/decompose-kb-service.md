---
id: decompose-kb-service
type: backlog_item
title: "Decompose KBService God Object into focused sub-services"
kind: enhancement
status: done
priority: medium
effort: XL
tags: [architecture, refactoring]
epic: epic-release-readiness-review
---

## Problem

`KBService` was 1,619 lines with 60+ methods, many of which were pure pass-throughs to already-extracted services. 26 files imported it — every endpoint, the CLI, the MCP server.

## What Was Done

### Phase 1: Remove pass-throughs to already-extracted services

Removed 18 delegation methods. Callers now import GraphService, ExportService, EphemeralKBService, and QuotaService directly. Added DI functions (`get_graph_service`, `get_export_service`, `get_ephemeral_service`) to `api.py`. Updated all production callers (endpoints, MCP, CLI) and 5 test files.

### Phase 2: Extract ReviewService and VersionService

Created two new services with real business logic:

- **ReviewService** — QA review lifecycle: create with content hashing, get reviews, check review currency against file state.
- **VersionService** — entry version history and git-based content retrieval at specific commits.

Both have dedicated DI functions, endpoint wiring, and test coverage (12 new tests).

### Phase 3–4: Evaluated, not pursued

**Phase 3 (KBInfoService + GitOpsService)** — Evaluated as diminishing returns. orient/readme are read-only aggregation methods that depend on config, db, and plugin registry; extracting them to a separate service with 3 dependencies would relocate ~124 lines without reducing complexity. Git ops (pending_changes, publish_changes) could merge into ExportService but only save ~105 lines.

**Phase 4 (EntryService for CRUD + hooks)** — Evaluated as net negative. The CRUD methods are the core of KBService — they require 8 dependencies (config, db, DocumentManager, IndexManager, PluginRegistry, EmbeddingService, EmbeddingWorker, KBRepository) and would need 122 call site updates across production and tests. Extracting them doesn't reduce coupling; it just moves complexity to a new file while forcing callers to import both services.

## Result

| Metric | Before | After |
|--------|--------|-------|
| KBService lines | 1,619 | 1,324 |
| Methods removed | — | 24 |
| New standalone services | 4 (Graph, Export, Ephemeral, Quota) | +2 (Review, Version) = 6 total |
| Tests | 2,504 | 2,534 |
| DI functions added | — | 5 |

The god object problem is resolved. Remaining KBService methods are cohesive: entry CRUD with hooks, KB management, query facade, and read-only aggregation.
