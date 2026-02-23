---
type: backlog_item
title: "Ephemeral KBs for Agent Swarm Shared Memory"
kind: feature
status: proposed
priority: medium
effort: M
tags: [ai, agents, collaboration, multi-kb]
---

## Summary

Ephemeral, short-lived knowledge bases that agent swarms can use as a lightweight shared memory system during parallel work (waves). Agents write discoveries, decisions, and warnings to a shared KB; other agents (and the orchestrator) can search it for context.

## Motivation

When multiple agents run in parallel (e.g., 3 agents in a wave), they cannot communicate. Each starts from the same git snapshot but diverges immediately. If Agent A discovers a gotcha (circular import, unexpected file state, design constraint), Agents B and C will never know. The orchestrator only discovers conflicts at merge time.

An ephemeral KB solves this by giving agents a shared, searchable scratchpad that persists for the duration of the wave and is archived or deleted afterward.

## Key Capabilities

- **Create on demand**: `pyrite kb create --ephemeral --name wave-3-memory --ttl 24h`
- **Agents write findings**: `pyrite create -k wave-3-memory -t note --title 'api.py has circular import risk' -b '...'`
- **Agents read context**: `pyrite search 'api import' -k wave-3-memory`
- **Auto-cleanup**: Ephemeral KBs are deleted or archived after TTL expires or wave completes
- **Structured entries**: Full frontmatter support (tags, types, importance) so findings are categorized
- **Semantic search**: Agents can find conceptually related findings, not just keyword matches

## Design Considerations

- Storage: temp directory with markdown files + SQLite index (same as regular KBs)
- Lifecycle: created before wave launch, deleted/archived after merge
- Access: all agents in the wave get the KB name in their prompt
- Indexing: lightweight — auto-index on create, no background sync needed
- Archive option: move to kb/archives/wave-N/ for post-mortem analysis
- Could integrate with the parallel-agents.md merge protocol

## Use Cases Beyond This Project

- **AI dev teams**: Any multi-agent workflow where agents work in parallel and need lightweight coordination
- **Research sprints**: Multiple agents researching different aspects of a topic, sharing findings
- **Code review swarms**: Agents reviewing different files, flagging cross-cutting concerns
- **CI/CD pipelines**: Agents running different test suites, sharing failure context

## Implementation Sketch

1. Add `--ephemeral` and `--ttl` flags to `pyrite kb add`
2. Ephemeral KBs stored in a temp/ephemeral directory (configurable)
3. Auto-index entries on create (no separate sync step needed)
4. Add `pyrite kb archive <name>` to snapshot ephemeral KB to permanent storage
5. Add `pyrite kb gc` to clean up expired ephemeral KBs
6. Update wave planning docs to include ephemeral KB in agent prompts

## Dependencies

- None (builds on existing multi-KB and CLI infrastructure)

## Acceptance Criteria

- [ ] Can create an ephemeral KB with a TTL
- [ ] Agents can CRUD entries via CLI
- [ ] Search (keyword + semantic) works on ephemeral KBs
- [ ] Expired KBs are automatically cleaned up
- [ ] Archive command preserves KB contents permanently
- [ ] Wave completion checklist includes ephemeral KB teardown
