---
type: backlog_item
title: "Web UI AI: Chat Sidebar (RAG over KB)"
kind: feature
status: proposed
priority: medium
effort: L
tags: [ai, web, search]
---

Conversational AI interface that can answer questions using KB content:

**How it works:**
1. User asks a question in chat sidebar
2. Backend retrieves relevant entries via search (FTS5 + optional semantic)
3. Retrieved entries sent as context to LLM along with the question
4. LLM responds with citations to specific entries
5. Citations are clickable links to entries

**Implementation:**
- `POST /api/ai/chat` — accepts message + conversation history
- Backend does RAG: search → retrieve top-N entries → build context → LLM
- SSE streaming for response
- Chat history maintained in frontend (not persisted)
- Source entries listed below each response

**UI:**
- Collapsible sidebar panel (right side)
- Keyboard shortcut to toggle (Cmd+Shift+K or similar)
- Clear conversation button
- "Ask about this entry" pre-fills context

**Depends on:** llm-abstraction-service, web-ai-summarize-and-tag (shared /api/ai/ patterns)
