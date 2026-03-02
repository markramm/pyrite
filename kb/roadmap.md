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

## 0.13 — Human & Agent UX Hardening

**Theme:** Fix every bug and gap in both the web UI and the agent-facing surfaces (CLI, MCP, REST). Both humans and agents must have a solid experience before the platform goes public.

**Web UI:**

| Item | Effort |
|------|--------|
| [[web-ui-logout-button]] | XS |
| [[web-ui-version-history-fix]] | XS |
| [[web-ui-type-colors-consolidation]] | XS |
| [[web-ui-page-titles]] | XS |
| [[web-ui-dead-code-cleanup]] | XS |
| [[web-ui-loading-states]] | S |
| [[web-ui-accessibility-fixes]] | S |
| [[web-ui-mobile-responsive]] | S |
| [[web-ui-collections-save]] | S |
| [[web-ui-first-run-experience]] | S |
| [[web-ui-starred-entries]] | S |
| [[ux-accessibility-fixes]] | M |
| [[playwright-integration-tests]] | M |

**Agent DX (CLI + MCP + REST):** Done — PosixPath fix, batch-read, list-entries, kb_recent, search fields, smart field routing, structured errors, file placement fix.

### Definition of done

All Playwright tests pass. No runtime errors on any route. Every page has a loading, empty, and error state. MCP `kb_update` works without serialization errors. `kb_batch_read`, `kb_list_entries`, `kb_recent` tools functional. Search `fields` parameter works across CLI, MCP, and REST. Agent errors return structured JSON with `suggestion` field.

---

## 0.14 — Auth & Rate Limiting

**Theme:** Multi-user access control for public-facing deployments.

| Item | Effort |
|------|--------|
| [[mcp-rate-limiting]] | S |
| [[oauth-providers]] Phase 1 (GitHub) | L |
| [[per-kb-permissions]] | L |

### Definition of done

GitHub OAuth login works. Per-KB read/write/admin tiers enforced. Rate limiting active on all public endpoints.

---

## 0.15 — Deployment & Demo

**Theme:** Docker, website, live demo site.

| Item | Effort |
|------|--------|
| [[container-deployment]] Phase 1 (Dockerfile + compose) | M |
| [[container-deployment]] Phase 2 (deploy buttons) | S |
| [[pyrite-website]] (pyrite.dev) | M |
| [[demo-site-deployment]] | M |
| [[byok-ai-gap-analysis]] | M |
| [[web-ui-review-hardening]] (final gate) | S |

### Definition of done

`docker compose up` works. Demo site live at demo.pyrite.dev. Website live at pyrite.dev. Final UI review passed.

---

## 0.16 — Ecosystem & Onboarding

**Theme:** Plugin extraction, tutorials, community readiness. This is the launch release.

| Item | Effort |
|------|--------|
| [[plugin-repo-extraction]] | M |
| [[personal-kb-repo-backing]] | M |
| Getting Started tutorial | S |
| [[plugin-writing-tutorial]] | S |
| [[awesome-plugins-page]] | XS |
| [[pyrite-ci-command]] | S |

### Definition of done

All 5 plugins on PyPI. Tutorials published. Awesome page live. `pyrite ci` works in CI pipelines.

### Launch Day (after 0.16.0 ships)

Wave 1 content push: HN Show HN, Reddit, blog post. Everything is live, tested, documented.

---

## 0.17 — Ecosystem

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

## Post-launch — KB Quality & Lifecycle

**Theme:** As KBs grow, search noise increases. Entry lifecycle management and type-aware freshness keep the active search surface clean without losing history.

| Item | Effort |
|------|--------|
| [[entry-lifecycle-field-and-search-filtering]] | S |
| [[kb-compaction-command-and-freshness-qa-rules]] | S |

### Definition of done

`lifecycle` field filters archived entries from default search. `pyrite kb compact --dry-run` identifies reasonable archival candidates. Type-aware freshness rules warn on stale component docs but not on ADRs.

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
