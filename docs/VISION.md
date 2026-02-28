# Pyrite: Product Vision

## What is Pyrite?

A **Knowledge-as-Code** platform. Knowledge bases are structured, version-controlled repositories — like code repos, but for any domain requiring persistent, queryable, validated knowledge. Designed for a world where AI agents are the primary producers and consumers of structured knowledge.

## BHAG: Self-Configuring Knowledge Infrastructure for Agent Swarms

An autonomous agent encounters a domain it needs to reason about persistently. It doesn't find existing infrastructure for that domain. So it builds a Pyrite extension — typed entries, validators, MCP tools — tests it, installs it, provisions a KB, and starts working. Every future agent that works in that domain gets structured, validated, queryable knowledge instead of flat files or lost context.

**The schema is the program. Pyrite is the runtime.**

See `kb/designs/bhag-self-configuring-knowledge-infrastructure.md` for the full design document.

## Core Thesis

Knowledge management will be consumed by AI agents in more cases than humans in the future. This means better versioning, better change management, and better AI access to create, update, read, and use knowledge bases. We are designing for a world filled with agent swarms.

## Core Idea: Knowledge as Code

Just as modern software development treats infrastructure, configuration, and documentation as code — versioned, reviewed, tested, and collaboratively maintained — Pyrite applies the same principles to knowledge:

| Code Repository | Knowledge Repository |
|---|---|
| Source files | Markdown entries with YAML frontmatter |
| `pyproject.toml` | `kb.yaml` — schema, editorial policies, entity types |
| Linting rules | Validation rules (required fields, controlled vocabulary, source requirements) |
| CI checks | QA agent — structural validation, consistency checks, factual verification |
| Git history | Full attribution — who (human or agent) created, modified, reviewed each entry |
| Fork + PR workflow | Same — fork a KB, contribute improvements, submit PR |
| pip install | `pyrite extension install` — domain-specific types, tools, validators |
| Test suite | Extension tests — 8-section structure, TDD protocol |

### What a KB Repository Contains

```
research-kb/
├── kb.yaml                  # Schema, editorial policies, entity types, validation rules
├── actors/
│   ├── miller-stephen.md    # Structured entries with YAML frontmatter
│   └── ...
├── organizations/
├── events/
├── themes/
├── documents/
└── .pyrite/                 # Local index cache (gitignored)
```

## Who Is It For?

### Agents (primary consumers)

- **Autonomous agent runtimes** (OpenClaw, Claude Code, Codex) — need persistent structured memory for domain-specific workflows
- **Agent orchestrators** — need task coordination, evidence tracking, and provenance across swarms
- **Research agents** — need typed entries, relationship graphs, and temporal queries
- **QA agents** — need validation rules, assessment tracking, and coverage metrics

### Humans (operators and collaborators)

- **Agent operators** — deploy agents, set trust tiers, monitor quality via web UI
- **Research teams** — investigative journalists, policy researchers, academic groups
- **Software teams** — architecture docs, ADRs, component catalogs (the "CLAUDE.md but structured" use case)
- **Domain experts** — define schemas, editorial guidelines, and validation rules that constrain agent output

## How Agents Use Pyrite

### Via CLI (primary path for agent runtimes)

Autonomous agents like OpenClaw execute shell commands. The CLI is the simplest, most universal integration:

```bash
# Install
pip install pyrite

# Provision a KB
pyrite init --template software --path ./project-kb

# Build a domain extension
pyrite extension init legal --types case,statute,ruling
# (agent fills in the scaffold using extension-builder skill)
pyrite extension install extensions/legal --verify

# Work
pyrite create --kb legal --type case --title "Smith v. Jones" \
  --field jurisdiction=federal --field status=active --format json
pyrite search "immigration policy" --kb research --format json
```

### Via MCP (primary path for Claude Desktop, custom integrations)

Three permission tiers. Each tier includes the tools from lower tiers.

| Tier | Access | Use Case |
|------|--------|----------|
| **read** | Search, browse, retrieve, schema discovery | Untrusted agents, research assistants |
| **write** | Create, update, delete, link entries | Trusted research workflows |
| **admin** | Index management, KB provisioning, git operations | Human-supervised, orchestrators |

### Via REST API and Web UI (monitoring and operator interface)

The web UI serves the human operator — the person deploying and monitoring agents. SvelteKit 5 frontend with entry editor, knowledge graph, collections, QA dashboard, and task monitoring.

## The Self-Configuration Loop

The BHAG realized as a concrete workflow:

1. **Agent discovers domain need** — needs to track legal cases, scientific papers, threat intelligence, etc.
2. **Agent scaffolds an extension** — `pyrite extension init legal --types case,statute` creates the structure
3. **Agent implements the extension** — guided by extension-builder skill, follows pyrite-dev TDD protocol
4. **Agent tests the extension** — 8-section test structure, verification before completion
5. **Agent installs and provisions** — `pyrite extension install` + `pyrite init --template legal`
6. **Agent populates the KB** — creates typed, validated entries via CLI or MCP
7. **QA agent validates output** — structural validation on every write, LLM consistency checks on schedule
8. **Future agents benefit** — the extension and KB are reusable infrastructure

### AI Agent Roles

Agents get different permission levels depending on trust:

| Role | Permissions | Interface | Use Case |
|------|------------|-----------|----------|
| **Reader** | Search, browse, retrieve entries | `pyrite-read` / MCP read tools | Research assistant — find relevant entries, summarize |
| **Contributor** | Read + write entries directly | `pyrite` / MCP write tools | Trusted agent that creates/edits entries subject to KB policies |
| **Orchestrator** | Full access + task coordination | `pyrite` / MCP admin tools | Decomposes work, dispatches to agents, aggregates results |

All agent contributions are attributed — the git commit records who (or what) made each change.

## Collaboration Model

### Git-Native

- Every KB is a **git repository** (or directory within one)
- **Markdown files are the source of truth** — human-readable, diffable, portable
- The database is a **fast query index**, not the canonical store
- Version history, attribution, branching, and merging are handled by git

### GitHub as the Trust Boundary

- **Public KBs** can be subscribed to (shallow clone) or forked
- **Private KBs** use GitHub's access control
- **Contributing to upstream** = fork + PR (standard GitHub workflow)
- The PR process is how trust is established for contributions from other users or AI agents

### Workspace Model

Each user (or agent runtime) has a **workspace** — a local collection of KB repos:

```
~/.pyrite/
├── config.yaml              # Global settings
├── repos/                   # Workspace: cloned KB repos
│   ├── my-org/
│   │   └── my-research/     # Owned repo
│   ├── other-team/
│   │   └── their-kb/        # Subscribed (shallow clone, read-only)
│   └── my-fork-of/
│       └── their-kb/        # Forked (full clone, can contribute)
└── index.db                 # Unified search index across all KBs
```

## Design Principles

1. **Agent-first** — Programmatic interfaces are primary. CLI output is machine-parseable. MCP tools are self-documenting.
2. **Local-first** — Everything runs on the user's machine. No mandatory cloud service.
3. **Git-native** — Git is the version control, collaboration, and distribution layer. Accountable change over seamless convergence.
4. **Markdown source of truth** — No lock-in. Portable. Human-readable. AI-readable.
5. **Schema-as-config** — Types and validation defined in YAML, not code. Agents can provision schemas programmatically.
6. **Plugin protocol** — 15 extension points. Agents can extend every aspect: types, tools, validators, hooks, workflows.
7. **Progressive enforcement** — Validation starts advisory, grows toward automated enforcement (like adding a linter to a codebase).
8. **Attribution everywhere** — Every change tracked to a user or agent via git history.
9. **Quality as infrastructure** — QA is not a human review step; it's an automated system that makes quality queryable and trackable.

## Inspiration

Anytype's insight that knowledge should be typed and relational, but reoriented for programmatic consumers. Anytype optimizes for a human dragging blocks on a canvas. Pyrite optimizes for an agent calling APIs. Anytype uses CRDTs for seamless convergence. Pyrite uses git for accountable change. In a world of agent swarms, accountable change wins.

## Roadmap Alignment

| Milestone | Theme | Status |
|-----------|-------|--------|
| 0.1–0.3 | Core infrastructure, CLI, MCP, REST API, Web UI, plugins | Done |
| 0.4 | MCP server hardening for agent workflows | Done |
| **0.5** | **Announceable alpha: agent infrastructure, QA Phase 1, web UI polish** | **Next** |
| 0.6 | Agent coordination: task plugin, programmatic schema provisioning | Planned |
| 0.7+ | Agent swarm infrastructure: provenance, conflict resolution, orchestrator events | Future |

See `kb/roadmap.md` for detailed milestone definitions.
