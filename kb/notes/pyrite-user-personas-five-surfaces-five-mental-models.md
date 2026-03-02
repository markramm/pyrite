---
id: pyrite-user-personas-five-surfaces-five-mental-models
title: 'Pyrite User Personas: Five Surfaces, Five Mental Models'
type: note
tags:
- architecture
- dx
- agents
- ux
- design
metadata:
  importance: 8
---

## The Five Personas

Pyrite has five distinct user personas, each with different interface preferences, mental models, and quality-of-life needs. Feature design should consider all five.

### 1. AI via CLI (token-optimized agents)

**Who:** Claude Code, Gemini CLI, Codex, Antigravity, VS Code Claude Code integration, and similar CLI+AI tools.

**Interface:** `pyrite` CLI with `--format json`. The agent invokes shell commands and parses structured output.

**Mental model:** The CLI is the most token-efficient pattern. Every flag, every output line costs tokens. These agents want: minimal output by default, structured JSON for parsing, batch operations to reduce round-trips, and predictable exit codes.

**What matters:** Token economy, parse-ability, batch operations, `--fields` and `--body-limit` style truncation. The CLI is their MCP server — they don't need a separate protocol layer.

### 2. AI via MCP (tool-calling agents)

**Who:** Claude Desktop, n8n, other MCP clients, agent-to-agent integrations, workflow automation platforms.

**Interface:** MCP tools (`kb_search`, `kb_create`, etc.) over stdio or HTTP transport.

**Mental model:** Tools are black boxes with typed inputs and outputs. The agent reads tool descriptions, calls tools, processes results. It never sees a command line. Schema discovery (`kb_schema`) is critical because the tool descriptions are the only documentation the agent gets.

**What matters:** Self-describing tools with good descriptions, schema discoverability, three-tier access control, rate limiting for public-facing use. Tool parameter design must be intuitive enough that an agent encountering Pyrite for the first time can create valid entries without prior examples.

### 3. Expert Users / Extenders

**Who:** Developers building extensions, defining schemas, writing kb.yaml files, creating custom entry types and validators. People who understand the domain model deeply.

**Interface:** All of them — CLI for daily work, REST API for integrations, direct file editing for schema work, Python API for extensions.

**Mental model:** Knowledge-as-Code. They think in types, schemas, relationships, and validation rules. They want the domain model to be expressive, the extension points to be well-documented, and the plugin protocol to be stable.

**What matters:** Extension scaffolding, schema expressiveness, plugin protocol stability, ADR documentation, test infrastructure. These users read the source code. They need it to be consistent and well-structured.

### 4. End Users (fluid KB interaction)

**Who:** People who just want to work with a knowledge base — add entries, search, browse, organize. They don't care about schemas or types; they want it to feel natural.

**Interface:** Web UI primarily, possibly CLI for power users.

**Mental model:** "I have information, I want to put it somewhere I can find it later." They think in terms of notes, tags, and search — not entry types, frontmatter, or validation rules. The system should guide them without requiring them to understand the domain model.

**What matters:** Web UI polish, search that works without knowing query syntax, entry creation that infers types, tag suggestions, good defaults. The schema should be invisible — it helps them without them knowing it's there.

### 5. (Implicit) KnowledgeClaw-style autonomous agents

**Who:** Long-running autonomous agents that use Pyrite as persistent memory. They combine personas 1 or 2 with self-directed workflows — they decide when to search, what to create, when to validate.

**Interface:** CLI or MCP, driven by their own CLAUDE.md mission brief rather than human commands.

**Mental model:** The KB is my memory. I search before I act. I create entries to remember. I run QA to maintain quality. I commit to make my work durable.

**What matters:** Everything from personas 1-2, plus: `kb_recent` for re-orientation after downtime, self-KB patterns, QA automation, cost tracking per operation. These agents need to be good citizens of a KB without human oversight.

## Design Implications

When designing a new feature, ask: how does each persona encounter this?

- **Search fields/truncation**: Persona 1 and 2 need it for token economy. Persona 4 doesn't care (web UI handles display). Persona 3 might use it for scripting.
- **list-entries**: Persona 1 and 2 need it for orientation. Persona 4 gets this from the web UI sidebar. Persona 3 already knows the KB structure.
- **batch-read**: Persona 1, 2, and 5 need it for research workflows. Persona 4 clicks through entries one at a time.
- **kb_recent**: Persona 5 needs it most urgently. Persona 1 and 2 benefit. Persona 4 sees "recently modified" in the web UI.
- **Smart field routing**: Persona 2 needs it most (can't read source code to figure out the metadata dict pattern). Persona 1 benefits. Persona 3 already knows.

The general principle: **personas 1 and 2 are the most demanding because every interaction costs tokens or round-trips.** Persona 4 is the most forgiving because the web UI can paper over rough edges. Persona 3 will work around anything. Persona 5 inherits from 1 or 2 but adds autonomy concerns.

## Unifying Design Goal: Fluidity as Minimized Thinking Cost

"Fluid" is the same goal across all five personas — minimize the cost of thinking. The difference is that for agents, thinking cost is measurable in tokens; for humans, it's felt as friction.

Agent token costs split three ways, each with distinct optimization strategies:

- **Input tokens (context cost):** The price of reading — search results, schema descriptions, entry bodies, error messages. Pyrite controls this directly through response verbosity. Optimized by: `--fields`, `--body-limit`, lightweight index queries, terse structured errors.
- **Thinking tokens (deliberation cost):** The price of ambiguity — reasoning about where a field goes, what an error means, whether to retry. Pyrite controls this indirectly through interface clarity. Optimized by: self-describing schemas, smart field routing, prescriptive error suggestions, unambiguous tool descriptions.
- **Output tokens (action cost):** The price of acting — formulating tool calls, retries, workarounds. Pyrite controls this through interface predictability. Optimized by: consistent parameter names across surfaces, batch operations, idempotent writes.

For human end users, the equivalent costs are: scanning time (input), confusion (thinking), and clicks/keystrokes (output). The design work often converges — smart field routing reduces both agent thinking tokens and human confusion. Prescriptive error messages help both the CLI user and the MCP agent.

Where they diverge is in the direction of disclosure:

- **Human-fluid:** Progressive disclosure — hide complexity until needed. Start with the simple view, drill down on demand.
- **Agent-fluid:** Progressive precision — give the minimum information needed, let the agent request more. Start with a lightweight query, expand selectively.

Same principle, inverted direction. Both minimize thinking cost; they just optimize for different cognitive architectures.
