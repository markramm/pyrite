---
id: gemini-byok-integration
title: "Implement Gemini BYOK API Integration in Svelte UI"
type: backlog_item
tags:
- ui
- api
- gemini
- byok
kind: feature
priority: medium
effort: M
status: proposed
---

## Problem

The Svelte UI currently supports BYOK for Anthropic/OpenAI but not Google Gemini. Users with Gemini API keys cannot use the AI chat sidebar with their own keys.

## Solution

Add BYOK support for Google Gemini in the UI. Map Pyrite's MCP tools to Gemini's Function Calling schema using the google-genai SDK on the backend. Extend the AI provider selection in the UI to include Gemini as an option.

## Success Criteria

- Users can enter a Gemini API key in the UI
- AI chat sidebar works with Gemini models
- Pyrite MCP tools are mapped to Gemini Function Calling schema
- Provider selection includes Gemini alongside existing options
