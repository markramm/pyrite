---
type: backlog_item
title: "AI Provider Settings in Web UI"
kind: feature
status: proposed
priority: medium
effort: S
tags: [ai, web, settings]
---

Settings page section for configuring AI provider (BYOK):

**UI in /settings:**
- Provider dropdown: Anthropic, OpenAI, OpenRouter, Ollama, None
- Model selection (text input or dropdown of common models per provider)
- API key input (password field, stored server-side in config.yaml)
- Custom base URL (for OpenRouter, Ollama, self-hosted)
- "Test Connection" button — calls `GET /api/ai/status` to verify

**Backend:**
- `GET /api/ai/status` — returns provider, model, whether key is configured, test result
- `PUT /api/settings` — already planned, add AI settings fields
- Keys stored in `~/.pyrite/config.yaml` (never sent to browser after save)

**UX:**
- If no provider configured: AI buttons throughout UI show "Configure AI in Settings"
- Token usage and estimated cost shown per AI request
- Clear messaging: "Your API keys stay on this machine"

**Depends on:** settings-and-preferences (the settings page infrastructure)
