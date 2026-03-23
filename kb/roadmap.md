---
id: roadmap
title: Pyrite Release Roadmap
type: note
tags:
- roadmap
- planning
---

# Pyrite Release Roadmap

## BHAG: Self-Configuring Knowledge Infrastructure for Agent Swarms

An autonomous agent encounters a domain, builds a Pyrite extension for it, provisions a KB, and starts working — all without human intervention. The schema is the program. Pyrite is the runtime. See [[bhag-self-configuring-knowledge-infrastructure]] for the full vision.

Every milestone below moves toward this goal.

---

## 0.3 — CLI Foundation (done)

Core CLI, storage layer, service architecture, plugin system (15-method protocol), three-tier MCP server, SvelteKit web UI, content negotiation, collections (phases 1-3, 5), block references (phases 1-2), background embedding pipeline, REST API tier enforcement. 1040 tests.

## 0.4 — MCP Server Hardening (done)

Production-solid MCP for agent workflows. Fixed metadata passthrough bugs, added capture lane validation (`allow_other` on FieldSchema), schema validation on all write paths. 1040 tests.

## 0.5 — QA & Agent CLI (done)

QAService with 9 structural validation rules. `--format json/markdown/csv/yaml` on 11 CLI commands. `pyrite init --template`, `pyrite extension init/install/list/uninstall`. 1086 tests.

## 0.6 — Agent Coordination (done)

Task plugin (7-state workflow, atomic `task_claim` via CAS, `task_decompose`, `task_checkpoint`). Plugin KB-type scoping. Programmatic schema provisioning. QA Phase 2 (assessment entries, post-save validation). 1154 tests.

## 0.7 — Web UI Polish (done)

QA dashboard, graph betweenness centrality, block-ID transclusions, collection embedding in transclusions, WebSocket live updates, cycle detection, transclusion view options, collection nesting. 1000+ entry performance test. 1179 backend + 115 frontend tests.

## 0.8 — UI Design & UX (done)

Brand identity (gold accent, DM Serif Display, "Py" monogram). Dashboard redesign with type distribution chart. Dedicated `/search` page. Responsive sidebar. Keyboard shortcuts modal. Template picker redesign. Page transitions. 1182 backend + 115 frontend tests.

## 0.9 — Code Hardening (done)

Internal quality pass across 8 waves. Key results: `mcp_server.py` 32% smaller (tool schemas extracted), `WikilinkService` extracted from `KBService`, 24 `_raw_conn` calls eliminated, 43 bare `except: pass` replaced with logging, SQL DDL injection prevention, stale `docs/` directory deleted. 1654 backend + 115 frontend tests.

---

## 0.10 — SearchBackend Protocol + PostgresBackend (done)

**Theme:** Pluggable storage backends via a clean protocol abstraction. See [ADR-0014](adrs/0014-structural-protocols-for-extension-types.md) (structural protocols), [ADR-0015](adrs/0015-odm-layer-and-schema-migration.md) (ODM architecture), [ADR-0016](adrs/0016-lancedb-evaluation.md) (LanceDB evaluation).

### Delivered

- **SearchBackend protocol** — 13-method structural protocol in `pyrite/storage/backends/protocol.py`, 66 conformance tests
- **SQLiteBackend** — wraps existing PyriteDB + FTS5 + sqlite-vec (default, local/single-user)
- **PostgresBackend** — tsvector + pgvector, 66/66 conformance tests (~3x indexing, ~2x query overhead vs SQLite — acceptable for server deployments)
- **LanceDB evaluated and rejected** — 49-66x slower indexing, 60-280x slower queries, 25-54x larger disk. See ADR-0016.

---

## 0.11 — ODM Completion (done)

Schema versioning (`_schema_version` tracking, `since_version` field semantics, `MigrationRegistry`, `pyrite schema migrate`). DocumentManager for write-path coordination. Architecture hardening (DDL validation, MCP constants extraction). Test infrastructure (pytest-xdist, extension tests). Docs KB fixes. 1505 tests.

---

## 0.12 — Distribution (done)

PyPI publish, version bump, MANIFEST.in, publish workflow, CHANGELOG, README.

Remaining loose ends (no version bump needed):
- PyPI trusted publisher setup (XS, manual step)
- [[mcp-submission-update]] (#89, XS)

---

## 0.13 — Human & Agent UX Hardening (done)

Web UI hardening (14 items: logout, version history, type colors, page titles, dead code, loading states, accessibility, mobile responsive, collections save, first-run experience, starred entries, full accessibility audit, Playwright tests, review hardening). Agent DX (8 items: PosixPath fix, batch-read, list-entries, kb_recent, search fields, smart field routing, structured errors, file placement fix).

---

## 0.14 — Auth & Rate Limiting (done)

GitHub OAuth login, per-KB read/write/admin permissions, MCP rate limiting.

---

## 0.15 — Deployment & Demo (done)

Docker/Compose, deploy buttons (Railway/Render/Fly.io), pyrite.wiki website, demo site deployment, BYOK AI gap analysis, final UI review.

---

## 0.16 — Ecosystem & Onboarding (done)

Getting Started tutorial, plugin writing tutorial, awesome plugins page, `pyrite ci` command, personal-kb-repo-backing, one-click deploy configs, alpha banner, OpenAI/Gemini MCP integration docs.

---

## 0.17 — Cleanup & Hardening (done)

Bug fixes (entry ID collisions, priority type mismatch, date field reads, status field reads). Reliability (API singletons, plugin hook atomicity, plugin discovery strict mode). Developer experience (MCP body truncation docs, embedding prewarm, import cycle detection, KB compaction, schema validation CLI, plugin registry dedup, factory open/closed, component documentation gaps).

---

## 0.18 — Architecture & Ecosystem (done)

KBService decomposition (extracted GraphService, EphemeralKBService, QuotaService, ExportService). Schema module decomposition. SearchService/KBService overlap resolution. Dynamic subdirectory paths. Reserved field validation. Software-kb plugin. Journalism-investigation plugin. Edge entities (typed relationships as first-class entities). Entry lifecycle and search filtering. DB backup/restore. Kanban workflow for agent teams. Export system (NotebookLM + Quartz renderers).

---

## 0.20.0 — First Public Release

**Theme:** Release readiness. Version bump, CHANGELOG, documentation accuracy, lint cleanup. No new features — polish and ship.

---

## Future (1.0+)

### Ecosystem (open from 0.18)

| Item | Effort | Status |
|------|--------|--------|
| [[extension-registry]] | M | planned |
| [[extension-type-protocols]] Phase 1 | L | planned |
| [[obsidian-migration]] | M | planned |
| [[pkm-capture-plugin]] | L | planned |
| [[plugin-repo-extraction]] | M | deferred |

### Agent Swarm Infrastructure

### Agent Swarm Infrastructure

- **Coordination/Task Plugin Phases 3-4** — DAG queries, critical path analysis, QA integration
- **[[intent-layer]]** — Guidelines, goals, rubrics for entry quality
- **[[kb-orchestrator-skill]]** — Multi-KB agent coordination pattern
- **Agent provenance tracking** — Structured identity, capability recording, change attribution
- **Conflict resolution at content level** — Semantic merge for concurrent agent writes
- **Observable state for orchestrators** — Event stream (WebSocket) for KB modifications
- **Read-your-own-writes guarantees** — Synchronous indexing mode for dependent agent steps

### QA Agent Phases 3-5

- **Tier 2**: LLM consistency checks against type instructions and editorial guidelines
- **Tier 3**: Factual verification with web search and source chain checking
- **Phase 5**: Continuous QA pipeline with post-save hooks and scheduled sweeps

### Infrastructure

- **[[event-bus-webhooks]]** — Integration story, live graph updates
- **[[db-backup-restore]]** — Database backup and restore tooling
- **[[oauth-providers]] Phase 3** — Generic OIDC for corporate SSO (Keycloak, Auth0, Okta, Azure AD)
- **[[extension-type-protocols]] Phases 2-3** — Satisfaction checking, registry integration

### KB Quality at Scale

- **[[search-relevance-boost-by-entry-type]]** — Operator-controlled search ranking by type, intent layer integration

### Polish and Scale

- **Canvas/Whiteboard** — Freeform spatial canvas
- **Git Sync Conflict Resolution UI** — Visual merge conflict resolution
- **Engagement Federation** — Sync engagement data across instances
- **Offline Support** — IndexedDB cache, virtual scrolling for large KBs
- **AI writing assistant** — Select text → summarize/expand/rewrite/continue

---

## Versioning notes

Milestones are scope-driven, not time-driven. Each milestone ships when its definition of done is met. Bug fixes and small improvements may land between milestones without bumping the version.
