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

## 0.12 — Launch Prep

**Theme:** Everything needed for a stranger to find, install, try, and trust Pyrite. Distribution, auth, rate limiting, demo site.

| Item | Description | Effort |
|------|-------------|--------|
| [[pypi-publish]] | Publish `pyrite` and `pyrite-mcp` to PyPI | S |
| [[mcp-submission-update]] | Accurate tool count, test count, configuration examples | XS |
| [[web-ui-auth]] Phase 1 | Local auth + API key tiers | M |
| [[mcp-rate-limiting]] | Rate limiting for public-facing MCP server | S |
| [[demo-site-deployment]] | Live demo on Fly.io/Railway with PostgresBackend | M |
| [[byok-ai-gap-analysis]] | Audit AI features for bring-your-own-key completeness | M |
| [[pyrite-ci-command]] | `pyrite ci` for CI/CD schema + link validation | S |
| Getting Started tutorial | Zero to working MCP connection in 5 minutes | S |

### Definition of done

- `pip install pyrite && pyrite init --template software` works from a clean venv
- `pip install pyrite-mcp` works and connects to Claude Desktop
- Demo site live with auth + rate limiting
- An autonomous agent can: install Pyrite, create a KB, build an extension, test it, install it, and start populating — entirely via CLI
- BYOK audit complete — all AI features work with user-provided keys
- README, tutorial, and docs are accurate and newcomer-friendly

---

## 0.13 — Ecosystem

**Theme:** Prove Pyrite is general-purpose. Ship plugins for different audiences, let others build and share extensions.

| Item | Description | Effort |
|------|-------------|--------|
| [[software-project-plugin]] | Evolves from `extensions/software-kb/` (Wave 2) | L |
| [[investigative-journalism-plugin]] | Proves general-purpose with different audience (Wave 3) | XL |
| [[extension-registry]] | Public extension directory | M |
| [[extension-type-protocols]] Phase 1 | Protocol definitions for extension types (ADR-0014) | L |
| [[obsidian-migration]] | Import from Obsidian vaults | M |
| [[pkm-capture-plugin]] | Personal knowledge management capture (Wave 4) | L |

### Definition of done

- At least 2 domain-specific plugins shipped and installable via registry
- `pyrite extension install <name>` pulls from public registry
- Obsidian users can migrate with `pyrite import --from obsidian`
- Extension type protocols defined, at least one plugin implements them

---

## Future (1.0+)

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
- **[[web-ui-auth]] Phase 2** — OAuth/OIDC for hosted deployments
- **[[extension-type-protocols]] Phases 2-3** — Satisfaction checking, registry integration

### Polish and Scale

- **Canvas/Whiteboard** — Freeform spatial canvas
- **Git Sync Conflict Resolution UI** — Visual merge conflict resolution
- **Engagement Federation** — Sync engagement data across instances
- **Offline Support** — IndexedDB cache, virtual scrolling for large KBs
- **AI writing assistant** — Select text → summarize/expand/rewrite/continue

---

## Versioning notes

Milestones are scope-driven, not time-driven. Each milestone ships when its definition of done is met. Bug fixes and small improvements may land between milestones without bumping the version.
