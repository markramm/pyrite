# Pyrite Architecture

## Overview

Pyrite is a local-first, multi-KB research infrastructure designed for citizen journalists and AI agents. It supports structured knowledge management with full-text search, relationship tracking, and multiple interfaces.

## Core Principles

1. **Local-first** - Everything runs on the researcher's machine
2. **Git-native** - Every KB is a git repo (version history, attribution, distribution)
3. **Markdown source of truth** - No lock-in, portable, human-readable
4. **Multi-KB** - Mount, search, and cross-reference multiple knowledge bases
5. **FtM-compatible semantics** - Exportable to FollowTheMoney for interop with Aleph/OpenAleph
6. **AI-native** - MCP integration, AI-assisted workflows, agent contributions

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Interfaces                                    │
├─────────────────┬─────────────────┬─────────────────┬───────────────────┤
│   CLI (typer)   │ Web UI (future) │  MCP Server     │  REST API         │
│   ✓ Implemented │   Streamlit     │  ✓ Implemented  │  FastAPI          │
└────────┬────────┴────────┬────────┴────────┬────────┴─────────┬─────────┘
         │                 │                 │                  │
         ▼                 ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Core Services                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  IndexManager  │  KBRepository  │  GitHub Auth   │  (future: AI svc)    │
└────────┬───────┴───────┬────────┴───────┬────────┴──────────────────────┘
         │               │                │
         ▼               ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Storage Layer                                    │
├─────────────────────────────────────────────────────────────────────────┤
│   CascadeDB (SQLite + FTS5)     │     File System (Markdown + YAML)     │
│   - Full-text search index       │     - Source of truth                 │
│   - Relationship graph           │     - Git-versioned                   │
│   - Tag index                    │     - Human-editable                  │
│   - Analytics queries            │     - Per-KB directories              │
└─────────────────────────────────────────────────────────────────────────┘
         │                                       │
         ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Configuration                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  ~/.pyrite/config.yaml    │    {kb}/kb.yaml                   │
│  - KB registry                       │    - KB-specific schema           │
│  - Repository definitions            │    - Validation rules             │
│  - GitHub OAuth credentials          │    - Entry type definitions       │
│  - Global settings                   │    - FtM mappings                 │
└─────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
~/.pyrite/              # Global config directory
├── config.yaml                   # Main configuration
├── github_auth.yaml              # OAuth credentials (secured)
├── index.db                      # SQLite FTS5 index
├── cache/                        # AI summaries, embeddings (future)
└── subscribed/                   # Cloned remote KBs

{knowledge-base}/                 # A Knowledge Base
├── kb.yaml                       # KB schema and policies
├── actors/                       # Research KB subdirectories
│   ├── miller-stephen.md
│   └── ...
├── organizations/
├── events/                       # Or root for Events KB
│   ├── 2025-01-20--event.md
│   └── ...
└── .cascade/                     # Per-KB cache (gitignored)
    └── index.db                  # Local index (optional)
```

## Data Flow

### Indexing

```
1. User runs: pyrite index build
2. IndexManager iterates over configured KBs
3. For each KB:
   a. KBRepository.list_entries() yields (Entry, Path)
   b. Entry converted to dict with all metadata
   c. CascadeDB.upsert_entry() stores in SQLite
   d. FTS5 triggers auto-update search index
4. KB stats updated (entry count, last indexed time)
```

### Search

```
1. User runs: pyrite search "query"
2. CascadeDB.search() executes FTS5 query
3. Optional filters applied (KB, type, tags, date range)
4. Results returned with snippets and BM25 ranking
5. Fallback to file-based search if index unavailable
```

### File Sync

```
1. User edits markdown file directly
2. User runs: pyrite index sync
3. IndexManager.sync_incremental() checks file mtimes
4. Only changed files re-indexed
5. Deleted files removed from index
```

## KB Types

### Events KB
- One event = one file
- Filename: `YYYY-MM-DD--slug.md`
- Canonical date field
- Single-paragraph body (typically)
- Importance score (1-10)
- Status: confirmed/disputed/alleged/rumored
- Actors list

### Research KB
- Rich narrative documents
- Subdirectories by type: actors/, organizations/, themes/
- Multiple sections and headers
- Research status: stub/partial/draft/complete/published
- Flexible frontmatter

## Database Schema (SQLite + FTS5)

```sql
-- KB registry
kb(name, kb_type, path, description, last_indexed, entry_count)

-- Main entries
entry(id, kb_name, entry_type, title, body, summary, file_path,
      date, importance, status, location,           -- events
      research_status, role, era,                   -- research
      created_at, updated_at, indexed_at)

-- Full-text search (FTS5)
entry_fts(id, kb_name, entry_type, title, body, summary, location)

-- Tags (many-to-many)
tag(id, name)
entry_tag(entry_id, kb_name, tag_id)

-- Actors mentioned in events
entry_actor(entry_id, kb_name, actor_name)

-- Relationships between entries
link(source_id, source_kb, target_id, target_kb, relation, inverse_relation, note)

-- Source citations
source(entry_id, kb_name, title, url, outlet, date, verified)
```

## Future Architecture Considerations

### Semantic Search / RAG

For future AI-powered search, we may add vector embeddings. Reference architecture from LobeHub:

- **LobeHub approach**: PGVector for semantic search with embeddings
- **Our approach options**:
  1. sqlite-vss (SQLite vector extension) - keeps local-first
  2. Separate embedding service with Anthropic/OpenAI APIs
  3. Local embeddings with sentence-transformers

See: https://github.com/lobehub/lobe-chat for RAG pipeline architecture:
- files → documents → chunks → embeddings
- PGlite WASM for local-first (interesting for future web UI)

### Agent-Optimized CLIs (Implemented)

Two CLIs provide permission-separated access for AI agents and human researchers:

#### `pyrite-read` — Read-only (safe for untrusted agents)

All commands output JSON: `{ok: bool, code: int, data/error: {...}}`

```bash
pyrite-read list                           # List all KBs
pyrite-read search "query"                 # Full-text search (FTS5)
pyrite-read get <entry-id>                 # Get entry by ID
pyrite-read timeline --from=2025-01-01     # Timeline events
pyrite-read tags                           # All tags with counts
pyrite-read actors                         # All actors with counts
pyrite-read backlinks <id> --kb=<name>     # Entries linking to this entry
pyrite-read stats                          # Index statistics
```

#### `pyrite` — Full access (read + write + admin)

```bash
# Read (same as pyrite-read)
pyrite search "immigration policy" --kb=timeline
pyrite get miller-stephen --with-links

# Write
pyrite create --kb=timeline --type=event --title="Title" --date=2025-01-20
pyrite update <id> --kb=timeline --body="Updated content"
pyrite delete <id> --kb=timeline

# Admin
pyrite index build                         # Rebuild search index
pyrite index sync                          # Incremental sync
pyrite index stats                         # Index statistics
pyrite index health                        # Check index health
```

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage error |
| 2 | Entry not found |
| 3 | KB not found |
| 4 | Permission denied |
| 5 | Validation error |
| 10 | Index error |
| 99 | Other error |

**Error Format:**
```json
{
  "ok": false,
  "code": 2,
  "error": {
    "code": "NOT_FOUND",
    "message": "Entry 'foo' not found",
    "hint": "pyrite-read search 'foo'",
    "docs": "https://github.com/markramm/pyrite/blob/main/docs/ARCHITECTURE.md"
  }
}
```

**Claude Skill:** See `.claude/skills/kb/skill.md` for integration with Claude Code.

### MCP Integration (Implemented)

The MCP (Model Context Protocol) server is implemented and ready for Claude Code integration.

**Setup:**
```bash
pyrite mcp-setup   # Configure Claude Code
pyrite mcp         # Run server manually (stdio)
```

**Available Tools:**
| Tool | Description |
|------|-------------|
| `kb_list` | List all mounted knowledge bases with types and entry counts |
| `kb_search` | Full-text search with FTS5 syntax, filters by KB/type/tags/dates |
| `kb_get` | Get entry by ID with full content, links, and backlinks |
| `kb_create` | Create new event or research entry |
| `kb_update` | Update existing entry fields |
| `kb_timeline` | Get timeline events by date range and importance |
| `kb_backlinks` | Find all entries linking to a given entry |
| `kb_tags` | Get all tags with usage counts |
| `kb_actors` | Get all actors mentioned in events |
| `kb_index_sync` | Sync search index with file changes |

**Protocol:** JSON-RPC 2.0 over stdio, compatible with Claude Code and MCP spec.

**Architecture notes from LobeHub:**
- 10,000+ tools via MCP marketplace
- Tool name format: `identifier::apiName::type`
- Supports stdio, SSE, WebSocket transports

**Future tools planned:**
- `kb_export_ftm` - Export as FollowTheMoney entities
- `kb_graph` - Get relationship graph for visualization
- `kb_ai_summarize` - Generate AI summaries of entries

### Authentication

LobeHub uses Better-Auth with:
- OAuth providers (Google, GitHub)
- Passkeys (WebAuthn)
- TOTP 2FA
- Magic links

We currently support:
- GitHub OAuth for private repo access
- SSH keys for git operations
- Personal access tokens

### Web UI

LobeHub architecture reference:
- Next.js + React frontend
- Zustand for state management
- tRPC for type-safe APIs

Our planned approach:
- Streamlit for rapid prototyping (simpler)
- FastAPI backend (already have foundation)
- Consider Electron for desktop (like LobeHub)

## References

- [LobeHub/lobe-chat](https://github.com/lobehub/lobe-chat) - Modern AI chat with RAG, MCP, multi-model support
- [FollowTheMoney](https://followthemoney.tech/) - Entity schema for investigative data
- [joshylchen/zettelkasten](https://github.com/joshylchen/zettelkasten) - Original inspiration for Pyrite
- [OpenAleph](https://openaleph.org/) - OCCRP investigative platform
