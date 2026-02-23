---
type: backlog_item
title: "LLM Abstraction Service (Provider-Agnostic)"
kind: feature
status: completed
priority: high
effort: M
tags: [ai, backend, architecture]
---

Replace narrow `QueryExpansionService` with a general-purpose `LLMService` in `pyrite/services/llm_service.py`.

**Interface:**
- `complete(prompt, system, max_tokens)` → str
- `stream(prompt, system)` → AsyncIterator[str]
- `embed(texts)` → list[list[float]]

**Provider support via Anthropic + OpenAI SDKs:**
- Anthropic (Claude) — direct SDK
- OpenAI (GPT) — direct SDK
- OpenRouter (200+ models) — OpenAI SDK with `base_url`
- Ollama (local) — OpenAI SDK with `base_url`
- Stub/None — graceful no-op

**Config:** `~/.pyrite/config.yaml` settings (ai_provider, ai_model, ai_api_base). Keys from environment variables.

**Migrate** `QueryExpansionService` to use `LLMService` internally. Add `GET /api/ai/status` endpoint.

See ADR-0007 for full rationale. This is the foundation all AI features build on.

## Completed

Implemented in Wave 2. `LLMService` with Anthropic, OpenAI (+ OpenRouter/Ollama via base_url), and stub backends. Lazy SDK imports with helpful error messages. `GET /api/ai/status` endpoint. 19 tests with mocked SDK calls.
