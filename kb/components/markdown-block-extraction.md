---
id: markdown-block-extraction
title: Markdown Block Extraction
type: component
kind: utility
path: pyrite/utils/markdown_blocks.py
owner: core
dependencies: []
tags:
- core
- block-refs
- indexing
---

Parses markdown text into discrete blocks (headings, paragraphs, lists, code) for block-level referencing. Each block gets an auto-generated ID from SHA-256(content)[:8], unless an explicit `^block-id` marker is present.

Key function: `extract_blocks(markdown_text) -> list[dict]` returns blocks with `block_id`, `heading`, `content`, `position`, `block_type`.

Used by IndexManager during entry indexing to populate the `block` table (migration v5).
