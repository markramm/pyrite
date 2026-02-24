# Pyrite

Pyrite is a multi-KB knowledge base system. Data is markdown files with YAML frontmatter, stored in git. Search is SQLite FTS5 with optional vector embeddings. AI agents access it through a three-tier MCP server (read/write/admin). Humans use a CLI, REST API, or SvelteKit web UI.

You define domain-specific entry types and field schemas in YAML. Pyrite validates entries, indexes them, and exposes them through all interfaces. A plugin protocol lets you extend entry types, add MCP tools, define relationship semantics, and hook into lifecycle events.

## Install

```bash
pip install -e "."            # Core
pip install -e ".[all]"       # Core + AI + semantic search + dev tools
pip install -e ".[ai]"        # OpenAI + Anthropic SDKs
pip install -e ".[semantic]"  # sentence-transformers + sqlite-vec
```

Extensions are installed separately:

```bash
pip install -e extensions/software-kb
pip install -e extensions/zettelkasten
pip install -e extensions/encyclopedia
pip install -e extensions/social
```

## Usage

```bash
# Build the search index (required before first search)
pyrite index build

# Search
pyrite search "immigration policy"
pyrite search "immigration" --kb=timeline --type=event --mode=hybrid

# Read
pyrite get stephen-miller
pyrite backlinks stephen-miller --kb=research
pyrite timeline --from=2025-01-01 --to=2025-06-30

# Write
pyrite create --kb=research --type=person --title="Jane Doe" \
  --body="Senior policy advisor." --tags="policy,doj"

# Admin
pyrite index sync          # Incremental re-index after file edits
pyrite index health        # Check for stale/missing entries
pyrite kb discover         # Auto-find KBs by kb.yaml presence
```

## MCP Server

Three permission tiers. Each tier is a separate server instance.

| Tier | Tools |
|------|-------|
| **read** | `kb_list`, `kb_search`, `kb_get`, `kb_timeline`, `kb_tags`, `kb_backlinks`, `kb_stats`, `kb_schema` |
| **write** | read + `kb_create`, `kb_update`, `kb_delete` |
| **admin** | write + `kb_index_sync`, `kb_manage` |

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

Field types: `text`, `number`, `date`, `datetime`, `checkbox`, `select`, `multi-select`, `object-ref`, `list`, `tags`.

Eight built-in entry types: `note`, `person`, `organization`, `event`, `document`, `topic`, `relationship`, `timeline`.

## Plugin Protocol

Extensions implement a Python protocol class with up to 12 methods:

- `get_entry_classes()` — custom entry types with serialization
- `get_type_metadata()` — field definitions, AI instructions, presets
- `get_mcp_tools(tier)` — per-tier MCP tools
- `get_cli_app()` — Typer sub-commands
- `get_validators()` — entry validation rules
- `get_relationship_types()` — semantic relationship definitions
- Lifecycle hooks: `before_save`, `after_save`, `before_delete`, `after_delete`

Four extensions ship: `software-kb` (ADRs, components, backlog), `zettelkasten` (CEQRC maturity workflow), `encyclopedia` (articles, reviews, voting), `social` (engagement tracking).

## Architecture

```
pyrite/
├── models/          # Entry types (base, core_types, factory, generic)
├── schema.py        # YAML-driven type definitions, field validation
├── config.py        # Multi-KB and repo configuration
├── server/
│   ├── api.py       # FastAPI REST API factory
│   ├── mcp_server.py # MCP server (mcp SDK, 3-tier)
│   └── endpoints/   # Per-feature REST routes
├── storage/
│   ├── database.py  # SQLite + FTS5 (SQLAlchemy + raw)
│   ├── index.py     # Incremental indexing
│   └── repository.py # Markdown file I/O
├── services/        # Business logic (kb, search, repo, llm, embedding, git, user)
├── plugins/         # Plugin discovery and protocol
└── formats/         # Content negotiation (JSON, Markdown, CSV, YAML)

extensions/          # Domain-specific plugins
web/                 # SvelteKit 5 frontend (TypeScript + Tailwind)
kb/                  # Pyrite's own KB (ADRs, backlog, components, standards)
```

**Storage model:** Markdown files in git are the source of truth. SQLite FTS5 is a derived index. Rebuild from files at any time with `pyrite index build`.

**Content negotiation:** REST API responds in JSON, Markdown, CSV, or YAML via `Accept` header. CLI supports `--format`.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
for ext in extensions/*/; do pip install -e "$ext"; done
pre-commit install

# Tests (583 tests)
pytest tests/ -v

# Frontend
cd web && npm install && npm run dev

# Linting
ruff check pyrite/
```

Pyrite's own backlog and architecture docs live in `kb/`:

```bash
pyrite sw backlog        # Prioritized backlog
pyrite sw adrs           # Architecture Decision Records
pyrite sw components     # Module documentation
pyrite sw standards      # Coding conventions
```

## Background

Started as a fork of [joshylchen/zettelkasten](https://github.com/joshylchen/zettelkasten). Since substantially rewritten: multi-KB, plugin system, three-tier MCP, FTS5, REST API, SvelteKit frontend, service layer, schema-as-config, content negotiation. See [UPSTREAM_CHANGES.md](UPSTREAM_CHANGES.md) for divergence history.

## License

MIT — see [LICENSE](LICENSE).
