---
id: wire-llmservice-cache-system-flag-through-ai-endpoints-and-qa-service-r2200-follow-ups
title: Wire LLMService cache_system flag through AI endpoints and QA service (r2200 follow-ups)
type: backlog_item
tags:
- ai
- anthropic
- performance
- llm
- cost
importance: 5
status: proposed
priority: medium
rank: 0
---

Follow-up from r2200 llm-prompt-caching, which landed the LLMService surface (cache_system flag, ephemeral block shape, cache-usage logging) and pinned the contract with TestAnthropicPromptCaching. The remaining ticket items are downstream wiring that needs its own sizing:

1. **AI sidebar / chat endpoint** (pyrite/server/endpoints/ai_ep.py): pass cache_system=True on every turn. The system prompt for the sidebar is stable per session; this is the highest-leverage call site.

2. **QA hallucination detection** (pyrite/services/qa_service.py if extant or equivalent): system prompt is fixed across all entries scanned in a sweep — cache_system=True gives near-100% hit rate.

3. **AI summarize / title-suggest / tag-suggest** (ai_ep.py write endpoints): same fixed system prompt across many entries; cache_system=True.

4. **Default-policy threshold**: ticket proposed auto-enabling caching when system >1024 tokens. Currently opt-in per call. Decide whether to default-on for system blocks above a threshold, or stay explicit per call.

5. **Retrieved-context caching**: ticket proposed a second cache_control block on the retrieved-context portion of a RAG turn so multi-turn chat over the same KB selection pays full price only on the first turn. Needs a session-scoped key or simply 'cache if context bytes > N'. Larger design.

6. **Token-budget metering**: expose cache_creation_input_tokens / cache_read_input_tokens via a counter that surfaces in /api/ai/status or a new /api/ai/usage endpoint so users see their hit rate without grepping logs.

Acceptance per cite:
  - ai_ep chat/summarize/tag-suggest call .complete(cache_system=True) when system text is present.
  - QA hallucination service passes cache_system=True.
  - Either default-on policy implemented OR explicitly deferred with rationale.
  - Test asserts the wiring (one integration test per surface).

Effort: M. Worth doing in a single planned wave so we can measure hit rate end-to-end after rollout.
