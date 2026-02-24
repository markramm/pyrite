---
type: backlog_item
title: "Web UI AI: Summarize, Auto-Tag, Link Suggestions"
kind: feature
status: done
priority: medium
effort: M
tags: [ai, web, editor]
---

First wave of AI features in the web UI, powered by the LLM abstraction service:

**Summarize Entry:**
- Button on entry view: "Summarize"
- `POST /api/ai/summarize` — sends entry body, returns summary
- Summary saved to entry's `summary` field
- Streaming response shown in UI

**Auto-Tag:**
- Button on entry edit: "Suggest Tags"
- `POST /api/ai/auto-tag` — sends entry body + existing tag vocabulary
- Returns suggested tags, user confirms before applying

**Suggest Links:**
- Button on entry edit: "Find Links"
- `POST /api/ai/suggest-links` — sends entry + context from related entries
- Returns suggested wikilinks with reasoning
- User confirms each suggestion

**Shared patterns:**
- All endpoints return 503 if no AI provider configured
- All return token usage metadata
- UI shows "Configure AI in Settings" if no provider
- Results are suggestions — user always confirms

**Depends on:** llm-abstraction-service, settings-and-preferences (for AI provider config in UI)
