---
id: add-substack-article-links-on-event-pages-related-articles-field
title: Add Substack article links on event pages (related_articles field)
type: backlog_item
tags:
- enhancement
- cascade
- substack
- content
importance: 5
kind: feature
status: completed
priority: high
effort: M
rank: 0
---

## Refined Design

Cross-KB wikilinks + backlinks, not a new data model.

### How it works
1. Substack articles already exist as KB entries (ramm KB)
2. Add wikilinks from article entries to timeline event IDs: [[2025-01-20--executive-orders-blitz]]
3. Backlink indexing already picks these up as cross-KB links
4. Site cache renderer shows backlinks from whitelisted KBs as a 'Related Articles' section with distinct styling

### Implementation
1. Add trusted_backlink_kbs config (whitelist of KBs whose backlinks get promoted to 'Related Articles')
2. In site cache _render_entry(): filter backlinks by source KB, render whitelisted ones as 'Read the investigation' links with article title and outlet
3. Add the actual wikilinks from ramm KB article entries to cascade-timeline event IDs (content task)

### Why DB-only backlinks
Same pattern as social plugin likes — the link relationship is DB-indexed, not stored in the target entry's frontmatter. The source entry (article) contains the wikilink; the target (event) discovers it via backlink query. No changes needed to event files.

## Status
Design refined. Ready for implementation.
