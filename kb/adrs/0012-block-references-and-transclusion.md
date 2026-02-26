---
type: adr
title: "Block References and Transclusion"
adr_number: 12
status: accepted
deciders: ["markr"]
date: "2026-02-24"
tags: [architecture, editor, wikilinks, transclusion]
---

# ADR-0012: Block References and Transclusion

## Context

Users need to reference and embed specific sections of entries, not just link to whole entries. This is essential for:
- Reusing content across entries without duplication
- Citing specific paragraphs or sections in research
- Building composite documents from existing knowledge
- Obsidian-compatible knowledge management workflows

Current wikilink syntax `[[entry-id]]` only supports entry-level linking. There's no way to reference a specific heading or paragraph.

## Decision

Adopt Obsidian-compatible block reference syntax:

1. **Heading links**: `[[entry-id#heading]]` — link to a specific heading within an entry
2. **Block references**: `[[entry-id^block-id]]` — link to a specific block (paragraph)
3. **Heading transclusion**: `![[entry-id#heading]]` — embed the content under a heading
4. **Block transclusion**: `![[entry-id^block-id]]` — embed a specific block
5. **Block ID markers**: `^block-id` at end of paragraphs for block-level addressing

### Syntax details

- `[[entry#heading]]` links to a heading with anchor navigation
- `![[entry#heading]]` transcludes everything from that heading to the next heading of same/higher level
- `![[entry^block-id]]` transcludes a single paragraph/block
- `^block-id` markers must be alphanumeric with hyphens, placed at end of paragraph
- Cross-KB block references: `[[kb:entry#heading]]` combines with cross-KB shortlinks

### Implementation phases

1. **Block ID generation and storage** — `block` table: entry_id, kb_name, block_id, heading, content, position, block_type (heading|paragraph|list|code)
2. **Heading link resolution** — extend wikilink regex to capture `#heading` suffix, add anchor navigation in editor and rendered views
3. **Block reference parsing** — extend wikilink regex to capture `^block-id` suffix, resolve to specific blocks
4. **Transclusion rendering in editor** — `![[...]]` renders as read-only embedded content in TipTap editor, with visual boundary and source attribution
5. **Real-time updates** — when source blocks change, transcluded views update via existing WebSocket infrastructure

### Wikilink regex evolution

Current: `\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]`
New: `\[\[(?:([a-z0-9-]+):)?([^\]|#^]+?)(?:#([^\]|]+?))?(?:\^([^\]|]+?))?(?:\|([^\]]+?))?\]\]`

Groups: (1) kb prefix, (2) target, (3) heading, (4) block-id, (5) display text

### Block table schema

```sql
CREATE TABLE block (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL,
    kb_name TEXT NOT NULL,
    block_id TEXT NOT NULL,
    heading TEXT,
    content TEXT NOT NULL,
    position INTEGER NOT NULL,
    block_type TEXT NOT NULL DEFAULT 'paragraph',
    FOREIGN KEY (entry_id, kb_name) REFERENCES entry(id, kb_name) ON DELETE CASCADE,
    UNIQUE(entry_id, kb_name, block_id)
);
CREATE INDEX idx_block_entry ON block(entry_id, kb_name);
CREATE INDEX idx_block_id ON block(block_id);
```

### Transclusion rendering

- In the TipTap editor, `![[entry#heading]]` renders as an inline read-only card showing the transcluded content
- Cards have a subtle border, source entry title/link, and a "refresh" indicator
- Editing the source entry triggers a WebSocket event that updates all transclusions
- Transclusions are resolved server-side via a new API endpoint: `GET /api/entries/{id}/blocks?heading=...` or `GET /api/entries/{id}/blocks?block_id=...`

## Consequences

### Positive

- **Obsidian compatibility** — users can migrate knowledge bases with block references intact
- **Content reuse** — reduces duplication across entries
- **Granular linking** — research and analysis can reference specific claims/paragraphs
- **Composable documents** — entries can be assembled from blocks of other entries
- **Existing WebSocket infrastructure** handles real-time updates

### Negative

- **Increased storage** — block index adds rows per paragraph per entry
- **Editor complexity** — transclusion rendering requires custom TipTap nodes and real-time resolution
- **Fragile references** — renaming headings or moving blocks breaks references (mitigated by block IDs being stable)
- **Index performance** — every entry save must re-extract and upsert blocks

### Risks

- **Block ID collision** — auto-generated IDs from content hashes could collide; mitigated by entry-scoped uniqueness
- **Circular transclusion** — A transcludes B which transcludes A; must detect and break cycles with depth limit
- **Large transclusions** — transcluding a long section could make entries unwieldy; consider max content size

## Related

- [ADR-0011: Collections and Views](0011-collections-and-views.md) — collection embedding uses `![[collection-id]]{ view options }` which extends this transclusion syntax
- Backlog #18: Cross-KB Shortlinks — `[[kb:entry#heading]]` combines cross-KB and block reference syntax
- Current wikilink implementation: `pyrite/storage/index.py` line 21, `web/src/lib/editor/wikilink-utils.ts`
