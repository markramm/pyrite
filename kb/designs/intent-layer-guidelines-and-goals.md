---
id: intent-layer-guidelines-and-goals
title: "Intent Layer: KB and Type-Level Guidelines, Goals, and Evaluation Rubrics"
type: design_doc
status: draft
tags:
- design
- intent-engineering
- qa
- schema
- agents
links:
- launch-plan
- bhag-self-configuring-knowledge-infrastructure
- qa-agent-workflows
- pyrite-ci-command
- permissions-model
---

## Problem

Pyrite has strong **context engineering** infrastructure — schemas, type metadata, AI instructions, search, MCP tools. Agents get the right tokens. But there's no formal place to encode **intent** — the "why" behind the KB, the quality standards, the editorial values, the goals that should guide every agent's decisions.

Currently:
- `kb.yaml` has `name`, `description`, `kb_type`, `types`, `policies`, `validation` — all structural
- `ai_instructions` on types tell agents how to create entries, but not *why* or to what standard
- QA Phase 1 validates structural rules (missing fields, broken links) but can't validate against editorial intent because that intent isn't formally specified
- Contributing guidelines live in ad-hoc notes or README files that agents may or may not find

This means: an agent can create a structurally valid entry that completely misses the point. A finding with all the right fields but no source chain. An ADR that documents the decision but not the alternatives considered. A backlog item with acceptance criteria that optimize for the wrong thing.

## Solution

Add a formal **intent layer** to both KB-level and type-level configuration. This encodes guidelines, goals, and evaluation rubrics that agents consume when creating content and QA agents consume when validating it.

### The Three Layers (Nate Jones Framework)

This design maps to the emerging "specification engineering" framework:

1. **Context Engineering** (already built) — KB structure, type definitions, search, MCP tools. Agents get the right information.
2. **Intent Engineering** (this design) — Guidelines, goals, evaluation rubrics. Agents know what matters and why.
3. **Specification Engineering** (task plugin + QA) — Acceptance criteria, decomposition, evaluation. Agents execute autonomously against verifiable specs.

### KB-Level Intent

Add `guidelines` and `goals` sections to `kb.yaml`:

```yaml
name: investigation-xyz
kb_type: journalism
description: "Follow the money investigation into ..."

# Intent layer — consumed by all agents working in this KB
guidelines:
  # Contributing guidelines — editorial standards and values
  contributing: |
    Every claim must link to a primary source document.
    Prefer public records over anonymous tips.
    Flag confidence level on all findings.
    When sources conflict, document both and note the conflict.
    Never publish unverified claims as findings — use the 'lead' type instead.

  # Quality standards — what "good" looks like here
  quality: |
    Findings must be defensible for publication.
    Source chains must be complete — no gaps between claim and evidence.
    Entity profiles should be comprehensive enough for a reader
    unfamiliar with the investigation to understand the significance.

  # Voice and tone — how content should read
  voice: |
    Factual, precise, no speculation. Attribution required.
    Use neutral language for all subjects until findings are confirmed.

# Goals — what this KB exists to achieve
goals:
  primary: |
    Build a complete financial flow map between entities X, Y, Z.
    Identify undisclosed relationships between board members.
  success_criteria: |
    All findings must be defensible for publication.
    Complete source chain for every claim.
    Financial flow map covers 2019-2024 with no unexplained gaps.
  constraints: |
    Only use publicly available records and on-the-record sources.
    Do not contact subjects directly without editor approval.
```

### Type-Level Intent

Extend `TypeSchema` to include `guidelines` and `goals` alongside the existing `ai_instructions`:

```yaml
types:
  finding:
    description: "Investigative conclusion supported by evidence"
    ai_instructions: "Create findings only when evidence supports a conclusion..."
    # Intent layer additions:
    guidelines: |
      Must include evidence chain with at least two corroborating sources.
      Confidence must reflect source quality, not analyst conviction.
      Counter-evidence must be documented, not omitted.
    goals: |
      Publishable finding with complete, defensible source chain.
    evaluation_rubric:
      - "Evidence chain links to at least one primary source document"
      - "Confidence level matches evidence strength (not 'confirmed' from single source)"
      - "Counter-evidence section present if any conflicting information exists"
      - "All referenced entities exist as person/organization entries"

  lead:
    description: "Unverified tip or thread to follow"
    ai_instructions: "Use for unverified information that needs investigation..."
    guidelines: |
      Leads are explicitly unverified. Never promote a lead to a finding
      without going through the verification workflow.
      Priority reflects potential impact, not certainty.
    goals: |
      Capture potential threads quickly without overstating certainty.
    evaluation_rubric:
      - "Clearly marked as unverified"
      - "Source attribution present (even if source is anonymous)"
      - "Priority reflects potential impact if verified"
```

### How Each Agent Consumes Intent

**Research/creation agents** read KB-level `guidelines.contributing` and type-level `guidelines` + `ai_instructions` before creating entries. The combined context tells them not just what fields to fill but what quality standards to meet and what values to uphold.

**QA agents** read KB-level `guidelines.quality` and type-level `evaluation_rubric` as their validation checklist. Structural QA (existing Phase 1) checks field presence. Intent QA (new, Phase 2+) checks rubric items. The rubric items are evaluable assertions — a QA agent can check "evidence chain links to at least one primary source document" by following the links.

**`pyrite ci`** runs structural validation (schema compliance) and can optionally run rubric checks against the evaluation_rubric lists. Rubric items that require LLM judgment are flagged as warnings, not errors, in CI — hard failures are reserved for structural rules.

**Orchestrator agents** read KB-level `goals` to understand what the KB is trying to achieve. When decomposing work via `task_decompose`, the goals inform what subtasks matter. When prioritizing, the goals define the optimization target.

### Resolution Order

Extend the existing 4-layer precedence to include intent fields:

1. KB-level `types.{type}.guidelines` (highest — project-specific override)
2. Plugin `get_type_metadata()` returning `guidelines` key
3. Core type defaults (if we add default guidelines to CORE_TYPE_METADATA)
4. Empty string (no guidelines specified)

Same for `goals` and `evaluation_rubric`.

KB-level guidelines (the top-level `guidelines` section) are additive — they apply to all types, and type-level guidelines are additional per-type constraints. They don't replace each other; agents see both.

### How Intent Flows to Agents

Extend `KBSchema.to_agent_schema()` to include the intent layer:

```python
def to_agent_schema(self) -> dict[str, Any]:
    result = {
        "name": self.name,
        "description": self.description,
        "kb_type": self.kb_type,
        # New: KB-level intent
        "guidelines": self.guidelines,
        "goals": self.goals,
        "types": { ... }
    }
    for type_name, type_schema in self.types.items():
        type_info = { ... }
        # New: type-level intent
        if type_schema.guidelines:
            type_info["guidelines"] = type_schema.guidelines
        if type_schema.goals:
            type_info["goals"] = type_schema.goals
        if type_schema.evaluation_rubric:
            type_info["evaluation_rubric"] = type_schema.evaluation_rubric
    return result
```

The MCP `kb_schema` tool already returns this schema — agents automatically get intent context when they query the schema.

### QA Integration

**Structural QA (Phase 1, existing):** Checks schema compliance. No change needed.

**Intent QA (Phase 2+, enhanced):** QA agents receive the evaluation_rubric for each type and validate entries against it. Rubric items fall into two categories:

- **Deterministic** (checkable without LLM): "links to at least one source document" — follow links, verify targets exist
- **Judgment** (requires LLM): "confidence level matches evidence strength" — LLM evaluates with rubric as prompt

Deterministic rubric items become QA Phase 1 rules (fast, no LLM cost). Judgment rubric items become QA Phase 2-3 checks (LLM-assisted, higher cost).

**`pyrite ci` integration:** Runs deterministic rubric checks. Surfaces judgment rubric items as advisories. Teams can configure severity thresholds.

**Periodic QA sweeps:** Scheduled review of all entries against current rubrics. Catches drift — entries written before rubric updates that no longer meet standards. Produces QA assessment entries linking to the specific rubric items that failed.

### Workflow Integration

Workflows already define valid state transitions. The intent layer adds **why** each transition exists:

```yaml
types:
  finding:
    workflow:
      states: [draft, review, confirmed, contested, retracted]
      transitions:
        draft -> review: "Author believes evidence is sufficient"
        review -> confirmed: "Independent reviewer verified source chain"
        review -> contested: "Reviewer found conflicting evidence"
        confirmed -> retracted: "New evidence invalidates the finding"
      # Intent: what this workflow ensures
      purpose: |
        Ensures no finding reaches 'confirmed' without independent review.
        Prevents single-agent confirmation bias.
```

This is informational for now — agents read it to understand the process — but could become enforceable (e.g., the `review -> confirmed` transition requires a different agent than the one who created the finding).

## Implementation

### Phase 1: Schema + Storage (Small)

- Add `guidelines: dict[str, str]` and `goals: dict[str, str]` to `KBSchema`
- Add `guidelines: str`, `goals: str`, `evaluation_rubric: list[str]` to `TypeSchema`
- Parse from kb.yaml in `KBSchema.from_dict()`
- Extend `to_agent_schema()` to include new fields
- Update `kb_schema` MCP tool response
- Tests: parsing, resolution, agent schema export

### Phase 2: QA Rubric Evaluation (Medium)

- QA service reads evaluation_rubric per type
- Deterministic rubric items extracted and added as validation rules
- `pyrite ci` runs rubric checks
- Rubric violations surface in QA status output

### Phase 3: LLM-Assisted Rubric Evaluation (Large)

- Judgment rubric items evaluated by LLM with entry content + rubric as prompt
- QA assessment entries link to specific rubric items
- Periodic sweep runs judgment checks on entries not yet assessed
- Confidence scoring on LLM rubric evaluations

## Relationship to Existing Features

- **ai_instructions** remain — they tell agents *how* to create entries (field-level guidance). Guidelines tell agents *why* and *to what standard*.
- **QA Phase 1** remains — structural validation is fast and cheap. Rubric evaluation is additive.
- **`pyrite ci`** gains rubric checking as an optional mode.
- **Workflows** gain optional `purpose` annotations — informational first, enforceable later.

## Success Criteria

- A new KB creator can specify intent (guidelines, goals, rubric) alongside schema in kb.yaml
- Agents creating entries see both ai_instructions (how) and guidelines (why/standard)
- QA agents validate against evaluation rubrics, not just structural rules
- `pyrite ci` surfaces rubric violations
- The software-kb extension's kb.yaml includes guidelines and goals (dogfooding)
- Launch blog post can show: "define your standards → agents follow them → QA validates against them"
