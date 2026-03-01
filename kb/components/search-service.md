---
type: component
title: "Search Service"
kind: service
path: "pyrite/services/search_service.py"
owner: "markr"
dependencies: ["pyrite.storage", "pyrite.services.embedding_service"]
tags: [core, search, fts5, semantic]
---

# Search Service

Unified search interface supporting keyword (FTS5), semantic (vector), and hybrid modes across all knowledge bases.

## API

```python
class SearchService:
    def __init__(self, db: PyriteDB, settings: Any | None = None)

    def search(
        self, query: str,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sanitize: bool = True,
        mode: str = "keyword",
        expand: bool = False,
    ) -> list[dict]
```

## Search Modes

| Mode | How it works | Performance | Quality |
|------|-------------|-------------|---------|
| `keyword` | SQLite FTS5 full-text search | Fast | Good for exact matches |
| `semantic` | Sentence-transformer embeddings + cosine similarity | Slower (first query loads model) | Good for conceptual queries |
| `hybrid` | Combines keyword + semantic, re-ranks by combined score | Slowest | Best overall |

## Components

- **FTS5 index**: Built by `IndexManager.sync_incremental()`, stored in SQLite
- **EmbeddingService**: Local sentence-transformers (`all-MiniLM-L6-v2`), 384-dimension vectors
- **QueryExpansionService**: Optional AI-powered query term expansion via LLMService (`expand=True`)

## REST API

`GET /api/search?q=...&mode=keyword&kb=...&type=...&tags=...&limit=20&expand=false`

Parameters:
- `q` (required): Search query
- `mode`: `keyword` (default), `semantic`, `hybrid`
- `kb`: Limit to specific knowledge base
- `type`: Filter by entry type
- `tags`: Comma-separated tag filter
- `expand`: Use AI query expansion (requires configured LLM)

## Used By

- **Search endpoint** (`search.py`): Direct user search
- **AI chat** (`ai_ep.py`): RAG context retrieval — searches KB for relevant entries to include as LLM context
- **AI suggest-links** (`ai_ep.py`): Finds related entries for link suggestions
- **MCP tools**: `search_kb` tool uses SearchService
- **CLI**: `pyrite search` command

## Related

- [[storage-layer]] — PyriteDB with FTS5 tables, SearchBackend protocol
- [[embedding-service]] — Provides vector embeddings for semantic/hybrid search
- [[background-embedding-worker]] — Async embedding queue
- [LLM Service](llm-service.md) — Powers query expansion and AI-driven search features
- [REST API Server](rest-api.md) — Hosts the search endpoint
