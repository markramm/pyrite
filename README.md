# Pyrite

Pyrite is a multi-KB knowledge base system. Data is markdown files with YAML frontmatter, stored in git. Search is SQLite FTS5 with optional vector embeddings (semantic and hybrid modes). AI agents access it through a three-tier MCP server (read/write/admin). Humans use a CLI, REST API, or SvelteKit web UI.

You define domain-specific entry types and field schemas in YAML. Pyrite validates entries, indexes them, and exposes them through all interfaces. A plugin protocol lets you extend entry types, add MCP tools, define relationship semantics, and hook into lifecycle events.

## Install

```bash
pip install pyrite             # Core
pip install "pyrite[all]"      # Core + AI + semantic search + dev tools
pip install "pyrite[ai]"       # OpenAI + Anthropic SDKs
pip install "pyrite[semantic]" # sentence-transformers + sqlite-vec
```

For development (editable install from source):

```bash
git clone https://github.com/markramm/pyrite.git && cd pyrite
pip install -e ".[all]"
```

Extensions are installed separately:

```bash
pip install -e extensions/software-kb
pip install -e extensions/zettelkasten
pip install -e extensions/encyclopedia
pip install -e extensions/social
pip install -e extensions/cascade
```

## Usage

```bash
# Build the search index (required before first search)
pyrite index build

# Search (keyword, semantic, or hybrid)
pyrite search "immigration policy"
pyrite search "immigration" --kb=timeline --type=event --mode=hybrid

# Read
pyrite get stephen-miller
pyrite backlinks stephen-miller --kb=research
pyrite timeline --from=2025-01-01 --to=2025-06-30
pyrite collections list --kb=research

# Write
pyrite create --kb=research --type=person --title="Jane Doe" \
  --body="Senior policy advisor." --tags="policy,doj"

# Admin
pyrite index sync          # Incremental re-index after file edits
pyrite index health        # Check for stale/missing entries
pyrite kb discover         # Auto-find KBs by kb.yaml presence

# Schema versioning
pyrite schema diff --kb=research      # Show type versions and field annotations
pyrite schema migrate --kb=research   # Migrate entries to current schema version
```

## MCP Server

Three permission tiers. Each tier includes the tools from lower tiers.

| Tier | Tools |
|------|-------|
| **read** (10) | `kb_list`, `kb_search`, `kb_get`, `kb_timeline`, `kb_tags`, `kb_backlinks`, `kb_stats`, `kb_schema`, `kb_qa_validate`, `kb_qa_status` |
| **write** (+6) | read + `kb_create`, `kb_bulk_create`, `kb_update`, `kb_delete`, `kb_link`, `kb_qa_assess` |
| **admin** (+4) | write + `kb_index_sync`, `kb_manage`, `kb_commit`, `kb_push` |

All paginated tools (`kb_search`, `kb_timeline`, `kb_backlinks`, `kb_tags`) support `limit`/`offset` params and return a `has_more` flag. `kb_bulk_create` handles up to 50 entries per call with best-effort per-entry semantics.

Plugins add their own tools per tier (e.g., software-kb adds `sw_adrs`, `sw_backlog`, `sw_new_adr`).

Also exposes: 4 prompts (`research_topic`, `summarize_entry`, `find_connections`, `daily_briefing`), resources (`pyrite://kbs`, `pyrite://kbs/{name}/entries`, `pyrite://entries/{id}`).

### Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "pyrite": {
      "command": "pyrite",
      "args": ["mcp"]
    }
  }
}
```

Use `pyrite-admin mcp --tier read` for a read-only server.

## Web UI

SvelteKit 2 with Svelte 5 frontend:

- WYSIWYG + markdown editor (Tiptap + CodeMirror dual mode)
- `[[wikilinks]]` with autocomplete, alias resolution, and pill decorations
- `![[transclusion]]` embedded content cards
- Block references: `[[entry#heading]]` and `[[entry^block-id]]`
- Backlinks panel, outline/TOC, split panes
- Interactive knowledge graph (Cytoscape.js)
- Collections with list, table, kanban, and gallery views
- Virtual collections via query DSL
- AI chat sidebar (RAG), summarize, auto-tag, suggest links
- Quick switcher (Cmd+O), command palette (Cmd+K)
- Daily notes with calendar
- Timeline visualization
- Version history with diff viewer
- Web clipper for URL content capture
- WebSocket multi-tab sync
- Slash commands in editor

## Custom Types

Define types in `kb.yaml`:

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

Types support versioning for safe schema evolution:

```yaml
types:
  case:
    version: 2
    fields:
      methodology:
        type: text
        required: true
        since_version: 2  # required for new entries, warning-only for legacy
```

Entries track their schema version in `_schema_version` frontmatter. `pyrite schema migrate` applies registered migrations and produces a reviewable git diff.

Field types: `text`, `number`, `date`, `datetime`, `checkbox`, `select`, `multi-select`, `object-ref`, `list`, `tags`.

Eight built-in entry types: `note`, `person`, `organization`, `event`, `document`, `topic`, `relationship`, `timeline`. Entries support `aliases` for alternate names that resolve in wikilinks and autocomplete.

## Plugin Protocol

Extensions implement a Python protocol class with up to 16 methods:

- `get_entry_classes()` — custom entry types with serialization
- `get_type_metadata()` — field definitions, AI instructions, presets
- `get_collection_types()` — custom collection types
- `get_mcp_tools(tier)` — per-tier MCP tools
- `get_cli_app()` — Typer sub-commands
- `get_validators()` — entry validation rules
- `get_migrations()` — schema migration functions for entry type upgrades
- `get_relationship_types()` — semantic relationship definitions
- Lifecycle hooks: `before_save`, `after_save`, `before_delete`, `after_delete`

Five extensions ship: `software-kb` (ADRs, components, backlog), `zettelkasten` (CEQRC maturity workflow), `encyclopedia` (articles, reviews, voting), `social` (engagement tracking), `cascade` (timeline events and migration).

## Architecture

```
pyrite/
├── models/          # Entry types (base, core_types, factory, generic, collection)
├── schema.py        # YAML-driven type definitions, field validation
├── migrations.py    # Schema migration registry (on-load entry transforms)
├── config.py        # Multi-KB and repo configuration
├── server/
│   ├── api.py       # FastAPI REST API factory (role-based tier enforcement)
│   ├── mcp_server.py # MCP server (mcp SDK, 3-tier, paginated)
│   ├── websocket.py # WebSocket multi-tab sync
│   └── endpoints/   # Per-feature REST routes (entries, search, kbs, collections, graph, daily, clipper, ...)
├── storage/
│   ├── database.py  # SQLite + FTS5 + sqlite-vec (SQLAlchemy ORM + raw SQL)
│   ├── index.py     # Incremental indexing with wikilink/transclusion extraction
│   └── repository.py # Markdown file I/O
├── services/        # Business logic (kb, search, embedding, llm, git, collection_query, clipper, user)
├── plugins/         # Plugin discovery and protocol
└── formats/         # Content negotiation (JSON, Markdown, CSV, YAML)

extensions/          # Domain-specific plugins (software-kb, zettelkasten, encyclopedia, social, cascade)
web/                 # SvelteKit 2 + Svelte 5 frontend (TypeScript + Tailwind)
kb/                  # Pyrite's own KB (ADRs, backlog, components, standards)
```

**Storage model:** Markdown files in git are the source of truth. SQLite FTS5 is a derived index. Rebuild from files at any time with `pyrite index build`. Background embedding pipeline keeps vector index current.

**Content negotiation:** REST API responds in JSON, Markdown, CSV, or YAML via `Accept` header. CLI supports `--format`.

**Access control:** REST API supports role-based tier enforcement (read/write/admin) with hashed API keys.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
for ext in extensions/*/; do pip install -e "$ext"; done
pre-commit install

# Tests (1505 tests)
pytest tests/ -v

# Frontend
cd web && npm install && npm run dev

# Linting
ruff check pyrite/
```

Pyrite's own backlog and architecture docs live in `kb/`:

```bash
pyrite sw backlog        # Prioritized backlog
pyrite sw adrs           # Architecture Decision Records (15 ADRs)
pyrite sw components     # Module documentation
pyrite sw standards      # Coding conventions
```

## Background

Started as a fork of [joshylchen/zettelkasten](https://github.com/joshylchen/zettelkasten). Since substantially rewritten: multi-KB, plugin system, three-tier MCP, FTS5 + vector search, REST API with tier enforcement, SvelteKit frontend, service layer, schema-as-config, content negotiation, collections, block references, web clipper, AI integration. See [UPSTREAM_CHANGES.md](UPSTREAM_CHANGES.md) for divergence history.

## License

MIT — see [LICENSE](LICENSE).
