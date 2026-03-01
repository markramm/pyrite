---
id: extension-type-protocols
title: "Extension Type Protocols: Structural Subtyping for Knowledge Types"
type: backlog_item
tags:
- feature
- extensions
- protocols
- type-system
- architecture
kind: feature
priority: medium
effort: L
status: planned
links:
- extension-type-protocols
- intent-layer-guidelines-and-goals
- extension-registry
- bhag-self-configuring-knowledge-infrastructure
---

## Problem

Extensions need to interoperate without explicit dependency graphs. The journalism plugin needs "claimable" behavior, the software plugin needs "evidence-linked" behavior for QA, but hard dependencies between extensions create a brittle ecosystem.

## Solution

Structural subtyping via protocols, modeled on Python's `typing.Protocol`. Types satisfy protocols implicitly by having the right fields, hooks, and tools. Extensions declare `requires_protocols` and `provides_protocols` instead of depending on specific other extensions.

See [[extension-type-protocols]] design doc for full details.

### Key Design Decisions

- **Structural, not nominal**: Types satisfy protocols by having the right shape, not by declaring inheritance
- **Fine-grained is OK**: Agents can search and hold many protocol contracts in context — the traditional "too many micro-contracts" objection doesn't apply when your consumers are AI agents with KB access
- **Batteries-included core protocols**: Ship ~8 core protocols (statusable, claimable, evidence-linked, source-tracked, prioritizable, reviewable, decomposable, temporal) covering 80% of interop needs
- **Protocols are KB entries**: Searchable, documented, with guidelines and evaluation rubrics via the intent layer

### Three phases:

1. **Protocol definition format** [S]: `protocol` entry type, core protocols as KB entries, `pyrite protocol list/show`
2. **Structural satisfaction checking** [M]: `pyrite protocol check`, extension manifest requires/provides, install-time validation
3. **Registry integration** [M]: Protocol search in extension registry, agent-driven discovery

## Prerequisites

- Intent layer phase 1 (protocols need guidelines/rubrics)
- Extension registry (protocols live in the registry KB)
- Schema-as-config (done)

## Success Criteria

- Core protocols defined and documented as KB entries
- `pyrite protocol check --type task --protocol claimable/1.0` validates structural satisfaction
- Extension install validates protocol requirements
- An agent can search for "types satisfying evidence-linked" and get correct results
- At least 3 extensions (task, software, journalism) using protocol declarations

## Launch Context

Phase 1 (protocol definitions) can ship with 0.8 as documentation. Phase 2 (checking) is post-launch. Phase 3 (registry integration) ships with the extension registry. The protocol system is the long-term answer to extension interoperability — it doesn't need to be fully automated at launch, but the design should be visible.
