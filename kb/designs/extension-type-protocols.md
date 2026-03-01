---
id: extension-type-protocols
title: "Extension Type System: Structural Protocols for Knowledge Types"
type: design_doc
status: draft
tags:
- design
- extensions
- protocols
- type-system
- architecture
links:
- bhag-self-configuring-knowledge-infrastructure
- intent-layer-guidelines-and-goals
- launch-plan
---

## Problem

Extensions need to interoperate. The journalism plugin's LeadEntry needs "claimable" behavior from the task plugin. The software plugin's BacklogItem needs "evidence-linked" behavior for QA. But explicit extension-to-extension dependencies create a brittle graph — you can't install journalism without task, can't install task without core, version mismatches break everything.

Traditional solutions (npm-style dependency trees, Java interfaces, explicit inheritance hierarchies) all assume human developers managing the complexity. Pyrite's consumers are primarily AI agents that can search a KB of interface definitions and hold fine-grained contracts in context.

## Design Decision

**Pyrite's extension type system uses structural subtyping via protocols (like Python's `typing.Protocol`) rather than nominal inheritance hierarchies.**

Types satisfy protocols implicitly by having the right fields, hooks, and tools — not by explicitly declaring "I implement X." This is duck typing for knowledge: if it has a status, an assignee, and a claim workflow, it's claimable.

## The Python Analogy

The mapping between Python's type system and Pyrite's knowledge type system is deliberate:

| Python | Pyrite |
|--------|--------|
| Class | Entry type — has data (fields/frontmatter) and behavior (workflows, hooks, validation) |
| `typing.Protocol` | Knowledge protocol — structural contract (required fields, hooks, tools) |
| Type annotations | Schema definitions — field types, required/optional, controlled vocabulary |
| `mypy` | `pyrite ci` / QA structural validation — static checking at commit time |
| `pytest` | QA evaluation rubrics — runtime validation against intent |
| Module | KB — namespace with exports, docstrings (`guidelines`), and `__all__` (`goals`) |
| `ABC` | Explicit type extension — `ADREntry(NoteEntry)` for field inheritance |
| `isinstance()` | `pyrite search "types satisfying claimable"` — agent-queryable |
| `__iter__`, `__len__` | `has_status`, `has_evidence_chain` — small behavioral contracts |

## Protocol Definition

Protocols are defined as KB entries in the extension registry (or in a core `protocols/` directory). They're searchable, documented, and consumable by both humans and agents.

### Example: `claimable/1.0`

```yaml
---
id: protocol-claimable
title: "claimable/1.0"
type: protocol
version: "1.0"
tags: [protocol, workflow, coordination]
---

# claimable/1.0

A type that supports atomic assignment to an agent or user.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| status | select | Must include at least: open, claimed, done |
| assignee | string | Agent or user identifier |

## Required Behavior

- **Atomic claim**: Transitioning from open → claimed must be atomic (no double-claims under concurrency)
- **Status validation**: before_save hook enforces valid transitions
- **Assignee set on claim**: assignee must be non-empty when status is "claimed"

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| claimed_at | datetime | When the claim occurred |
| claim_reason | string | Why this agent claimed this entry |

## Invariants

- An entry with status "claimed" always has a non-empty assignee
- An entry with status "open" always has an empty assignee
- Transition from claimed → open clears the assignee (unclaim)

## Guidelines

Use this protocol for any entry type where agents need exclusive
assignment. The atomic claim prevents duplicate work in agent swarms.
If your type doesn't need exclusive assignment (e.g., multiple agents
can work on it simultaneously), don't use claimable — use a different
coordination pattern.
```

### Example: `evidence-linked/1.0`

```yaml
---
id: protocol-evidence-linked
title: "evidence-linked/1.0"
type: protocol
version: "1.0"
tags: [protocol, qa, research]
---

# evidence-linked/1.0

A type whose claims are backed by linked evidence entries.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| evidence | multi-ref | Links to entries that support this claim |
| confidence | number | 0.0-1.0, reflects evidence strength |

## Required Behavior

- **Source chain validation**: QA can follow evidence links and verify targets exist
- **Confidence reflects evidence**: confidence level must be justifiable from linked evidence

## Evaluation Rubric

- Evidence links resolve to existing entries
- Confidence > 0.8 requires at least two corroborating evidence entries
- Confidence < 0.3 should be flagged as "needs more evidence"

## Guidelines

Use for any entry type that makes claims about the world. Findings,
assessments, conclusions, recommendations — anything that needs to
show its work. The evaluation rubric feeds directly into QA validation.
```

## How Types Satisfy Protocols

Satisfaction is structural, not declared. A type satisfies a protocol if:

1. It has all required fields with compatible types
2. It has hooks/tools that provide the required behavior
3. Its workflow (if any) supports the required transitions

### Checking Satisfaction

```bash
# Agent asks: what types satisfy claimable?
pyrite search "types satisfying claimable" -k extension-registry

# Programmatic check
pyrite protocol check --type task --protocol claimable/1.0
# ✅ task satisfies claimable/1.0
#   - status: select [open, claimed, in_progress, blocked, review, done, failed] ✅
#   - assignee: string ✅
#   - atomic claim: task_claim tool provides CAS ✅

pyrite protocol check --type note --protocol claimable/1.0
# ❌ note does not satisfy claimable/1.0
#   - status: missing ❌
#   - assignee: missing ❌
```

### Explicit Declaration (Optional)

Types *may* explicitly declare protocol satisfaction for discoverability, but it's not required:

```yaml
# In a type definition or extension manifest
types:
  lead:
    satisfies: [claimable/1.0, evidence-linked/1.0]
    fields:
      status: {type: select, values: [open, claimed, investigating, verified, dead_end]}
      assignee: {type: string}
      evidence: {type: multi-ref}
      confidence: {type: number, min: 0, max: 1}
```

This is a hint for the registry and search — the structural check is still authoritative.

## Extension Dependencies via Protocols

Instead of `depends: [pyrite-task]`, an extension declares:

```yaml
# extension.yaml or pyproject.toml metadata
requires_protocols:
  - claimable/1.0       # I need something claimable in the KB
  - evidence-linked/1.0  # I need evidence-linked entries

provides_protocols:
  - claimable/1.0       # My lead type is claimable
  - source-tracked/1.0  # My document type tracks provenance
```

`pyrite extension install journalism` checks that the target KB has types satisfying the required protocols. It doesn't care *which* extension provides them — any type satisfying `claimable/1.0` works.

This decouples extensions from each other. The journalism plugin doesn't depend on the task plugin. It depends on the `claimable/1.0` protocol. The task plugin satisfies it. So would any other extension that provides claimable types.

## Batteries-Included Core Protocols

Pyrite ships with a set of core protocols covering the 80% case:

| Protocol | Required Fields | Behavior | Use Case |
|----------|----------------|----------|----------|
| `statusable/1.0` | status (select) | Workflow transitions, before_save validation | Any entry with lifecycle states |
| `claimable/1.0` | status, assignee | Atomic claim, exclusive assignment | Agent coordination |
| `evidence-linked/1.0` | evidence (multi-ref), confidence (number) | Source chain validation | Research, investigation, QA |
| `source-tracked/1.0` | sources (list), provenance | Origin tracking | Documents, references, claims |
| `prioritizable/1.0` | priority (select), effort (select) | Triage, ranking | Backlog items, leads, tasks |
| `reviewable/1.0` | status (includes review state), reviewers | Peer review workflow | ADRs, findings, publications |
| `decomposable/1.0` | parent (ref), children (multi-ref) | Parent-child hierarchy, rollup | Tasks, investigations, projects |
| `temporal/1.0` | date (datetime) | Timeline placement, chronological queries | Events, milestones, deadlines |

Extensions don't need to implement these — they're contracts for interoperability. Most domain types will naturally satisfy several protocols just by having the right fields.

## Agent Advantage

The traditional objection to fine-grained protocols is complexity. Humans managing 50 micro-contracts get overwhelmed. Pyrite's approach works because:

1. **Protocols are KB entries** — searchable via `pyrite search`, browsable in the web UI, queryable by agents
2. **The intent layer documents each protocol** — guidelines explain when to use it, evaluation rubrics define compliance
3. **Agents hold more contracts in context** — an agent building an extension can search for all relevant protocols, read their definitions, and implement against them in one session
4. **Structural checking is automatic** — `pyrite protocol check` validates satisfaction without the developer manually tracking contracts
5. **The extension registry is a Pyrite KB** — the protocol definitions, extension metadata, and satisfaction mappings are all structured, typed, searchable entries

This is specification engineering applied to the extension system itself. The protocols are specifications. The KB makes them agent-readable. The checking tools make them verifiable.

## Relationship to Existing Type Hierarchy

The existing `NoteEntry` → `ADREntry` inheritance in Python code continues to work for field inheritance (DRY). Protocols are orthogonal — they define behavioral contracts, not implementation inheritance:

- `ADREntry extends NoteEntry` — inherits id, title, body, tags, links, etc. (implementation reuse)
- `ADREntry satisfies reviewable/1.0` — has status with review states and reviewers field (behavioral contract)

Both coexist. Extension developers use inheritance for implementation and protocols for interoperability.

## Implementation Phases

### Phase 1: Protocol Definition Format (S)

- Define `protocol` as a KB entry type
- Ship core protocols as entries in a `protocols/` directory
- `pyrite protocol list` and `pyrite protocol show <name>`
- No automated checking yet — protocols are documentation

### Phase 2: Structural Satisfaction Checking (M)

- `pyrite protocol check --type <type> --protocol <protocol>`
- Extension manifest `requires_protocols` / `provides_protocols`
- `pyrite extension install` validates protocol requirements
- Protocol satisfaction indexed for search

### Phase 3: Registry Integration (M)

- Extension registry entries include provides/requires protocols
- `pyrite search "extensions providing claimable"` works
- Agent-driven extension discovery via protocol search
- Protocol compatibility matrix in registry UI

## Open Questions

- **Protocol versioning**: semver? Major-only? How do breaking changes propagate?
- **Partial satisfaction**: If a type has 4 of 5 required fields, is that a warning or an error?
- **Protocol composition**: Can protocols extend other protocols? (`claimable/1.0` requires `statusable/1.0`?)
- **Runtime vs static**: Should protocol satisfaction be checked only at install time, or continuously?
- **Batteries-included types vs protocols**: Do we ship reference type implementations (like Python's `list` implementing `Iterable`, `Sized`, `Container`) or just the protocols?

These are all worth discussing but none block the initial design.
