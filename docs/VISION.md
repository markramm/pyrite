# Pyrite: Product Vision

## What is Pyrite?

A **Knowledge-as-Code** platform for research teams. Knowledge bases are structured, version-controlled repositories — like code repos, but for investigative research, policy analysis, intelligence work, and any domain requiring collaborative structured knowledge.

## Core Idea: Knowledge as Code

Just as modern software development treats infrastructure, configuration, and documentation as code — versioned, reviewed, tested, and collaboratively maintained — Pyrite applies the same principles to knowledge:

| Code Repository | Knowledge Repository |
|---|---|
| Source files | Markdown entries (events, actors, documents, themes) |
| `package.json` / `pyproject.toml` | `kb.yaml` — schema, editorial policies, entity types |
| Linting rules | Validation rules for entries (required fields, allowed types, source requirements) |
| CI checks | Policy enforcement on ingest (start advisory, grow toward enforcement) |
| Git history | Full attribution — who created, modified, reviewed each entry |
| Fork + PR workflow | Same — fork a KB, contribute improvements, submit PR |
| README | KB description, editorial guidelines, contribution standards |
| npm / PyPI | Public KB registry — subscribe to research from other teams |

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
└── .cascade/                # Local index cache (gitignored)
```

`kb.yaml` defines the rules:
```yaml
name: research-kb
kb_type: research
description: "Investigative research on [topic]"

# Entity schemas — what fields each entry type requires
schema:
  actor:
    required: [title, role, tags]
    optional: [era, sources, links]
  event:
    required: [title, date, importance, status]
    optional: [location, actors, sources]

# Editorial policies — advisory now, enforceable later
policies:
  minimum_sources: 1           # Every entry needs at least one source
  require_verification: false   # Sources don't need to be verified yet
  allowed_statuses: [confirmed, disputed, alleged, rumored]
  review_required: false        # No mandatory peer review (yet)

# Entity type definitions for this KB
types:
  actor: "Person or organization involved in events"
  theme: "Recurring pattern or policy area"
  mechanism: "How something works or is implemented"
```

## Who Is It For?

Research teams doing structured knowledge work:

- **Investigative journalists** — OSINT, source tracking, timeline reconstruction
- **Policy researchers** — tracking legislation, actors, organizations across issues
- **Academic research groups** — collaborative literature and evidence bases
- **Corporate intelligence** — competitive analysis, due diligence research
- **Any team** that needs to collaboratively build, maintain, and query structured knowledge

## How Users and Agents Interact

Pyrite is designed for **humans and AI agents working together** on the same knowledge bases, through multiple interfaces:

```
┌─────────────────────────────────────────────────────────────┐
│                     Interfaces                               │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ CLI          │  │ MCP Server   │  │ Web UI            │  │
│  │ pyrite-read  │  │              │  │ (Streamlit/future)│  │
│  │ pyrite       │  │              │  │                   │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────────┘  │
│         │                 │                   │              │
│  Used by:          Used by:            Used by:              │
│  • Humans          • Claude Desktop    • Humans              │
│  • Claude Code     • n8n workflows     • Dashboards          │
│  • Gemini CLI      • Custom agents     • Editors             │
│  • Codex           • Any MCP client    • Reviewers           │
│  • Any terminal    │                   │                     │
│         │                 │                   │              │
│         └─────────────────┴───────────────────┘              │
│                           │                                  │
│                  ┌────────┴────────┐                         │
│                  │ Services Layer   │                         │
│                  │ (same for all)   │                         │
│                  └────────┬────────┘                         │
│                           │                                  │
│              ┌────────────┴────────────┐                     │
│              │                         │                     │
│        ┌─────┴─────┐          ┌───────┴──────┐              │
│        │ SQLite/PG  │          │ Git Repos    │              │
│        │ (index)    │          │ (source of   │              │
│        │            │          │  truth)      │              │
│        └────────────┘          └──────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

### AI Agent Roles

Agents get different permission levels depending on trust:

| Role | Permissions | Interface | Use Case |
|------|------------|-----------|----------|
| **Reader** | Search, browse, retrieve entries | `pyrite-read` / MCP read tools | Research assistant — find relevant entries, summarize |
| **Drafter** | Read + propose new entries (saved as drafts or PRs) | `pyrite` with draft flag / MCP | Agent researches a topic, drafts entries for human review |
| **Contributor** | Read + write entries directly (with attribution) | `pyrite` / MCP write tools | Trusted agent that creates/edits entries subject to KB policies |

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
- **Review workflow** = GitHub PR review (we don't reinvent this)
- The PR process is how trust is established for contributions from other users or AI agents

### Workspace Model

Each user has a **workspace** — a local collection of KB repos:

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

- **Own repos**: full read/write, push directly
- **Subscribed repos**: read-only shallow clone, pull updates
- **Forked repos**: full clone, push to fork, PR to upstream

## Design Principles

1. **Local-first** — Everything runs on the researcher's machine. No mandatory cloud service.
2. **Git-native** — Git is the version control, collaboration, and distribution layer.
3. **Markdown source of truth** — No lock-in. Portable. Human-readable. AI-readable.
4. **Multi-interface** — Same backend for CLI, MCP, web. Humans and agents use the same tools.
5. **Policy-governed** — KBs define their own schemas and editorial standards via `kb.yaml`.
6. **Progressive enforcement** — Policies start advisory, grow toward automated enforcement (like adding a linter to a codebase).
7. **Attribution everywhere** — Every change tracked to a user or agent via git history.
8. **FtM-compatible** — Entries map to FollowTheMoney schemas for interop with Aleph/OCCRP tools.

## Roadmap Alignment

| Phase | Focus | Status |
|-------|-------|--------|
| 1-4 | Core infrastructure, CLI, MCP, REST API | Done |
| 5 | Web UI (Streamlit) | Done |
| 6 | Semantic search (embeddings, hybrid search) | Done |
| **7** | **Collaboration: git-native repos, user identity, attribution, workspace model** | **Next** |
| 8 | FollowTheMoney export (Aleph/OpenAleph interop) | Planned |
| 9 | Policy enforcement (validation on ingest, schema checking) | Planned |
| 10 | Public KB registry / discovery | Future |
