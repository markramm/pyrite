---
id: intent-layer
title: "Intent Layer: KB and Type-Level Guidelines, Goals, and Evaluation Rubrics"
type: backlog_item
tags:
- feature
- schema
- intent-engineering
- qa
- agents
kind: feature
priority: high
effort: M
status: planned
links:
- intent-layer-guidelines-and-goals
- qa-agent-workflows
- pyrite-ci-command
- launch-plan
- bhag-self-configuring-knowledge-infrastructure
---

## Problem

Pyrite provides strong context engineering (schemas, type metadata, search) but has no formal place to encode intent — contributing guidelines, project goals, quality standards, and evaluation rubrics. Agents can create structurally valid entries that completely miss the point because "the point" isn't machine-readable.

## Solution

Add `guidelines`, `goals`, and `evaluation_rubric` fields to both `KBSchema` (KB-level) and `TypeSchema` (type-level) in kb.yaml. These flow to agents via the existing `kb_schema` MCP tool and become the rubric for QA validation.

See [[intent-layer-guidelines-and-goals]] for full design.

### Three phases:

1. **Schema + Storage** [S]: Add fields to KBSchema/TypeSchema, parse from kb.yaml, extend to_agent_schema(), update MCP tool response
2. **QA Rubric Evaluation** [M]: QA service reads evaluation_rubric, deterministic rubric items become validation rules, `pyrite ci` runs rubric checks
3. **LLM-Assisted Rubric Evaluation** [L]: Judgment rubric items evaluated by LLM, QA assessment entries link to rubric items, periodic sweeps

## Prerequisites

- QA Phase 1 (done)
- Schema-as-config (done)
- Type metadata system (done)

## Success Criteria

- kb.yaml supports guidelines, goals, and evaluation_rubric at both KB and type level
- Agents see intent context when querying schema via MCP
- QA validates entries against evaluation rubrics
- `pyrite ci` surfaces rubric violations
- Pyrite's own kb.yaml includes guidelines and goals (dogfooding)

## Launch Context

This is the "intent engineering" story for launch. Maps directly to Nate Jones's specification engineering framework. Differentiates Pyrite from every other knowledge tool: "your AI isn't just context-aware, it's intent-aware." Phase 1 should ship before 0.8 launch — it's the feature that makes the blog post land.
