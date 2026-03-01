---
id: event-bus-webhooks
title: "Event Bus and Webhook System"
type: backlog_item
tags:
- feature
- infrastructure
- webhooks
- events
- integration
kind: feature
priority: medium
effort: M
status: planned
links:
- websocket-multi-tab
- qa-agent-workflows
- roadmap
---

## Problem

Pyrite's hooks are per-KB, synchronous, and internal. There's no way for external systems to react to KB events. Use cases that need this:

- Slack notification when a QA validation fails
- CI trigger when an entry is created or modified
- Dashboard update when the knowledge graph changes
- "Watch the graph grow" live visualization (extends existing WebSocket #23)
- Cross-KB workflows (finding confirmed in KB-A → task created in KB-B)
- External agent systems subscribing to KB changes

## Solution

### Internal Event Bus

Lightweight pub/sub within the Pyrite process:

- Events: `entry.created`, `entry.updated`, `entry.deleted`, `qa.validation_failed`, `task.claimed`, `task.completed`, `kb.indexed`, `schema.changed`
- Existing hooks migrate to event subscribers (backwards compatible)
- WebSocket clients subscribe to event streams (extends #23)
- Event payloads include entry ID, KB name, type, actor, timestamp

### Webhook Dispatch

External HTTP callbacks:

```yaml
# kb.yaml or pyrite.yaml
webhooks:
  - url: https://hooks.slack.com/...
    events: [qa.validation_failed]
  - url: https://ci.example.com/trigger
    events: [entry.created, entry.updated]
    filter:
      kb: project-kb
      type: backlog_item
```

- Async dispatch (don't block the write path)
- Retry with exponential backoff
- Webhook secret for signature verification

### Event Log (optional)

Persist recent events to DB for replay and debugging. Useful for agents that want to "catch up" on what happened while they were offline.

## Prerequisites

- WebSocket infrastructure (done, #23)
- Hook system (done, used by task plugin and QA)

## Success Criteria

- Internal events fire on all write operations
- WebSocket clients can subscribe to filtered event streams
- At least one webhook integration working (Slack or generic HTTP)
- Existing hooks continue to work unchanged
- Event payloads are structured and documented

## Launch Context

Not strictly needed for 0.8 alpha, but valuable for the demo site (live graph updates) and corporate adoption (Slack integration). The internal event bus is the foundation — webhooks and external integrations build on top.
