---
type: design_doc
title: "BHAG: Self-Configuring Knowledge Infrastructure for Agent Swarms"
status: active
author: markr
date: "2026-02-28"
tags: [vision, bhag, agents, architecture]
---

# BHAG: Self-Configuring Knowledge Infrastructure for Agent Swarms

## The Vision

An autonomous agent encounters a domain it needs to reason about persistently. It doesn't find existing infrastructure for that domain. So it uses Pyrite's extension builder to create typed entries, validators, and MCP tools for that domain. It tests what it built. It installs the extension, provisions a KB, and starts working. From that point forward, every agent that works in that domain — in that session or future sessions — gets structured, validated, queryable knowledge instead of stuffing things into flat files or losing context between runs.

**Pyrite is not a knowledge management tool. It is a knowledge compiler.** The agent defines a schema, the schema generates infrastructure (validation, search, API surface), and the infrastructure constrains future agents to produce quality output. The schema is the program. Pyrite is the runtime.

## Core Thesis

Knowledge management will be consumed by AI agents in more cases than humans in the future. This means better versioning, better change management, and better AI access to create, update, read, and use knowledge bases. We are designing for a world filled with agent swarms.

## The Agent-as-User Model

Traditional knowledge tools assume a human installs the software, configures schemas via UI, and connects agents as tools. Pyrite inverts this:

**The agent is the customer, not the tool.**

An autonomous agent runtime (OpenClaw, Claude Code, Codex, custom orchestrators) needs persistent, structured, queryable memory for a domain-specific workflow. The agent:

1. **Discovers** Pyrite via `pip install pyrite` or `pip install pyrite-mcp`
2. **Provisions** a KB with the right schema via `pyrite init --template <domain>` or programmatic API
3. **Extends** the type system by building a domain-specific extension (using the extension-builder skill as a guide)
4. **Tests** the extension using the pyrite-dev skill's TDD protocol
5. **Populates** the KB through CLI commands or MCP tools
6. **Queries** structured knowledge with full-text, semantic, and hybrid search
7. **Validates** its own output through schema validation and QA workflows

The human's role shifts from "user" to "operator" — deploying the agent, monitoring quality, setting trust tiers.

## Three Portals, One Knowledge Base

The knowledge an agent builds is accessible from everywhere:

**CLI** — the agent-native path. OpenClaw, Claude Code, Codex, shell scripts. Every command outputs structured JSON. Agents do the heavy lifting here: bulk creation, extension management, headless provisioning, JSON pipelines.

**MCP** — the conversational path. Claude Desktop, Cowork, any MCP-compatible client. Humans and agents talk to the knowledge base in natural language. Three permission tiers control access.

**Web UI** — the visual path. Knowledge graph exploration, rich entry editor, QA dashboard, BYOK AI integration. The operator interface — watch the graph grow as agents populate a KB, explore relationships, trigger workflows.

An agent builds the KB through CLI at 3am. You review what it produced in the web UI over coffee. You ask follow-up questions through Claude Desktop. All hitting the same typed, validated, versioned knowledge.

## Why This Is Credible (closer than you think)

This isn't aspirational — almost all the pieces already ship:

- **`pyrite extension init legal --types case,statute,ruling`** — agent scaffolds a full extension in one command
- **Extension builder skill** guides the agent through implementation, following the same TDD protocol used to build Pyrite itself
- **`pyrite extension install extensions/legal --verify`** — installs and optionally runs tests
- **`pyrite init --template <domain>`** — provisions a KB with zero interactive prompts
- **`--format json` on every CLI command** (11 commands and counting) — agents consume output programmatically
- **QA validation on every write** — agents validate their own output against the schema
- **Three-tier MCP server** with schema self-discovery (`kb_schema` tool)
- **Task/coordination plugin** with 7-state workflow, atomic operations, 4 MCP tools
- **Programmatic schema provisioning** — agents define types and fields via MCP/CLI without editing YAML
- **Plugin protocol** with 15 extension points covering every aspect an agent would need
- **Six shipped extensions** (zettelkasten, social, encyclopedia, software-kb, task, and Pyrite's own KB) proving the pattern produces working, tested code
- **1780+ tests** across the platform

The gap between "human defines schema" and "agent defines schema" is one skill file and a few CLI commands. The BHAG isn't a 2-year plan — it's a closing sprint.

## The Self-Improving Loop

Every agent-quality bug produces a schema or validation improvement. The gotchas.md file is maintained by the agents that encounter pitfalls. The knowledge infrastructure improves itself through use:

1. Agent builds extension, encounters non-obvious behavior
2. Pyrite-dev skill's pre-commit checklist prompts: "Did I encounter any non-obvious behavior?"
3. Agent appends to gotchas.md
4. Future agents read gotchas.md before building extensions
5. Failure rate decreases over time

## What Differentiates This From Everything Else

Every other knowledge tool assumes a human defines the schema and agents fill it in. Pyrite is building toward agents defining the schema too.

| Approach | Who Defines Schema | Who Populates | Who Validates |
|----------|-------------------|---------------|---------------|
| Obsidian/Notion | Human | Human | Human |
| Vector stores | Nobody (unstructured) | Agent | Nobody |
| RAG pipelines | Human (retrieval config) | Agent | Human (spot-checks) |
| **Pyrite (current)** | **Human** | **Human + Agent** | **Schema + Agent** |
| **Pyrite (BHAG)** | **Agent** | **Agent** | **Schema + QA Agent** |

## Truth-Functionality: The Foundational Commitment

Pyrite is named after fool's gold. The aspiration is to build something that isn't.

In a world where AI generates plausible-sounding knowledge at scale, most of it is pyrite — it looks like knowledge but has no epistemic backing. The foundational commitment of Pyrite-the-platform is **truth-functionality**: every KB inherits a posture of validation, provenance tracking, and structured accountability from the system itself. This isn't a feature you enable — it's the default.

**What truth-functionality means in practice:**

- **Schema validation on every write** — the operator defines what "well-formed" means for their domain, and the system enforces it. An entry that doesn't conform to the schema is rejected or flagged, not silently accepted.
- **QA as immune system** — structural validation, consistency checks, and factual verification run continuously. The knowledge base actively resists degradation.
- **Source chains** — claims link to evidence. Entries link to sources. The graph structure *is* the evidence structure. An isolated claim with no links, no sources, and no QA assessment is epistemically weaker than one embedded in a web of corroborating entries.
- **Cross-linking as epistemic infrastructure** — truth in a knowledge base isn't a property of individual entries, it's a property of the graph. The more connected and mutually consistent a cluster of entries is, the stronger the epistemic foundation.
- **Lifecycle and freshness** — knowledge ages. Component docs go stale. The system tracks currency and warns when entries may no longer reflect reality. See [[entry-lifecycle-field-and-search-filtering]] and [[kb-compaction-command-and-freshness-qa-rules]].

This commitment is domain-agnostic. A legal KB defines truth through citation chains and jurisdictional validity. A journalism KB defines truth through source verification and evidence standards. A software KB defines truth through test results and architecture consistency. Pyrite provides the infrastructure; the schema encodes what "true" means for each domain.

**The [[intent-layer-guidelines-and-goals|intent layer]] is the mechanism** through which truth-functionality becomes operational. Every KB inherits system-level truth-functional defaults — source chain expectations, cross-linking norms, QA baselines — before the operator adds any domain-specific configuration. The operator extends the baseline; the baseline is inherited from the platform.

Anyone can fork. But merges require validation. Truth is enforced at the repo boundary.

**This is already operational**, not aspirational. Two KBs in daily use demonstrate truth-functionality across different domains:

- **Investigative journalism** (4800+ entries) — timeline events with capture lanes, source citations, importance scores, cross-linked entities and organizations. When an agent or human queries "what happened with voter purges in Georgia," the answer comes from validated, sourced, linked entries — not hallucinated context. Schema enforces sourcing standards; QA catches broken links and missing citations.
- **Software development** (200+ entries) — ADRs recording decisions with rationale, component docs describing current architecture, backlog items tracking work with dependencies. Schema enforces per-type fields; QA catches staleness. The project's own KB runs on the tool it builds.

Both run today as MCP servers over git repos. No demo site needed, no OAuth, no Docker. The truth-functional infrastructure is the daily workflow, not a launch feature.

## Trust as a Measurable Property

Trust in Pyrite isn't binary — it's accumulated over time and measured at the credential level.

**Signed commits as provenance chain:** When all commits to a KB are signed, every entry has verifiable provenance — who created it, which credential, when. The credential might be a human, an agent, or a swarm sharing a key. The system doesn't need to distinguish — it measures output quality.

**Trust-over-time:** A credential that consistently produces entries that pass QA, get linked by other entries, survive freshness checks, and don't get contradicted earns implicit trust. One that produces entries that get flagged, archived, or contradicted doesn't. This creates a trust score derived from the KB's own assessment history — not from external identity verification.

**Trust tiers compose with git:**

| Layer | Mechanism | What It Controls |
|-------|-----------|-----------------|
| Git | Signed commits, branch protection, CODEOWNERS | Who can write to the repo |
| QA | Schema validation, assessment entries, `pyrite ci` | What quality bar must be met |
| Trust | Credential history, QA pass rates, link density | How much scrutiny a contribution gets |

A new contributor's PR gets full QA scrutiny and manual review. A credential with a long history of high-quality contributions might get lighter review. The trust signal comes from the KB's own data, not from an external reputation system.

**For agent swarms**, this is essential. An orchestrator deploying 10 agents against a KB needs to know which agents are producing reliable output and which need tighter supervision. Signed commits + QA history per credential provides that signal without requiring the orchestrator to inspect every entry.

## Inspiration

Anytype's insight that knowledge should be typed and relational, but reoriented for programmatic consumers. Anytype optimizes for a human dragging blocks on a canvas. Pyrite optimizes for an agent calling APIs. Anytype uses CRDTs for seamless convergence. Pyrite uses git for accountable change. In a world of agent swarms, accountable change wins.

## Go-to-Market: Four Waves

The BHAG is realized through progressive launch waves, each widening the audience and proving the platform with a domain-specific plugin:

1. **Platform Launch (0.16)** — Agent builders, MCP users. "Pyrite turns your AI into a domain expert."
2. **Software Project Plugin** — Dev teams. Agents collaborate on your project natively.
3. **Investigative Journalism Plugin** — Researchers, OSINT. Follow the money. Different domain, same platform.
4. **PKM Capture Plugin** — Everyone. Frictionless capture → auto-classification → structured knowledge.

Each wave is a proof point. By wave 4, three shipping plugins demonstrate that Pyrite is genuinely general-purpose knowledge infrastructure. See [[launch-plan]] for the full content matrix and messaging.

## Related

- [[launch-plan]] — Content matrix, messaging foundation, four-wave launch strategy
- [[permissions-model]] — Three-layer permissions design sketch
- [[coordination-task-plugin]] — Agent task coordination within the knowledge graph
- [[pkm-capture-plugin]] — Frictionless knowledge ingestion for PKM users
- [[qa-agent-workflows]] — Automated quality assurance for agent-authored content
- [[roadmap]] — Release milestones toward the BHAG
- [[kb/positioning/software-teams]] — Initial go-to-market positioning
