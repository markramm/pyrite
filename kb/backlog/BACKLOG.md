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

**0.12 — Distribution (done):**

| Priority | Item | Effort | Status |
|----------|------|--------|--------|
| **1** | [[pypi-publish]] | S | **done** |
| **2** | [[mcp-submission-update]] | XS | pending |

**0.13 — Human & Agent UX Hardening:**

*Web UI:*

| Priority | Item | Effort | Rationale | Status |
|----------|------|--------|-----------|--------|
| **1** | [[web-ui-logout-button]] | XS | No logout = blocked users | **done** |
| **2** | [[web-ui-version-history-fix]] | XS | Broken feature | **done** |
| **3** | [[web-ui-type-colors-consolidation]] | XS | Deduplicate type→color mappings | **done** |
| **4** | [[web-ui-page-titles]] | XS | Missing browser tab titles | **done** |
| **5** | [[web-ui-dead-code-cleanup]] | XS | Remove unused code | **done** |
| **6** | [[web-ui-loading-states]] | S | Standardize loading indicators | **done** |
| **7** | [[web-ui-accessibility-fixes]] | S | aria-labels, keyboard nav | **done** |
| **8** | [[web-ui-mobile-responsive]] | S | Mobile viewport fixes | **done** |
| **9** | [[web-ui-collections-save]] | S | Save collection views | **done** |
| **10** | [[web-ui-first-run-experience]] | S | Empty-state onboarding | **done** |
| **11** | [[web-ui-starred-entries]] | S | Restore starred entries feature | **done** |
| **12** | [[ux-accessibility-fixes]] | M | Original accessibility audit items | **done** |
| **13** | [[playwright-integration-tests]] | M | E2E test coverage | **done** |
| **14** | [[web-ui-review-hardening]] | S | Final pre-launch UI gate | **done** |

*Agent DX (CLI + MCP + REST):* **All done.**

| Priority | Item | Effort | Status |
|----------|------|--------|--------|
| **14** | [[bug-mcp-kb-create-places-entries-at-kb-root-instead-of-type-directory]] | S | **done** |
| **15** | [[bug-kb-update-mcp-tool-returns-posixpath-serialization-error]] | S | **done** |
| **16** | [[mcp-tool-kb-batch-read-for-multi-entry-retrieval-in-one-call]] | S | **done** |
| **17** | [[mcp-search-add-fields-parameter-for-token-efficient-results]] | M | **done** |
| **18** | [[mcp-tool-kb-list-entries-for-lightweight-kb-index-browsing]] | M | **done** |
| **19** | [[mcp-tool-kb-recent-for-what-changed-orientation-queries]] | M | **done** |
| **20** | [[clarify-metadata-vs-top-level-field-mapping-in-mcp-create-update-tools]] | M | **done** |
| **21** | [[agent-oriented-error-responses-across-cli-and-mcp]] | L | **done** |

**0.14 — Auth & Rate Limiting:**

| Priority | Item | Effort | Rationale |
|----------|------|--------|-----------|
| **1** | [[mcp-rate-limiting]] | S | Required for public-facing endpoints |
| **2** | [[oauth-providers]] Phase 1 | L | GitHub OAuth — "Sign in with GitHub" |
| **3** | [[per-kb-permissions]] | L | Per-KB ACL + ephemeral KB sandbox |

**0.15 — Deployment & Demo:**

| Priority | Item | Effort | Rationale |
|----------|------|--------|-----------|
| **1** | [[container-deployment]] Phase 1 | M | Dockerfile + Docker Compose |
| **1a** | [[container-deployment]] Phase 2 | S | Deploy-to-Railway/Render/Fly buttons |
| **2** | [[pyrite-website]] | M | Marketing site + docs at pyrite.dev |
| **3** | [[demo-site-deployment]] | M | Live demo at demo.pyrite.dev |
| **4** | [[byok-ai-gap-analysis]] | M | All AI features work with user-provided keys |

**0.16 — Ecosystem & Onboarding (launch release):**

| Priority | Item | Effort | Rationale |
|----------|------|--------|-----------|
| **1** | [[plugin-repo-extraction]] | M | Extract 5 extensions to PyPI |
| **2** | [[personal-kb-repo-backing]] | M | Export KB to GitHub repo + tiers |
| **3** | Getting Started tutorial | S | Newcomer-friendly onboarding |
| **4** | [[plugin-writing-tutorial]] | S | Build a plugin with Claude Code |
| **5** | [[awesome-plugins-page]] | XS | Curated plugin listing |
| **6** | [[pyrite-ci-command]] | S | CI/CD schema + link validation |

**0.17 — Ecosystem:**

| Priority | Item | Effort | Rationale |
|----------|------|--------|-----------|
| **1** | [[software-project-plugin]] | L | Evolves from software-kb, grabs dev team eyeballs |
| **2** | [[investigative-journalism-plugin]] | XL | Proves general-purpose, different audience |
| **3** | [[extension-registry]] | M | Public directory for sharing extensions |
| **4** | [[extension-type-protocols]] Phase 1 | L | Protocol definitions for extension types |
| **5** | [[obsidian-migration]] | M | Import from Obsidian vaults |
| **6** | [[pkm-capture-plugin]] | L | Personal knowledge management capture |

**Post-launch — KB Quality & Lifecycle:**

| Priority | Item | Effort | Rationale |
|----------|------|--------|-----------|
| **1** | [[entry-lifecycle-field-and-search-filtering]] | S | Archive entries without deleting, filter from search |
| **2** | [[kb-compaction-command-and-freshness-qa-rules]] | S | Detect archival candidates, type-aware staleness |

**Future:**

| Priority | Item | Effort | Rationale |
|----------|------|--------|-----------|
| **1** | [[intent-layer]] | M | Guidelines, goals, rubrics for entry quality |
| **2** | [[event-bus-webhooks]] | M | Integration story, live graph updates |
| **3** | [[kb-orchestrator-skill]] | M | Multi-KB agent coordination pattern |
| **4** | [[db-backup-restore]] | S | Operational tooling |
| **5** | [[search-relevance-boost-by-entry-type]] | M | Type-aware search ranking + intent integration |

---

## Open Items

### In Progress

| # | Item | Kind | Effort | Status | Notes |
|---|------|------|--------|--------|-------|
| 79 | [[coordination-task-plugin]] | feature | XL | in progress | Phases 1-2 done. Remaining: Phase 3 (DAG queries), Phase 4 (QA integration) |

### Planned — 0.12 (done)

| # | Item | Kind | Effort | Milestone | Status |
|---|------|------|--------|-----------|--------|
| 74 | [[pypi-publish]] | feature | S | 0.12 | **done** |
| 89 | [[mcp-submission-update]] | improvement | XS | 0.12 | pending |
| 94 | [[web-ui-auth]] Phase 1 | feature | M | 0.12 | **done** |

### Planned — 0.13 (Human & Agent UX Hardening) — all done

| # | Item | Kind | Effort | Milestone | Status |
|---|------|------|--------|-----------|--------|
| — | [[web-ui-logout-button]] | bug | XS | 0.13 | **done** |
| — | [[web-ui-version-history-fix]] | bug | XS | 0.13 | **done** |
| — | [[web-ui-type-colors-consolidation]] | improvement | XS | 0.13 | **done** |
| — | [[web-ui-page-titles]] | improvement | XS | 0.13 | **done** |
| — | [[web-ui-dead-code-cleanup]] | improvement | XS | 0.13 | **done** |
| — | [[web-ui-loading-states]] | improvement | S | 0.13 | **done** |
| — | [[web-ui-accessibility-fixes]] | improvement | S | 0.13 | **done** |
| — | [[web-ui-mobile-responsive]] | improvement | S | 0.13 | **done** |
| — | [[web-ui-collections-save]] | improvement | S | 0.13 | **done** |
| — | [[web-ui-first-run-experience]] | improvement | S | 0.13 | **done** |
| — | [[web-ui-starred-entries]] | improvement | S | 0.13 | **done** |
| 105 | [[ux-accessibility-fixes]] | improvement | M | 0.13 | **done** |
| — | [[playwright-integration-tests]] | feature | M | 0.13 | **done** |
| — | [[web-ui-review-hardening]] | improvement | S | 0.13 | **done** |
| — | [[bug-mcp-kb-create-places-entries-at-kb-root-instead-of-type-directory]] | bug | S | 0.13 | **done** |
| — | [[bug-kb-update-mcp-tool-returns-posixpath-serialization-error]] | bug | S | 0.13 | **done** |
| — | [[mcp-tool-kb-batch-read-for-multi-entry-retrieval-in-one-call]] | feature | S | 0.13 | **done** |
| — | [[mcp-search-add-fields-parameter-for-token-efficient-results]] | enhancement | M | 0.13 | **done** |
| — | [[mcp-tool-kb-list-entries-for-lightweight-kb-index-browsing]] | feature | M | 0.13 | **done** |
| — | [[mcp-tool-kb-recent-for-what-changed-orientation-queries]] | feature | M | 0.13 | **done** |
| — | [[clarify-metadata-vs-top-level-field-mapping-in-mcp-create-update-tools]] | improvement | M | 0.13 | **done** |
| — | [[agent-oriented-error-responses-across-cli-and-mcp]] | enhancement | L | 0.13 | **done** |

### Planned — 0.14 (Auth & Rate Limiting)

| # | Item | Kind | Effort | Milestone |
|---|------|------|--------|-----------|
| 97 | [[mcp-rate-limiting]] | feature | S | 0.14 |
| 110 | [[oauth-providers]] Phase 1 | feature | L | 0.14 |
| 112 | [[per-kb-permissions]] | feature | L | 0.14 |

### Planned — 0.15 (Deployment & Demo)

| # | Item | Kind | Effort | Milestone |
|---|------|------|--------|-----------|
| 114 | [[container-deployment]] | feature | M | 0.15 |
| 111 | [[pyrite-website]] | feature | M | 0.15 |
| 85 | [[demo-site-deployment]] | feature | M | 0.15 |
| 87 | [[byok-ai-gap-analysis]] | improvement | M | 0.15 |

### Planned — 0.16 (Ecosystem & Onboarding — launch release)

| # | Item | Kind | Effort | Milestone |
|---|------|------|--------|-----------|
| 107 | [[plugin-repo-extraction]] | feature | M | 0.16 |
| 113 | [[personal-kb-repo-backing]] | feature | M | 0.16 |
| — | Getting Started tutorial | feature | S | 0.16 |
| 108 | [[plugin-writing-tutorial]] | feature | S | 0.16 |
| 109 | [[awesome-plugins-page]] | feature | XS | 0.16 |
| 86 | [[pyrite-ci-command]] | feature | S | 0.16 |

### Planned — 0.17 (Ecosystem)

| # | Item | Kind | Effort | Milestone |
|---|------|------|--------|-----------|
| 82 | [[software-project-plugin]] | feature | L | 0.17 |
| 83 | [[investigative-journalism-plugin]] | feature | XL | 0.17 |
| 84 | [[extension-registry]] | feature | M | 0.17 |
| 88 | [[obsidian-migration]] | feature | M | 0.17 |
| 90 | [[pkm-capture-plugin]] | feature | L | 0.17 |
| 99 | [[extension-type-protocols]] | feature | L | 0.17 |

### Post-launch — KB Quality & Lifecycle

| # | Item | Kind | Effort |
|---|------|------|--------|
| — | [[entry-lifecycle-field-and-search-filtering]] | feature | S |
| — | [[kb-compaction-command-and-freshness-qa-rules]] | feature | S |
| — | [[knowledgeclaw-pyrite-powered-agent-for-openclaw-ecosystem]] | feature | XL |

### Planned — Future

| # | Item | Kind | Effort |
|---|------|------|--------|
| 92 | [[intent-layer]] | feature | M |
| 95 | [[event-bus-webhooks]] | feature | M |
| 96 | [[db-backup-restore]] | feature | S |
| 98 | [[kb-orchestrator-skill]] | feature | M |
| — | [[search-relevance-boost-by-entry-type]] | feature | M |

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

---

## Dependencies (open items only)

```
pypi-publish (#74)                   [0.12] ✅
  └── plugin-repo-extraction (#107)  [0.16] — needs #74 ✅
      ├── awesome-plugins-page (#109) [0.16] — needs #107
      └── plugin-writing-tutorial (#108) [0.16] — needs #107

web-ui-* items                       [0.13] ✅ — all done
  └── playwright-integration-tests   [0.13] ✅ — validates all UI fixes
      └── web-ui-review-hardening    [0.13] ✅ — final gate, moved from 0.15, done

web-ui-auth (#94)                    [0.12] ✅ Phase 1 done
  ├── oauth-providers (#110)         [0.14] — GitHub OAuth
  │   Phase 1: GitHub OAuth          — needs #94 ✅
  │   Phase 2: Google OAuth          — needs Phase 1
  │   Phase 3: Generic OIDC          — post-launch
  ├── per-kb-permissions (#112)      [0.14] — per-KB ACL + ephemeral sandboxes
  │   — needs #94 ✅, benefits from #110
  └── personal-kb-repo-backing (#113) [0.16] — repo-backed KBs + plan tiers
      — needs #110 (GitHub OAuth), #112 (per-KB perms)

container-deployment (#114)          [0.15] — no hard blockers
  Phase 1: Dockerfile + Compose      — no hard blockers
  Phase 2: Deploy buttons            — benefits from Phase 1

pyrite-website (#111)                [0.15] — no blockers
demo-site-deployment (#85)           [0.15] — needs #94 ✅, #97, #111, #112, #114

extension-type-protocols (#99)       [0.17]
  Phase 1: protocol definitions      — needs #92 (intent layer)
  Phase 2: satisfaction checking     — needs Phase 1
  Phase 3: registry integration      — needs #84 (extension registry)

extension-registry (#84)             [0.17] — needs demo site (#85)

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

entry-lifecycle-field-and-search-filtering  [post-launch] — no blockers
  └── kb-compaction-command-and-freshness-qa-rules  [post-launch] — needs lifecycle field
      └── search-relevance-boost-by-entry-type      [future] — needs compaction + intent layer
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

### Wave 13 — ODM Completion (0.11)
[[schema-versioning]], [[odm-layer]] DocumentManager, [[docs-kb-fixes]], [[architecture-hardening]], [[test-infrastructure]]

### Wave 14 — Agent DX (0.13)
[[bug-mcp-kb-create-places-entries-at-kb-root-instead-of-type-directory]], [[bug-kb-update-mcp-tool-returns-posixpath-serialization-error]], [[mcp-tool-kb-batch-read-for-multi-entry-retrieval-in-one-call]], [[mcp-search-add-fields-parameter-for-token-efficient-results]], [[mcp-tool-kb-list-entries-for-lightweight-kb-index-browsing]], [[mcp-tool-kb-recent-for-what-changed-orientation-queries]], [[clarify-metadata-vs-top-level-field-mapping-in-mcp-create-update-tools]], [[agent-oriented-error-responses-across-cli-and-mcp]]

### Wave 15 — Web UI Hardening (0.13)
[[web-ui-logout-button]], [[web-ui-version-history-fix]], [[web-ui-type-colors-consolidation]], [[web-ui-page-titles]], [[web-ui-dead-code-cleanup]], [[web-ui-loading-states]], [[web-ui-accessibility-fixes]], [[web-ui-mobile-responsive]], [[web-ui-collections-save]], [[web-ui-first-run-experience]], [[web-ui-starred-entries]], [[ux-accessibility-fixes]], [[playwright-integration-tests]], [[web-ui-review-hardening]]

### Also Completed
[[web-server-implementation]], [[cli-entry-point-consolidation]], [[extension-builder-skill]], [[entry-aliases]], [[web-clipper]], [[postgres-storage-backend]]
