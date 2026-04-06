---
id: embedding-body-truncation
type: backlog_item
title: "Embedding service silently truncates body to 500 chars, degrading semantic search"
kind: bug
status: proposed
priority: high
effort: M
tags: [search, embeddings, semantic-search]
---

## Problem

In `services/embedding_service.py` (~line 37-38), the `_entry_text()` helper truncates entry bodies to 500 characters before embedding:

```python
body = entry.get("body") or ""
if body:
    parts.append(body[:500])
```

This is silent — no log, no config, no indication that semantic search quality is being limited. For entries with substantive bodies (many cascade-research entries are 500+ lines), the embedding only captures the first paragraph. This means semantic search results are biased toward entries whose key content appears early in the body.

## Expected Behavior

- Truncation limit should be configurable (or use the model's actual token limit)
- When truncation occurs, it should be logged at DEBUG level with entry ID and original length
- Consider chunking strategies: embed the full entry in overlapping windows, or at minimum embed title + summary + first N chars of body
- `index embed --stats` should report how many entries were truncated

## Context

The all-MiniLM-L6-v2 model has a 256 token (~1200 char) effective window. The 500-char limit is conservative but reasonable for that model. However, if the model is upgraded, this hardcoded limit becomes a silent bottleneck. At minimum, tie the limit to the model's actual capacity.

## Acceptance Criteria

- Truncation limit is derived from model config, not hardcoded
- Truncated entries are counted in embedding stats
- `pyrite index embed --stats` shows truncation count
