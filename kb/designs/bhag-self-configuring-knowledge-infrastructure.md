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
- **1086 tests** across the platform

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

## Inspiration

Anytype's insight that knowledge should be typed and relational, but reoriented for programmatic consumers. Anytype optimizes for a human dragging blocks on a canvas. Pyrite optimizes for an agent calling APIs. Anytype uses CRDTs for seamless convergence. Pyrite uses git for accountable change. In a world of agent swarms, accountable change wins.

## Go-to-Market: Four Waves

The BHAG is realized through progressive launch waves, each widening the audience and proving the platform with a domain-specific plugin:

1. **Platform Launch (0.8)** — Agent builders, MCP users. "Pyrite turns your AI into a domain expert."
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
