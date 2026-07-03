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

## 0.21–0.24 — Shipped between milestones (reconciliation note, 2026-07-02)

Versions 0.21.0 through 0.24.0 were tagged without roadmap or CHANGELOG
entries (CHANGELOG stops at 0.20.0). Highlights recoverable from git:
Tier-A agent-CLI features (`pyrite rename` + wikilink rewrite, `qa
coverage` curation stats), the CLI error-shape consistency sweep (0
ad-hoc sites CLI-wide), `task reset` for stale claims, FTS5 term quoting
in links suggest/discover (fixed the `links orphans` crash), and the
`all_kbs()` enumeration fix for DB-registered KBs. Backfill CHANGELOG as
part of 0.25.

---

## 0.25 — Field Hardening & Shared-Instance Pilot (next)

**Theme:** Retire the derived-state bug class, then put a second human on
the instance. No speculative architecture, no new UI surface. Epic:
[[epic-shared-instance-readiness]].

The prioritization rule for this milestone: the tool's job for the next
quarter is to be *boring* for its operator and *trustworthy* for one or
two invited peers — every candidate item is tested against that and
nothing else.

### Workstream 1 — Derived-state reliability (prerequisite)

- [[ci-make-green-and-load-bearing]] (high, M) — CI red 100/100 runs
  for three months; pre-commit configured but never installed;
  postgres conformance never runs in CI. Highest leverage-to-cost in
  the 2026-07-03 audit; everything else on this list needs a working
  gate to stay fixed.
- [[verify-after-write-on-the-index-path]] (high, M) — read-back
  verification on every indexing write; hard errors, not warnings;
  hash-based staleness so same-second edits re-index. (Content-hash
  half landed: caa3902.)
- [[collapse-kb-registry-to-one-source-of-truth]] (medium, M) — finish
  the `all_kbs()` sweep, pick one registry owner, ADR the decision,
  make user-side config drift structurally impossible.
- [[fail-open-exception-sweep]] (high, S) — ~10 broad excepts convert
  failure to false success at trust boundaries (MCP registry merge,
  status-drift detector self-disable, mislabeled push failures);
  the incubator for the next field-bug class.
- [[task-claim-concurrency-test]] (high, S) — the fleet's one
  concurrency guard has never been executed concurrently; N-process
  race, exactly one winner.
- [[regression-test-links-fts-quoting]] (high, XS) — the missing
  40e7a39 regression lock (the one open Iron Law 1 violation).

### Workstream 2 — Shared-instance pilot (read-only)

- [[oauth-state-store-persistence]] (high, S) — login survives restarts.
- [[mcp-rest-tool-parity]] (medium, M) — the web UI peers see must match
  agent capability.
- [[search-query-syntax-error-contract]] (high, S) — fix the sanitizer
  bypass on operator/quoted queries (live crash, 40e7a39 class),
  return QUERY_SYNTAX instead of INTERNAL/retryable, and audit every
  MATCH/tsquery site that touches entry-derived terms.
- Hosting-security Phase 1 static audit from
  [[hosting-security-hardening]] run against the pilot deploy config —
  audit only; fixes triaged by tier.
- [[llm-usage-tracking-and-quotas]] (medium, M) — only if hosted AI is
  enabled for peers; otherwise slips to 0.26.
- Ship: 1–2 trusted peers (candidates: Drey Dossier, The Pugilist) with
  read access to cascade-research + cascade-timeline + actors, plus a
  written invite doc (what they see, what's logged, what's not).

### Workstream 3 — Documentation (from the 2026-07-02 docs audit)

Finding: docs are excellent wherever an agent loop exercises them
daily (CLAUDE.md, pyrite-dev skill, MCP truncation docs) and fictional
wherever never executed (`pip install pyrite` is DOA on PyPI,
`mcp --tier read` doesn't exist, getting-started's git-init claim is
false). A pilot peer's first hour is the onboarding funnel, so the
first two items are epic subtasks:

- [[docs-onboarding-fiction-sweep]] (high, S) — every documented
  onboarding command must work on the current build; settle the PyPI
  vs source-install story; implement or un-document `--tier`.
- [[docs-operational-contracts-travel-with-tool]] (high, M) — move the
  operational contracts out of tcp-skills/memory into
  `orient`/help/docs; JSON-contracts page; un-stale api-design.md;
  multi-session git discipline into CLAUDE.md; AGENTS.md.
- [[ci-run-getting-started-tutorial]] (medium, S) — docs-as-tests so
  the fiction class can't re-ship.
- [[qa-validate-enforce-type-rubrics]] (medium, M) — make kb.yaml
  rubrics enforced rather than decorative; reconcile the ADR rubric;
  fix kind-enum errors and broken ADR wikilinks.
- [[dirty-world-fixtures-and-adversarial-corpus]] (medium, M) — make
  the five escaped field-bug classes representable in tests: real
  config loading, out-of-band edits, adversarial strings by default.
- [[shared-frontmatter-split-utility]] (medium, S) — retire 8+
  hand-rolled frontmatter splitters; fix the divergent
  journalism-investigation copy (drops `_schema_version`).

### Workstream 4 — Bookkeeping

- Backfill CHANGELOG 0.21–0.24; keep it current through 0.25.
- [[links-asymmetric-intra-kb-mode]] (medium, S) — unblocks the
  intra-KB cross-linking-debt audit on cascade-research.
- KNOWN-ISSUES.md stays a thin pointer file; field bugs get backlog
  items same-day.

### Deliberately frozen for 0.25

[[backend-agnostic-query-dsl]] and
[[split-backend-protocol-entitystore-searchengine-embeddingstore]]
(re-prioritized to medium — no forcing function),
[[ji-ui-investigation-dashboard]] and [[ji-ui-timeline-visualization]]
(build after a second person actually uses the instance), write access
for peers (needs tool-enforced source-tier provenance +
[[per-user-fork-directories]]), [[plugin-type-resolution-scoping]]
(medium, L — real, but it's an extension-registry prerequisite, not a
pilot blocker; the pilot ships with first-party extensions only),
Canvas/extension-registry/ecosystem items.

### Definition of done

One peer, logged in, searching the corpus read-only for two weeks with
zero operator interventions caused by index/registry drift, and zero
known crash bugs reachable from the read surface.

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
