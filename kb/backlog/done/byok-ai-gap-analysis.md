---
id: byok-ai-gap-analysis
title: "BYOK AI Integration Gap Analysis"
type: backlog_item
tags:
- feature
- ai
- web-ui
- gap-analysis
kind: improvement
priority: medium
effort: M
status: completed
links:
- launch-plan
- roadmap
- gemini-byok-integration
---

## Problem

The web UI already has AI features (summarize, auto-tag, suggest-links, RAG chat sidebar), but the launch plan calls for the web UI to be a full AI interaction portal where users can "see the knowledge graph grow as agents populate a KB" and "interact with the KB and workflows from BYOK model integration." Need to identify what's missing between current AI integration and the launch vision.

## Audit Results (March 2026)

### What Works — Full BYOK Support

All core AI features work end-to-end with user-provided API keys. No hardcoded keys, no forced cloud integrations.

| Feature | Status | Providers | Notes |
|---------|--------|-----------|-------|
| **AI Provider Settings** | Done | All 4 | Settings UI stores to DB, env vars as fallback |
| **Summarize** | Done | All 4 | POST /api/ai/summarize, 256 token output |
| **Auto-Tag** | Done | All 4 | Suggests 3-7 tags with reasoning, knows existing vocabulary |
| **Suggest Links** | Done | All 4 | Hybrid search → AI evaluation of candidates |
| **RAG Chat Sidebar** | Done | All 4 | SSE streaming, KB context, source citations, Cmd+Shift+K |
| **QA Dashboard** | Done | N/A | Validation status, issue trends, entries needing review |
| **Semantic Search** | Done | Local | sentence-transformers (all-MiniLM-L6-v2), no API key needed |
| **MCP Server** | Done | N/A | Agents bring their own LLM, independent of Pyrite AI config |

**Supported providers:** Anthropic, OpenAI, OpenRouter, Ollama. All configured via Settings UI or env vars. DB settings take precedence over config.yaml.

### Minor Issues (not blockers)

1. **Test Connection is shallow** — `/api/ai/status` only checks if key exists, doesn't validate it works. User gets "configured" with an invalid key, then errors on first AI operation. Fix: make test button do an actual API call. **Effort: XS**

2. **Anthropic can't embed** — Anthropic has no public embeddings API. If user picks Anthropic as their LLM provider, chat/summarize/tags work fine, but the embedding service uses local sentence-transformers anyway (independent of LLM provider). This is actually fine — embeddings are always local. No user-facing issue. **No action needed.**

3. **Semantic search requires optional dep** — `pip install 'pyrite[semantic]'` needed for sqlite-vec + sentence-transformers. Without it, search falls back to keyword silently. Docker image includes it by default. **No action needed for deployed instances.**

### Remaining Gaps — Prioritized

Gaps from the original backlog item, re-assessed against current state:

| # | Gap | Effort | Priority | Milestone | Assessment |
|---|-----|--------|----------|-----------|------------|
| 1 | **Gemini provider** | M | Medium | 0.16+ | Separate backlog item [[gemini-byok-integration]]. Google AI SDK + Function Calling mapping. Not a blocker — 4 providers already cover most users. |
| 2 | **AI-assisted entry creation** | S | Medium | 0.16+ | "Describe what you want" → structured entry. Nice UX but not blocking launch. Chat sidebar already helps with this workflow manually. |
| 3 | **Batch AI operations** | S | Low | Post-launch | Summarize/tag/link-suggest across multiple entries. Useful for bulk imports but not a launch requirement. |
| 4 | **Live graph growth** | M | Low | Post-launch | WebSocket infra exists but graph doesn't subscribe to live updates. Cool demo but not functional blocker. |
| 5 | **Workflow triggering from UI** | L | Low | Post-launch | Start research/investigation workflows from browser. Requires agent orchestration layer that doesn't exist yet. |
| 6 | **Task monitoring dashboard** | M | Low | Post-launch | Depends on task plugin (phases 1-2 done). Better suited for 0.17+ when task plugin matures. |
| 7 | **Multi-model chat** | S | Low | Post-launch | Switch providers mid-conversation. Niche feature, post-launch. |

### Verdict

**BYOK is launch-ready.** All four providers work. All AI features (summarize, tag, suggest-links, RAG chat) work with user-provided keys. Semantic search works locally with no API key. The remaining gaps are nice-to-have features for post-launch, not BYOK integration issues.

The only pre-launch improvement worth doing is the shallow test-connection fix (XS effort) — everything else can wait for 0.16+.

## Deployment Notes for BYOK

**Self-hosters:** Configure AI in the Settings UI after first login. No env vars needed — the UI stores keys to the database.

**Docker deployments:** Optionally set env vars for server-wide defaults:
```bash
ANTHROPIC_API_KEY=sk-ant-...    # or OPENAI_API_KEY
```
Users can still override in Settings UI (DB settings take precedence).

**Semantic search:** Included in Docker image by default (`pyrite[semantic]`). Works without any API key — uses local sentence-transformers model.
