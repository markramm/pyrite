---
id: llm-prompt-caching
title: "Implement Anthropic prompt caching in LLMService for RAG, chat, QA"
type: backlog_item
tags: [ai, llm, performance, cost, anthropic]
importance: 5
kind: improvement
status: proposed
priority: high
effort: M
rank: 2200
---

## Problem

`pyrite/services/llm_service.py` has zero prompt-caching support. Every call
through `_anthropic_complete` and `_anthropic_stream` builds a fresh kwargs
dict with no `cache_control` blocks. System prompts and retrieved KB context
are re-encoded on every request.

The Anthropic Python SDK supports `cache_control: {"type": "ephemeral"}` on
system blocks and individual content blocks. Cached tokens cost ~10% of the
input price and stay warm for 5 minutes. For Pyrite's workload — RAG chat,
on-save QA, hallucination detection, AI summarize — this is a major missed
optimization.

The `claude-api` skill explicitly calls this out: "Apps built with this skill
should include prompt caching." Pyrite is exactly the kind of app it
describes (long system prompts + KB context replayed across calls).

## Workloads that benefit

- **AI sidebar chat** — same system prompt every turn; same retrieved entries
  often re-fetched across turns in a session
- **QA hallucination detection** — fixed system prompt + each entry replayed
- **AI summarize** — fixed system prompt + bodies
- **Title/tag suggestion** — fixed system prompt + body
- **Query expansion** — fixed system prompt + query

For an active user issuing 100 chat turns in a research session, this is the
difference between roughly 10× and 1× cost on the cached portions.

## Solution

1. Extend `LLMService.complete()` / `.stream()` to accept a `cache_blocks`
   parameter that marks specific content blocks for caching.
2. Default policy: cache the system prompt block automatically when length
   exceeds a configurable threshold (e.g., 1024 tokens). Configurable per
   call via the new parameter.
3. For RAG flows (`ai_ep.py`), restructure the prompt as:
   - System block (always cached)
   - Retrieved-context block (cached when KB selection is stable across
     turns in a session — use a session-keyed cache hint)
   - User turn (never cached)
4. Add unit tests that assert `cache_control` keys land on the expected
   blocks for each provider path.
5. For OpenAI / Gemini paths, document that caching is provider-specific
   (OpenAI prompt-caching is implicit per-org; Gemini has explicit
   ContextCaching). Leave OpenAI path as-is unless we surface usage.
6. Add a single counter for `cache_creation_input_tokens` and
   `cache_read_input_tokens` returned by Anthropic so we can measure the
   hit rate after rollout.

## Acceptance criteria

- `LLMService.complete()` and `.stream()` accept and pass through
  `cache_control` markers on system + content blocks (Anthropic path).
- AI sidebar uses caching for system prompt + retrieved context.
- QA service uses caching for the hallucination-check system prompt.
- A simple log line records `cache_read_input_tokens` so we can measure.
- Tests assert the API call structure includes `cache_control` blocks.
- Documentation: brief note in `kb/components/llm-service.md` (if exists)
  or in the AI integration ADR.

## Related

- `ADR-0007` AI Integration Architecture — pre-dates caching landing in SDK
- Claude API skill: cache_control patterns, hit-rate measurement
- `embedding-body-truncation` — adjacent AI-cost lever
