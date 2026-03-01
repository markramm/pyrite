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
status: planned
links:
- launch-plan
- roadmap
---

## Problem

The web UI already has AI features (summarize, auto-tag, suggest-links, RAG chat sidebar — items #26, #27, #32), but the launch plan calls for the web UI to be a full AI interaction portal where users can "see the knowledge graph grow as agents populate a KB" and "interact with the KB and workflows from BYOK model integration." Need to identify what's missing between current AI integration and the launch vision.

## Solution

Audit current AI features against the launch plan's web UI vision and identify gaps.

### What Exists (items #26, #27, #32)

- **AI Provider Settings** (#27): Anthropic, OpenAI, OpenRouter, Ollama provider config in settings UI
- **Summarize, Auto-Tag, Suggest Links** (#26): AI dropdown menu on entry pages
- **RAG Chat Sidebar** (#32): SSE streaming chat with KB context, Cmd+Shift+K toggle

### Likely Gaps to Evaluate

1. **Live graph growth visualization**: WebSocket-driven graph updates when agents create entries (partial — WebSocket infrastructure exists from #23, but graph doesn't subscribe to live updates)
2. **Workflow triggering from UI**: Start agent workflows (research flow, investigation) from the web UI, monitor progress
3. **Task monitoring dashboard**: See active tasks, agent assignments, completion status (depends on task plugin)
4. **QA dashboard**: Visual QA status — verification rates, issue trends, entries needing review (listed in 0.7 roadmap)
5. **Multi-model support in chat**: Switch between providers mid-conversation, compare responses
6. **AI-assisted entry creation**: "Describe what you want to capture" → AI creates the structured entry with correct type and fields
7. **Batch AI operations**: Run summarize/tag/link-suggest across multiple entries (useful after agent bulk creates)

### Deliverable

A prioritized list of gaps with effort estimates, mapped to which launch wave each gap blocks.

## Prerequisites

- Review current state of #26, #27, #32 implementations
- Task plugin phase 1 (already done) for task monitoring gaps

## Success Criteria

- Clear gap analysis document with prioritized items
- Each gap mapped to a launch wave (which wave does it block?)
- Effort estimates for each gap
- Decision on what's 0.8 vs 0.9+ scope
