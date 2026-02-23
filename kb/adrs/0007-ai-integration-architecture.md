---
type: adr
title: "AI Integration Architecture: Three Surfaces with BYOK"
adr_number: 7
status: accepted
deciders: ["markr"]
date: "2026-02-23"
tags: [architecture, ai-agents, mcp, web, llm]
---

## Context

Pyrite serves two audiences: human researchers using the web UI, and AI agents accessing knowledge programmatically. The AI landscape has three distinct interaction surfaces, each with different needs:

1. **Claude Code** — Developers and power users working in the terminal, using AI to manage KBs, run research workflows, and develop Pyrite itself
2. **MCP clients** — Claude Desktop, Cline, Windsurf, Cowork, and any MCP-compatible AI tool that needs structured access to Pyrite knowledge bases
3. **Web UI** — Browser-based users who want AI-assisted features (summarize, suggest links, auto-tag, chat with KB) using their own API keys

Currently Pyrite has:
- A working MCP server with 3-tier tools (ADR-0006) but no MCP prompts or resources
- A `QueryExpansionService` supporting Anthropic and OpenAI SDKs (narrow: returns term lists only)
- A Claude Code skill (`kb`) for CLI reference, but no research workflow skills
- No Claude Code plugin manifest (`.claude-plugin/plugin.json`)
- No LLM abstraction beyond query expansion
- No web UI AI features

The Superpowers plugin for Claude Code demonstrates an effective pattern: domain-specific skills that enforce methodology through chaining, hard gates, and native task tracking. Pyrite should adapt this pattern for research workflows rather than generic development processes.

## Decision

### 1. Three-Surface Architecture

All three surfaces share the same backend (pyrite CLI + REST API + SQLite). AI features are implemented as backend services, not duplicated per surface.

```
Surface 1: Claude Code Plugin     Surface 2: MCP Server     Surface 3: Web UI
  skills, commands, hooks           tools, prompts, resources   /api/ai/* endpoints
         │                                  │                         │
         └──────────────────┬───────────────┘─────────────────────────┘
                            │
                     pyrite CLI + REST API
                            │
                    ┌───────┴────────┐
                    │  LLM Service   │  (provider-agnostic)
                    │  KB Services   │  (search, CRUD, graph)
                    │  PyriteDB      │  (SQLite + FTS5)
                    └────────────────┘
```

### 2. LLM Abstraction: Anthropic + OpenAI SDKs (No LiteLLM)

**Decision:** Keep the two SDKs we already depend on. Add OpenRouter and Ollama support via OpenAI's `base_url` parameter.

**Rejected alternative: LiteLLM** — 100MB+ dependency, complex configuration, overkill for our needs. Most providers are OpenAI-compatible.

**Provider coverage:**

| Provider | SDK | How |
|----------|-----|-----|
| Anthropic (Claude) | `anthropic` | Direct SDK |
| OpenAI (GPT) | `openai` | Direct SDK |
| OpenRouter (200+ models) | `openai` | `base_url="https://openrouter.ai/api/v1"` |
| Ollama (local models) | `openai` | `base_url="http://localhost:11434/v1"` |
| Any OpenAI-compatible | `openai` | Custom `base_url` |
| Stub/None | — | Graceful no-op for testing and offline use |

**New service:** `pyrite/services/llm_service.py` replaces and generalizes `QueryExpansionService`:

```python
class LLMService:
    """Provider-agnostic LLM interface."""
    async def complete(self, prompt, system=None, max_tokens=1024) -> str
    async def stream(self, prompt, system=None) -> AsyncIterator[str]
    async def embed(self, texts: list[str]) -> list[list[float]]
```

Configuration via `~/.pyrite/config.yaml`:

```yaml
settings:
  ai_provider: "anthropic"          # or openai, openrouter, ollama, stub
  ai_model: "claude-haiku-4-5-20251001"
  ai_api_base: ""                   # custom base URL (for OpenRouter, Ollama, etc.)
  # Keys from env: ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY
```

### 3. BYOK Model (Bring Your Own Keys)

AI features are opt-in and degrade gracefully:
- **No key configured:** AI features are hidden or show "Configure AI provider in settings"
- **Key configured:** Features appear in UI, CLI, and MCP prompts
- **Keys never leave the server.** Web UI calls `/api/ai/*` backend endpoints; keys stay in `~/.pyrite/config.yaml` or environment variables, never sent to browser
- **Cost transparency:** Token usage and estimated cost shown per request in web UI

### 4. Claude Code Plugin Structure

```
.claude-plugin/
  plugin.json              # Plugin manifest
  plugin.md                # Global skill discovery
skills/
  kb/                      # Existing — CLI reference
  pyrite-dev/              # Development workflow for Pyrite contributors
  research-flow/           # Structured research methodology
  investigation/           # Entity investigation and relationship mapping
  backlog-mgmt/            # Backlog management process
commands/
  /research                # Start research session
  /daily                   # Open today's daily note
  /investigate             # Pull together entity knowledge
  /review-kb               # Audit KB health
hooks/
  hooks.json               # Session start, post-tool validation
```

**Skills are research-methodology-focused**, not generic dev process:

| Skill | Methodology |
|-------|-------------|
| `research-flow` | Gather sources → create entries → link findings → build timeline → synthesize |
| `investigation` | Identify entity → collect mentions → map relationships → track source chain → assess confidence |
| `pyrite-dev` | TDD, backlog process, architecture patterns (for Pyrite contributors) |
| `backlog-mgmt` | Complete feature → move to done → update BACKLOG.md → add new items |

### 5. MCP Server Enhancements

Extend the existing MCP server (ADR-0006) with:

**MCP Prompts** — Pre-built prompt templates MCP clients can offer:
- `research_topic` — Research a topic across all KBs
- `summarize_entry` — Summarize an entry
- `find_connections` — Find connections between two entries
- `daily_briefing` — Generate briefing from recent entries

**MCP Resources** — Expose KB content as browsable resources:
- `pyrite://kbs` — List of knowledge bases
- `pyrite://kbs/{name}/entries` — Entry listing for a KB
- `pyrite://entries/{id}` — Entry content with metadata

### 6. Web UI AI Features

Backend endpoints under `/api/ai/`:

| Endpoint | Feature | How it works |
|----------|---------|-------------|
| `POST /api/ai/summarize` | Summarize entry | Entry body → LLM → summary |
| `POST /api/ai/suggest-links` | Link suggestions | Entry + KB context → LLM → wikilink suggestions |
| `POST /api/ai/auto-tag` | Auto-tagging | Entry + existing tag vocabulary → LLM → tag suggestions |
| `POST /api/ai/chat` | Chat with KB | RAG: retrieve relevant entries → LLM conversation |
| `POST /api/ai/expand-query` | Smart search | Query → LLM → expanded terms (existing, moved here) |
| `POST /api/ai/generate` | Generate entry | Prompt → LLM → structured entry with frontmatter |
| `POST /api/ai/assist` | Writing assist | Selected text + action (summarize/expand/rewrite) → LLM |
| `GET /api/ai/status` | Provider status | Current provider, model, whether key is configured |

All endpoints:
- Require AI provider to be configured (return 503 otherwise)
- Support streaming via SSE for generation endpoints
- Return token usage metadata for cost transparency
- Use the shared `LLMService` backend

## Consequences

### Positive
- Single LLM abstraction serves all three surfaces — no duplication
- BYOK means no Pyrite-hosted API costs, no vendor lock-in
- Graceful degradation — everything works without AI, AI features are additive
- Research-focused skills differentiate Pyrite from generic AI tools
- MCP prompts and resources make Pyrite a first-class knowledge source for any AI tool
- OpenRouter support covers 200+ models with zero additional code

### Negative
- Two SDK code paths (Anthropic vs OpenAI-compatible) require maintenance
- Backend streaming (SSE) adds complexity to the FastAPI server
- BYOK means users must manage their own API keys
- Claude Code plugin requires maintaining skills and commands alongside the core codebase

### Risks
- LLM API changes could break provider integrations (mitigated by using official SDKs)
- Token costs could surprise users (mitigated by cost transparency in UI)
- MCP protocol evolution may require server updates (mitigated by staying current with spec)

## Related

- ADR-0006: MCP Three-Tier Tool Model (extended by this ADR)
- ADR-0003: Two-Tier Data Durability (AI-generated content is content-tier, in git)
- `kb/designs/plugin-protocol.md` (plugins can register AI-powered tools)
