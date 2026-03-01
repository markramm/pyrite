---
type: note
title: "Pyrite Prioritized Backlog"
tags: [backlog, roadmap]
---

# Pyrite Prioritized Backlog

Active items in priority order across three tracks: **UI** (web application features), **AI** (agent workflows, LLM integration), and **Core** (data model, storage, schema). See [[roadmap]] for milestone themes and definitions of done.

---

## Prioritized Next Up

Recommended execution order. Grouped by milestone.

**0.11 — ODM Completion:**

| Priority | Item | Effort | Rationale |
|----------|------|--------|-----------|
| **1** | [[schema-versioning]] | M | Pre-launch critical — first schema change after launch breaks every KB |
| **2** | [[odm-layer]] DocumentManager | M | Route KBService through DocumentManager — completes the abstraction |
| **3** | [[architecture-hardening]] | M | DDL validation, layer violations, stale docs |

**0.12 — Launch Prep:**

| Priority | Item | Effort | Rationale |
|----------|------|--------|-----------|
| **6** | [[pypi-publish]] | S | `pip install pyrite` as the golden path |
| **7** | [[mcp-submission-update]] | XS | Accurate listing for MCP registry |
| **8** | [[web-ui-auth]] Phase 1 | M | Local auth + tiers — required for demo site |
| **9** | [[mcp-rate-limiting]] | S | Required for public-facing demo site |
| **10** | [[demo-site-deployment]] | M | Live demo for visitors (needs #94, #97, #91 ✅) |
| **11** | [[byok-ai-gap-analysis]] | M | All AI features work with user-provided keys |
| **12** | [[pyrite-ci-command]] | S | CI/CD schema + link validation |
| **13** | Getting Started tutorial | S | Newcomer-friendly onboarding |

**0.13 — Ecosystem:**

| Priority | Item | Effort | Rationale |
|----------|------|--------|-----------|
| **14** | [[software-project-plugin]] | L | Evolves from software-kb, grabs dev team eyeballs |
| **15** | [[investigative-journalism-plugin]] | XL | Proves general-purpose, different audience |
| **16** | [[extension-registry]] | M | Public directory for sharing extensions |
| **17** | [[extension-type-protocols]] Phase 1 | L | Protocol definitions for extension types |
| **18** | [[obsidian-migration]] | M | Import from Obsidian vaults |
| **19** | [[pkm-capture-plugin]] | L | Personal knowledge management capture |

**Future:**

| Priority | Item | Effort | Rationale |
|----------|------|--------|-----------|
| **20** | [[intent-layer]] | M | Guidelines, goals, rubrics for entry quality |
| **21** | [[event-bus-webhooks]] | M | Integration story, live graph updates |
| **22** | [[kb-orchestrator-skill]] | M | Multi-KB agent coordination pattern |
| **23** | [[db-backup-restore]] | S | Operational tooling |

---

## Open Items

### In Progress

| # | Item | Kind | Effort | Status | Notes |
|---|------|------|--------|--------|-------|
| 100 | [[odm-layer]] | feature | L | in progress | Phase 1 (SearchBackend) done, Phase 3 (LanceDB) rejected, Phase 4 (Postgres) done. Remaining: DocumentManager |
| 79 | [[coordination-task-plugin]] | feature | XL | in progress | Phases 1-2 done. Remaining: Phase 3 (DAG queries), Phase 4 (QA integration) |

### Planned — 0.11

| # | Item | Kind | Effort | Milestone |
|---|------|------|--------|-----------|
| 93 | [[schema-versioning]] | feature | M | 0.11 |
| 106 | [[architecture-hardening]] | improvement | M | 0.11 |

### Planned — 0.12

| # | Item | Kind | Effort | Milestone |
|---|------|------|--------|-----------|
| 74 | [[pypi-publish]] | feature | S | 0.12 |
| 85 | [[demo-site-deployment]] | feature | M | 0.12 |
| 86 | [[pyrite-ci-command]] | feature | S | 0.12 |
| 87 | [[byok-ai-gap-analysis]] | improvement | M | 0.12 |
| 89 | [[mcp-submission-update]] | improvement | XS | 0.12 |
| 94 | [[web-ui-auth]] | feature | M | 0.12 |
| 97 | [[mcp-rate-limiting]] | feature | S | 0.12 |

### Planned — 0.13

| # | Item | Kind | Effort | Milestone |
|---|------|------|--------|-----------|
| 82 | [[software-project-plugin]] | feature | L | 0.13 |
| 83 | [[investigative-journalism-plugin]] | feature | XL | 0.13 |
| 84 | [[extension-registry]] | feature | M | 0.13 |
| 88 | [[obsidian-migration]] | feature | M | 0.13 |
| 90 | [[pkm-capture-plugin]] | feature | L | 0.13 |
| 99 | [[extension-type-protocols]] | feature | L | 0.13 |

### Planned — Future

| # | Item | Kind | Effort |
|---|------|------|--------|
| 92 | [[intent-layer]] | feature | M |
| 95 | [[event-bus-webhooks]] | feature | M |
| 96 | [[db-backup-restore]] | feature | S |
| 98 | [[kb-orchestrator-skill]] | feature | M |

### Open Phases (blocked or deferred)

| # | Item | Status | Blocked by |
|---|------|--------|------------|
| 60 | [[block-refs-phase3-transclusion]] | proposed | #59 ✅ (ready to start) |
| 64 | [[collections-phase4-embedding]] | proposed | #60 |
| 73 | [[qa-agent-workflows]] Phases 3-5 | deferred | Phase 2 done, Phases 3-5 post-launch |

### Remaining Hardening (unscheduled)

| # | Item | Kind | Effort |
|---|------|------|--------|
| 102 | [[silent-error-logging]] | improvement | M |
| 103 | [[test-coverage-gaps]] | improvement | L |
| 105 | [[ux-accessibility-fixes]] | improvement | M |

---

## Dependencies (open items only)

```
schema-versioning (#93)              [0.11]
  └── depends on odm-layer (#100) Phase 1 ✅

odm-layer (#100)                     [0.11] — Phase 1 ✅, Phase 3 ✗, Phase 4 ✅
  └── Phase 2: DocumentManager       — remaining work

web-ui-auth (#94)                    [0.12]
  Phase 1: local auth + tiers        — needs #56 ✅ (REST tier enforcement)
  Phase 2: OAuth/OIDC                — post-launch

demo-site-deployment (#85)           [0.12] — needs #94, #97, #91 ✅

extension-type-protocols (#99)       [0.13]
  Phase 1: protocol definitions      — needs #92 (intent layer)
  Phase 2: satisfaction checking     — needs Phase 1
  Phase 3: registry integration      — needs #84 (extension registry)

extension-registry (#84)             [0.13] — needs demo site (#85)

coordination-task-plugin (#79)       — Phases 1-2 ✅
  Phase 3: DAG queries               [future]
  Phase 4: QA integration            [future, after #73 Phase 2]

qa-agent-workflows (#73)             — Phases 1-2 ✅
  Phase 3: LLM consistency checks    [future]
  Phase 4: factual verification      [future]
  Phase 5: continuous QA pipeline    [future]

block-refs-phase3 (#60)              — ready to start
  └── collections-phase4 (#64)       — blocked by #60

kb-orchestrator-skill (#98)          [future] — needs #79 Phase 2, #92 Phase 1
intent-layer (#92)                   [future] — phase 1 no blockers
```

---

## Retired

Items subsumed by larger features:

| # | Item | Subsumed by | Reason |
|---|------|-------------|--------|
| 28 | [[dataview-queries]] | #51 Collections Phase 2 | Virtual collections with `source: query` are dataview |
| 29 | [[database-views]] | #51 Collections Phase 3 | Collection view types cover table, kanban, gallery |
| 43 | [[display-hints-for-types]] | #51 Collections Phase 1 | View configuration is per-collection, not just per-type |

---

## Future Ideas

Lower-priority items in [`future-ideas/`](future-ideas/):

- [[web-ai-writing-assist]] — Select text → AI summarize/expand/rewrite/continue
- [[offline-and-performance]] — IndexedDB cache, virtual scrolling, service worker
- [[canvas-whiteboard]] — Freeform spatial canvas for visual thinking
- [[sync-conflict-resolution-ui]] — Visual merge conflict resolution

- [[engagement-federation]] — Sync engagement data across instances
- [[graph-betweenness-centrality]] — Size nodes by BC to highlight bridging entries
- [[graph-community-detection]] — Detect topical clusters, color by community
- [[graph-structural-gap-detection]] — Find missing links between distant clusters
- [[graph-influence-per-occurrence]] — Surface entries with outsized connective importance

---

## Bugs

| # | Item | Status |
|---|------|--------|
| 66 | [[health-check-timezone-fix]] | **done** |
| 67 | [[create-body-file-nested-yaml-bug]] | **done** |

---

## Completed Waves (1-12)

All items below are done. Detail lives in the individual backlog item files in [`done/`](done/).

### Wave 1 — Foundation
[[ruamel-yaml-migration]], [[claude-code-plugin]], [[wikilinks-and-autocomplete]], [[api-security-hardening]]

### Wave 2 — Core Features
[[structured-data-schema]], [[llm-abstraction-service]], [[quick-switcher-and-command-palette]], [[templates-system]], [[starred-entries]], [[plugin-developer-guide]]

### Wave 3A — Parallel Features
[[entry-factory-deduplication]], [[backlinks-and-split-panes]], [[daily-notes]]

### Wave 3B — Core Cleanup
[[split-database-module]] → [[service-layer-enforcement]] → [[cli-service-layer]] → [[test-improvements]]

### Wave 4 — Service Layer Features
[[type-metadata-and-ai-instructions]], [[mcp-prompts-and-resources]], [[slash-commands]], [[content-negotiation-and-formats]]

### Wave 5A — Skills
[[research-flow-skill]], [[investigation-skill]], [[pyrite-dev-skill]], [[readme-rewrite]]

### Wave 5B — UI Features
[[callouts-and-admonitions]], [[outline-table-of-contents]], [[timeline-visualization]], [[legacy-file-cleanup]]

### Wave 5C — Core Infrastructure
[[custom-exception-hierarchy]], [[plugin-dependency-injection]], [[hooks-db-access-gap]], [[standalone-mcp-packaging]]

### Wave 5D — Data Model
[[typed-object-references]], [[tag-hierarchy]], [[settings-and-preferences]], [[version-history]]

### Wave 6A — Graph + Realtime
[[knowledge-graph-view]], [[websocket-multi-tab]], [[tiptap-wysiwyg-editor]]

### Wave 6B — AI Features
[[web-ai-summarize-and-tag]], [[ai-provider-settings-ui]], [[web-ai-chat-sidebar]], [[ephemeral-kbs]], [[cross-kb-shortlinks]]

### Wave 6C — Plugin UI + Import/Export
[[plugin-ui-hooks]], [[import-export]]

### Wave 7A — Access Control
[[implement-pyrite-read-cli]], [[mcp-commit-tool]], [[rest-api-tier-enforcement]], [[background-embedding-pipeline]]

### Wave 7B — DB Transactions
[[database-transaction-management]]

### Wave 7C — Block References (Phases 1-2)
[[block-refs-phase1-storage-and-heading-links]], [[block-refs-phase2-block-id-references]]

### Wave 7D — Collections (Phases 1-3, 5)
[[collections-phase1-foundation]], [[collections-phase2-virtual-collections]], [[collections-phase3-rich-views]], [[collections-phase5-plugin-types]]

### Wave 9 — MCP Hardening
[[entry-type-mismatch-event-vs-timeline-event]], [[mcp-link-creation-tool]], [[mcp-large-result-handling]], [[mcp-bulk-create-tool]], [[capture-lane-validation-via-kb-yaml-controlled-vocabulary]]

### Wave 10 — QA (Phases 1-2)
[[qa-agent-workflows]] — QAService, 9 validation rules, assessment entries, post-save validation

### Wave 11 — Agent CLI (0.5)
[[headless-kb-init]], [[cli-json-output-audit]], [[extension-init-cli]], [[extension-install-cli]]

### Wave 12 — Agent Coordination (0.6)
[[coordination-task-plugin]] Phases 1-2, [[programmatic-schema-provisioning]], Plugin KB-Type Scoping

### Also Completed
[[web-server-implementation]], [[cli-entry-point-consolidation]], [[extension-builder-skill]], [[entry-aliases]], [[web-clipper]], [[postgres-storage-backend]], [[docs-kb-fixes]], [[test-infrastructure]]
