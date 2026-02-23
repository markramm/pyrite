---
type: adr
title: "Content Negotiation and Multi-Format Support"
adr_number: 10
status: accepted
deciders: ["markr"]
date: "2026-02-23"
tags: [architecture, api, formats, mcp, ai-agents]
---

# ADR-0010: Content Negotiation and Multi-Format Support

## Context

Pyrite entries have a single canonical format: YAML frontmatter + Markdown body, stored as `.md` files in git. All API endpoints return JSON via Pydantic serialization. The MCP server wraps everything in JSON text content blocks. There is no content negotiation — clients cannot request data in alternative formats.

This creates several friction points:

### 1. AI agents pay a token tax

When an LLM agent retrieves entries via MCP or API, it receives JSON. JSON is verbose — quotes around every key, braces, commas, brackets. For structured data like entry listings, search results, and tabular queries, this verbosity costs real tokens. Formats like [TOON](https://github.com/toon-format/toon) (`text/toon`) are purpose-built for LLM consumption: ~40% fewer tokens than JSON on tabular data with equal or better LLM parse accuracy.

### 2. Human consumers want human formats

A CLI user piping search results to another tool may want CSV or TSV. A researcher exporting findings may want Markdown. A dashboard may want a summary, not a full entry. Currently there is no way to request these.

### 3. The canonical format is already multi-format

A Pyrite entry is simultaneously:
- **Markdown** (the body)
- **YAML** (the frontmatter)
- **JSON** (the API representation)
- **SQL rows** (the indexed representation)

The conversion infrastructure partially exists — `to_markdown()`, `to_frontmatter()`, `to_db_dict()` — but it's not exposed through content negotiation and there's no unified conversion layer.

### 4. Import is the flip side of export

Users need to bring data into Pyrite from other systems (CSV contact lists, JSON API dumps, Obsidian vaults, Notion exports). This requires the same format awareness, run in reverse.

## Decision

### 1. Accept Header Content Negotiation on API

API endpoints honor the `Accept` header to select response format. The default remains `application/json`.

```
GET /api/entries/meeting-2024-03-15
Accept: application/json          → JSON (current behavior, default)
Accept: text/markdown              → Full markdown with frontmatter
Accept: text/toon                  → TOON encoding of the entry data
Accept: text/csv                   → CSV (for list/search endpoints only)
Accept: application/yaml           → YAML frontmatter only (no body)
```

**Implementation:** A response format layer sits between the endpoint logic and the HTTP response. Endpoints return structured data (Pydantic models or dicts). The format layer serializes based on `Accept` header, falling back to JSON for unsupported types.

```python
# Conceptual — actual implementation may vary
from pyrite.formats import negotiate_response

@router.get("/api/entries/{entry_id}")
def get_entry(entry_id: str, request: Request):
    data = service.get_entry(entry_id)
    return negotiate_response(request, data)
```

### 2. Format Registry

A pluggable format registry maps MIME types to serializer/deserializer pairs:

| MIME Type | Ext | Serialize | Deserialize | Best for |
|-----------|-----|-----------|-------------|----------|
| `application/json` | `.json` | Built-in (Pydantic) | Built-in | API default, web UI |
| `text/markdown` | `.md` | `Entry.to_markdown()` | `Entry.from_markdown()` | Human reading, git storage |
| `text/toon` | `.toon` | toon-python `encode()` | toon-python `decode()` | LLM agents (token-efficient) |
| `text/csv` | `.csv` | stdlib csv | stdlib csv | Tabular export, spreadsheets |
| `application/yaml` | `.yaml` | ruamel.yaml `dump()` | ruamel.yaml `load()` | Frontmatter-only, config tools |
| `text/plain` | `.txt` | Body text only | — | Grep, simple tools |

New formats can be added by registering a serializer. Plugins could contribute formats via a future `get_formats()` protocol method, but this is not required for the initial implementation.

### 3. TOON for LLM-Optimized Responses

[TOON](https://github.com/toon-format/toon) (Token-Oriented Object Notation) is a format designed for LLM input. It uses indentation-based nesting (like YAML) with CSV-style tabular arrays, achieving ~40% fewer tokens than JSON on structured data while maintaining lossless round-trip fidelity.

**Where TOON excels in Pyrite:**
- Search results (uniform arrays of entries with consistent fields)
- Entry listings and tag/stats aggregations
- Bulk entry retrieval for AI processing
- MCP tool responses (where every token has a cost)

**Where TOON doesn't help:**
- Single entry with a large markdown body (the body dominates token count)
- Deeply nested or non-uniform structures
- Browser consumption (JSON is native)

**Integration:**
- Add `toon-python` as an optional dependency in the `[ai]` extra
- MCP server can default to TOON for list/search responses when the client signals support
- API supports TOON via `Accept: text/toon`
- Graceful fallback: if `toon-python` is not installed, return JSON with a warning header

### 4. Automatic Conversion Where It Makes Sense

Some conversions are lossless and automatic; others are lossy and require explicit opt-in:

| From → To | Lossless? | Automatic? | Notes |
|-----------|-----------|------------|-------|
| Markdown → JSON | Yes | Yes | Full entry with all fields |
| JSON → Markdown | Yes | Yes | Reconstruct frontmatter + body |
| JSON → TOON | Yes | Yes | Structural encoding, round-trips |
| TOON → JSON | Yes | Yes | Structural decoding |
| JSON → CSV | Lossy | Yes (for lists) | Flattens nested fields; body truncated |
| CSV → JSON | Lossy | Import only | Requires column→field mapping |
| JSON → YAML | Partial | Yes | Frontmatter only, no body |
| JSON → Plain text | Lossy | Yes | Body only, metadata stripped |
| Markdown → Plain text | Lossy | Yes | Strip formatting |

**Automatic means:** the API/MCP will perform the conversion when the client requests it. No explicit "convert" step needed.

**Import conversions** (CSV → entries, JSON → entries) require explicit field mapping and are handled by the import/export system, not content negotiation.

### 5. MCP Format Awareness

The MCP protocol returns text content blocks. Currently all tool responses are `json.dumps(result)`. With format support:

- Tool responses can include a `mimeType` field in the content block (MCP spec supports this)
- Clients that understand TOON can request it; others get JSON
- The `kb_schema` tool response describes available formats

```json
{
  "content": [
    {
      "type": "text",
      "mimeType": "text/toon",
      "text": "results[5]{id,title,type,date,tags}:\n  meeting-01,Sprint Planning,meeting,2024-03-15,[dev]\n  ..."
    }
  ]
}
```

### 6. CLI Output Formats

The CLI gains a `--format` flag:

```bash
pyrite search "budget" --format json     # default
pyrite search "budget" --format csv
pyrite search "budget" --format toon
pyrite get meeting-01 --format markdown
pyrite get meeting-01 --format yaml      # frontmatter only
```

### 7. Import Pipeline (Future)

Content negotiation establishes the format registry. The import pipeline (backlog item #36) reuses it:

```bash
pyrite import contacts.csv --type person --mapping name=title,email=metadata.email
pyrite import notion-export.json --format notion
pyrite import vault/ --format obsidian
```

Import is out of scope for this ADR but benefits directly from the format infrastructure.

## Implementation Order

1. **Format registry** — `pyrite/formats/` module with serializer/deserializer protocol
2. **API content negotiation** — `Accept` header handling, response format layer
3. **JSON, Markdown, YAML, CSV serializers** — using existing code paths
4. **TOON serializer** — optional dependency, LLM-optimized output
5. **MCP format support** — `mimeType` in content blocks
6. **CLI `--format` flag** — wire into existing CLI output

## Consequences

### Positive

- AI agents get token-efficient responses, reducing cost and improving accuracy
- CLI users get formats suitable for their toolchain (CSV for spreadsheets, Markdown for docs)
- The format registry is extensible — new formats without modifying core endpoints
- Import/export infrastructure shares the same conversion layer
- MCP responses become more efficient for high-volume operations
- Content negotiation is a standard HTTP pattern — no surprise for API consumers

### Negative

- TOON is a new/niche format — clients need a TOON parser (libraries exist for TS, Python, Go, Rust)
- Optional dependency (`toon-python`) adds a conditional code path
- CSV serialization of nested data requires flattening decisions
- More response code paths means more testing surface

### Risks

- TOON adoption: if the format doesn't gain traction, we maintain a rarely-used serializer (mitigated: it's optional and small)
- Format proliferation: adding too many formats dilutes focus (mitigated: start with JSON + Markdown + TOON + CSV, add others on demand)
- Lossy conversions could surprise users (mitigated: document which conversions are lossy, warn in CLI output)

## Related

- **ADR-0001**: Git-native markdown storage — Markdown remains the canonical on-disk format
- **ADR-0008**: Structured data and schema-as-config — typed fields enable smarter CSV column mapping
- **ADR-0009**: Type metadata — field descriptions improve export headers and import mapping
- **Backlog**: Import/Export Support (#36), Content Negotiation and Format Support (new)
