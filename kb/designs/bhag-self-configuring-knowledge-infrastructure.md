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

## Why This Is Credible

Almost all the pieces already exist:

- **Plugin protocol** with 15 extension points covering every aspect an agent would need
- **Extension builder skill** with scaffolding recipes, entry type contracts, and test templates
- **Pyrite-dev skill** with TDD protocol, debugging methodology, and verification requirements
- **Five shipped extensions** proving the pattern produces working, tested code
- **CLI that works headlessly** — `--format json` on every command, no interactive prompts required
- **Three-tier MCP server** with schema self-discovery (`kb_schema` tool)
- **Ephemeral KBs** with TTL and garbage collection for session-scoped memory
- **Capture lane validation** enforcing controlled vocabulary on agent writes

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

## Related

- [[coordination-task-plugin]] — Agent task coordination within the knowledge graph
- [[qa-agent-workflows]] — Automated quality assurance for agent-authored content
- [[roadmap]] — Release milestones toward the BHAG
- [[kb/positioning/software-teams]] — Initial go-to-market positioning
