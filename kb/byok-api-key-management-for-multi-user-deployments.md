---
id: byok-api-key-management-for-multi-user-deployments
title: BYOK API Key Management for Multi-User Deployments
type: backlog_item
tags:
- web
- security
- hosting
- authentication
- ai
links:
- target: epic-journalists-pyrite-wiki-hosted-research-platform-for-independent-journalists
  relation: subtask_of
  kb: pyrite
importance: 5
---

## Problem

For the hosted service, users need to provide their own LLM API keys (BYOK) for AI features -- chat, research workflows, agent runs. Currently Pyrite uses a single server-side API key. Multi-user deployments need per-user key storage and routing.

## Solution

1. Per-user API key storage in user settings (encrypted at rest)
2. UI settings page for entering/updating API keys (Anthropic, OpenAI, etc.)
3. Backend routes AI requests through the authenticated user's key
4. Key validation on save (test call to verify the key works)
5. Clear error messaging when a user without keys tries to use AI features

## Success Criteria

- Each user stores their own API keys
- AI chat, research workflows, and agent runs use the requesting user's key
- Keys are encrypted at rest
- Hosting operator pays zero LLM costs
