# Pyrite

**Knowledge-as-Code for you and your agents.**

Pyrite is a knowledge infrastructure platform. You define your domain's types in YAML, your data lives in git as markdown, and everything is searchable by both humans and AI agents through a permissioned MCP server.

## What It Does

- **Typed knowledge entries** — People, organizations, events, documents, topics, and custom types with field-level validation
- **Multi-KB architecture** — Mount multiple knowledge bases (a timeline, a research KB, a project wiki) and query across all of them with cross-KB links
- **Three-tier MCP server** — AI agents get read, write, or admin access depending on trust level. The only knowledge system with permissioned agent access.
- **Git-native storage** — Markdown files with YAML frontmatter. Version history on every entry. No vendor lock-in.
- **Full-text + semantic search** — SQLite FTS5 with BM25 ranking, optional vector embeddings, and hybrid mode
- **Plugin protocol** — Define custom entry types, field schemas, relationship semantics, workflows, and MCP tools without modifying core

## Quick Start

```bash
# Install
pip install pyrite

# Or from source
git clone https://github.com/markramm/pyrite
cd pyrite
pip install -e ".[all]"

# Initialize a knowledge base
pyrite kb init my-research --type generic
pyrite kb mount my-research /path/to/my-research

# Create entries
pyrite entry create "Machine Learning Fundamentals" -k my-research -t note --tags ai,ml

# Search
pyrite search "machine learning" -k my-research

# Start the web UI
pyrite-server --dev
# Open http://localhost:8088
```

## Interfaces

| Interface | Command | Purpose |
|-----------|---------|---------|
| CLI (full access) | `pyrite` | Researchers and power users |
| CLI (read-only) | `pyrite-read` | Safe for untrusted AI agents |
| REST API | `pyrite-server` | Web and programmatic access |
| MCP Server | Configure in Claude/Cursor | AI agent integration |
| Web UI | `pyrite-server --dev` | Browser-based search, editing, graph |

## MCP Server

Pyrite's MCP server exposes your knowledge base to AI assistants with three permission tiers:

| Tier | Tools | Use Case |
|------|-------|----------|
| **Read** | `kb_search`, `kb_get`, `kb_timeline`, `kb_tags`, `kb_backlinks`, `kb_schema` | Public assistants, research queries |
| **Write** | Read + `kb_create`, `kb_update`, `kb_delete`, `kb_create_link` | Trusted research agents |
| **Admin** | Write + `kb_init`, `kb_remove`, `index_sync`, `repo_sync` | Human-supervised operations |

Pre-built MCP prompts (`research_topic`, `summarize_entry`, `find_connections`, `daily_briefing`) and browsable `pyrite://` resources are included.

### Claude Desktop / Claude Code Configuration

```json
{
  "mcpServers": {
    "pyrite": {
      "command": "pyrite-server",
      "args": ["--mcp", "--tier", "write"]
    }
  }
}
```

## Define Your Domain

Custom types in `kb.yaml` — no code required:

```yaml
name: legal-research
kb_type: generic
types:
  case:
    description: "Legal case or proceeding"
    fields:
      jurisdiction:
        type: select
        options: [federal, state, international]
      status:
        type: select
        options: [active, decided, appealed, settled]
      filing_date:
        type: date
      parties:
        type: list
        items:
          type: text
```

Field types: `text`, `number`, `date`, `datetime`, `checkbox`, `select`, `multi-select`, `object-ref`, `list`, `tags`. All auto-validated.

For deeper customization, the [plugin protocol](kb/designs/plugin-protocol.md) provides 12 extension points: custom entry types, MCP tools, relationship semantics, lifecycle hooks, workflows, database tables, and more. Four extensions ship today: zettelkasten, encyclopedia, social, and software-kb.

## Architecture

```
pyrite/
├── models/          # Entry types (base, core_types, factory, generic)
├── schema.py        # Type definitions, field schemas, relationship types
├── config.py        # Multi-KB + repo configuration
├── server/
│   ├── api.py       # FastAPI REST API
│   ├── mcp_server.py # Three-tier MCP server
│   └── endpoints/   # Per-feature REST routes
├── storage/
│   ├── models.py    # SQLAlchemy ORM
│   ├── crud.py      # CRUD operations
│   ├── queries.py   # Complex queries (backlinks, timeline, graph)
│   └── index.py     # FTS5 indexing
├── services/        # Business logic (kb, search, repo, llm, embedding, git, user)
├── plugins/         # Plugin discovery and protocol
├── formats/         # Content negotiation (JSON, Markdown, CSV, YAML)
└── ui/              # Streamlit web interface

extensions/          # Domain-specific plugins
├── zettelkasten/    # ZettelEntry, CEQRC workflow, maturity tracking
├── encyclopedia/    # ArticleEntry, review workflows, voting
├── social/          # SocialPostEntry, engagement tracking
└── software-kb/     # ComponentEntry, ADRs, backlog items

web/                 # SvelteKit 5 frontend (TypeScript + Tailwind)
```

### Storage Model

- **Source of truth**: Markdown files in git repos
- **Index**: SQLite with FTS5 for fast search
- **Two-tier durability**: Git for persistence, SQLite for queries. Rebuild the index from markdown at any time.

### Data Model

Eight core entry types: `note`, `person`, `organization`, `event`, `document`, `topic`, `relationship`, `timeline`. Each carries typed fields, source provenance with confidence scores, and relationship links with semantic inverses.

Content negotiation: API responses in JSON, Markdown, CSV, or YAML via `Accept` header. CLI supports `--format`.

## Who It's For

Pyrite is a horizontal platform. Current and intended use cases:

- **AI agent shared memory** — Persistent, typed, permissioned knowledge that agents can read and write through MCP
- **Software teams** — Architecture decision records, component docs, system knowledge that AI coding assistants can query
- **Domain-specific knowledge bases** — Legal research, policy analysis, medical studies — define your types in YAML
- **Investigative journalism** — Battle-tested on a 4,240-event timeline and 323-article research knowledge base
- **Enterprise knowledge management** — Multi-KB for organizational structure with plugin-based customization

See [kb/positioning/](kb/positioning/) for detailed market analysis.

## Development

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
pre-commit install

# Tests (583 tests)
pytest tests/ -v

# Frontend
cd web && npm install && npm run dev

# Linting
ruff check pyrite/
```

Pyrite manages its own backlog and architecture docs in its own KB:

```bash
pyrite sw backlog        # Prioritized feature list
pyrite sw adrs           # Architecture Decision Records
pyrite sw components     # Core module documentation
pyrite sw standards      # Coding conventions
```

## Background

Pyrite began as a fork of [joshylchen/zettelkasten](https://github.com/joshylchen/zettelkasten), a single-KB note-taking tool with OpenAI integration. It has since been substantially rewritten: multi-KB architecture, plugin system, three-tier MCP server, SQLite FTS5, REST API, SvelteKit frontend, service layer, schema-as-config, content negotiation, and collaboration support. See [UPSTREAM_CHANGES.md](UPSTREAM_CHANGES.md) for the full divergence history and [CHANGELOG.md](CHANGELOG.md) for release notes.

## License

MIT License — see [LICENSE](LICENSE).
