# Pyrite

**A second brain for you, your agents, and your teams.**

Knowledge-as-Code — structured knowledge in markdown files with YAML frontmatter, schema-validated, versioned in git, searchable by any AI through MCP.

Your AI agents have no memory. Your knowledge is trapped in platform silos. Every new chat starts from zero. Pyrite gives you structured, validated, git-versioned knowledge bases that any AI can read and write through a built-in MCP server. One brain, every AI, persistent memory that compounds over time.

**Why Pyrite instead of vectors-in-Postgres or Notion+AI?**

- **Typed entries with schema validation** — not flat vector blobs. Define `person`, `decision`, `event`, `component` types with validated fields. Query structurally, not just by vibes.
- **Git-native** — every change is a versioned commit, not a database mutation. Branch, diff, review, rollback. Your knowledge has a full audit trail.
- **MCP server with three-tier access control** — read/write/admin tiers. Give untrusted agents read-only access. Give your own agents write access. Keep admin for yourself.
- **Semantic + structured search** — find by meaning (vector embeddings) AND by type, tag, date range, or relationship. Both at once in hybrid mode.
- **Plugin system with 15 extension points** — custom entry types, MCP tools, CLI commands, validators, lifecycle hooks, relationship semantics, schema migrations.
- **Zero running cost locally** — markdown files + SQLite index on your disk. No cloud dependency, no subscription, no vendor lock-in. Your data is plain text files you can read in any editor.

## Quick Start

```bash
# Install
pip install pyrite

# Initialize a knowledge base
mkdir my-kb && cd my-kb
pyrite init --name my-brain

# Create some entries
pyrite create --type person --title "Sarah Chen" \
  --body "Engineering lead. Considering move to consulting." --tags "team,engineering"

pyrite create --type decision --title "Switch to async standups" \
  --body "Decided 2026-03-01. Reduces meeting load by 3hrs/week." --tags "process"

# Search (keyword, semantic, or hybrid)
pyrite search "career transition"
pyrite search "team decisions" --mode=semantic

# Connect to Claude Desktop / Claude Code
# Add to your MCP config:
```

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

Now any AI that speaks MCP can search, read, and write your knowledge base.

## How It Works

Markdown files with YAML frontmatter in git are the source of truth. Pyrite builds a SQLite FTS5 index (with optional vector embeddings) on top of the files for fast search. The MCP server, CLI, and REST API all read from and write to the same files. Rebuild the index from files at any time with `pyrite index build`.

You define domain-specific entry types and field schemas in a `kb.yaml` file. Pyrite validates entries on every write, indexes them, and exposes them through all interfaces. A plugin protocol lets you extend entry types, add MCP tools, define relationship semantics, and hook into lifecycle events.

```
Your files (git)  →  SQLite index (derived)  →  MCP server / CLI / REST API / Web UI
                                               ↑
                                          Any AI connects here
```

## MCP Server

Three permission tiers. Each tier includes the tools from lower tiers.

| Tier | Tools |
|------|-------|
| **read** (14) | `kb_list`, `kb_search`, `kb_get`, `kb_timeline`, `kb_tags`, `kb_backlinks`, `kb_stats`, `kb_schema`, `kb_orient`, `kb_batch_read`, `kb_list_entries`, `kb_recent`, `kb_qa_validate`, `kb_qa_status` |
| **write** (+6) | read + `kb_create`, `kb_bulk_create`, `kb_update`, `kb_delete`, `kb_link`, `kb_qa_assess` |
| **admin** (+4) | write + `kb_index_sync`, `kb_manage`, `kb_commit`, `kb_push` |

All paginated tools (`kb_search`, `kb_timeline`, `kb_backlinks`, `kb_tags`) support `limit`/`offset` params and return a `has_more` flag. `kb_bulk_create` handles up to 50 entries per call with best-effort per-entry semantics. `kb_orient` provides a one-shot KB summary for agent onboarding. `kb_batch_read` fetches multiple entries in one call. Search results return snippets by default (use `include_body` for full text, `fields` for projection).

Plugins add their own tools per tier (e.g., software-kb adds `sw_adrs`, `sw_backlog`, `sw_new_adr`).

Also exposes: 4 prompts (`research_topic`, `summarize_entry`, `find_connections`, `daily_briefing`), resources (`pyrite://kbs`, `pyrite://kbs/{name}/entries`, `pyrite://entries/{id}`).

Use `pyrite mcp --tier read` for a read-only server.

## CLI

```bash
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

All commands support `--format json` for agent consumption.

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

Ten built-in entry types: `note`, `person`, `organization`, `event`, `document`, `topic`, `relationship`, `timeline`, `collection`, `qa_assessment`. Entries support `aliases` for alternate names that resolve in wikilinks and autocomplete.

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

Six extensions ship:

| Extension | Purpose | Key Types |
|-----------|---------|-----------|
| **software-kb** | Software project management | ADRs, components, backlog items, standards, runbooks |
| **zettelkasten** | CEQRC maturity workflow | Notes with maturity progression |
| **encyclopedia** | Articles with review workflow | Articles, reviews, voting |
| **social** | Engagement tracking | Social interactions |
| **cascade** | Timeline research | Timeline events, actors, capture lanes |
| **task** | Work coordination | 7-state task workflow with atomic claim and decomposition |

## Web UI

Optional SvelteKit 2 + Svelte 5 frontend for browsing, visualization, and oversight:

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

extensions/          # Domain-specific plugins (software-kb, zettelkasten, encyclopedia, social, cascade, task)
web/                 # SvelteKit 2 + Svelte 5 frontend (TypeScript + Tailwind)
kb/                  # Pyrite's own KB (ADRs, backlog, components, standards)
```

**Storage model:** Markdown files in git are the source of truth. SQLite FTS5 is a derived index. Rebuild from files at any time with `pyrite index build`. Background embedding pipeline keeps vector index current.

**Content negotiation:** REST API responds in JSON, Markdown, CSV, or YAML via `Accept` header. CLI supports `--format`.

**Access control:** REST API supports role-based tier enforcement (read/write/admin) with hashed API keys.

## Deploy

### One-Click Deploy

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template/new?repo=markramm/pyrite&referralCode=pyrite)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/markramm/pyrite)

**Fly.io** — create a volume and deploy:

```bash
fly launch --copy-config --name my-pyrite
fly volumes create pyrite_data --size 1
fly deploy
```

All three platforms use the included Dockerfile, persist data at `/data`, and expose port 8088. Set `PYRITE_AUTH_ENABLED`, `PYRITE_OPENAI_API_KEY`, and other env vars in your platform's dashboard after deploy.

### Self-Hosted VPS

Run your own Pyrite instance on any VPS ($6/month, unlimited users, you own your data):

```bash
git clone https://github.com/markramm/pyrite.git && cd pyrite
bash deploy/selfhost/setup.sh kb.example.com
```

This installs Docker, starts Pyrite + Caddy (auto TLS), and seeds Pyrite's own KB so you have content to explore immediately. Then create your admin user:

```bash
docker compose -f deploy/selfhost/docker-compose.yml exec pyrite \
  python /app/deploy/selfhost/create-user.py admin yourpassword
```

Auth is required, registration is closed by default — add users manually with the same command.

### Local Docker

For local development without TLS, use the minimal compose:

```bash
docker compose up -d  # http://localhost:8088
```

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
pip install -e extensions/task
```

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
for ext in extensions/*/; do pip install -e "$ext"; done
pre-commit install

# Tests (1468 tests)
pytest tests/ -v

# Frontend
cd web && npm install && npm run dev

# Linting
ruff check pyrite/
```

Pyrite's own backlog and architecture docs live in `kb/`:

```bash
pyrite sw backlog        # Prioritized backlog
pyrite sw adrs           # Architecture Decision Records (16 ADRs)
pyrite sw components     # Module documentation
pyrite sw standards      # Coding conventions
```

## Background

Started as a fork of [joshylchen/zettelkasten](https://github.com/joshylchen/zettelkasten). Since substantially rewritten: multi-KB, plugin system, three-tier MCP, FTS5 + vector search, REST API with tier enforcement, SvelteKit frontend, service layer, schema-as-config, content negotiation, collections, block references, web clipper, AI integration. See [UPSTREAM_CHANGES.md](UPSTREAM_CHANGES.md) for divergence history.

## License

MIT — see [LICENSE](LICENSE).
