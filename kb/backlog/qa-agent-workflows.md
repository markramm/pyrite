---
id: qa-agent-workflows
title: QA Agent Workflows
type: backlog_item
tags:
- feature
- ai
- quality
kind: feature
priority: medium
effort: XL
status: proposed
---

## Problem

Knowledge base quality currently depends entirely on human review at commit time. There is no continuous, automated quality assurance across the corpus. Entries can have missing fields, inconsistent importance scores, unsupported claims, stale cross-references, and style drift — none of which are caught after initial creation.

## Solution

A multi-tier QA agent system that evaluates KB entries against type-level criteria, KB-level editorial guidelines, and factual accuracy standards. QA results are themselves KB entries (type: `qa_assessment`), making quality a queryable, trackable property of the knowledge base.

## Design

### Three evaluation tiers

**Tier 1: Structural validation (fully automatable, no LLM)**

Deterministic checks that run on every save or as a batch sweep:

- Required fields present per entry type (date on events, target/source on relationships)
- Date formats parseable
- Importance scores within valid range (1-10)
- Capture lanes from controlled vocabulary (if KB has `kb.yaml` with vocabulary)
- Tags exist and aren't orphaned
- Wikilink targets resolve to existing entries
- Sources have URLs or citations
- No empty bodies on non-stub entries

Implementation: Pure Python validation functions, no LLM needed. Can run as a post-save hook or CLI batch command.

**Tier 2: Consistency and appropriateness (LLM-assisted, high confidence)**

AI-judged checks that flag issues for human review:

- Body text supports the title's claim
- Importance score consistent with comparable entries in the KB
- Tags and capture lanes appropriate for the content
- Entry contextualizes rather than merely records (for investigative KBs)
- Relationships are bidirectional where expected
- Summaries accurately reflect body content
- No duplicate or near-duplicate entries (semantic similarity check)

Implementation: LLM evaluation against type-level AI instructions (already in CORE_TYPE_METADATA) plus KB-level guidelines. Produces confidence-scored assessments.

**Tier 3: Factual verification (LLM + research, lower confidence)**

Deep verification requiring external research:

- Specific claims match cited sources
- Dates are historically accurate
- Quotes are correctly attributed
- Causal claims are defensible
- Statistics and figures are verifiable
- Cross-reference against existing KB for contradictions

Implementation: Research agent with web search capability, source document retrieval, and cross-KB consistency checking. Produces confidence-scored assessments with source chains.

### QA assessment entries

Each QA run produces entries of type `qa_assessment`:

```yaml
---
id: qa-{entry-id}-{timestamp}
type: qa_assessment
title: "QA: {entry title}"
tags: [qa, tier-{1|2|3}]
target_entry: {entry-id}
tier: 1|2|3
status: pass|warn|fail
issues_found: 3
issues_resolved: 1
last_assessed: 2026-02-28
---

## Assessment Summary

Overall: WARN (2 open issues)

## Issues

### 1. Missing source citation (tier-1, FAIL)
Body claims "$25,000 donation" but no source is linked.
**Confidence:** 1.0

### 2. Importance score inconsistency (tier-2, WARN)
Importance 8 but comparable events scored 5-6.
**Confidence:** 0.85

### 3. Date verified (tier-3, PASS)
"March 2024" confirmed via source URL.
**Confidence:** 0.92
```

### KB-level editorial guidelines

New optional section in `kb.yaml`:

```yaml
editorial_guidelines:
  tone: analytical
  framework: "collective punishment and institutional lineage"
  sourcing: "every factual claim must link to a source entry or URL"
  style_notes:
    - "contextualize events within broader patterns, don't just record"
    - "name specific actors and mechanisms, avoid vague systemic claims"
    - "trace institutional lineage rather than treating events as isolated"
```

These guidelines are passed to Tier 2/3 evaluations alongside type-level AI instructions.

## Phases

### Phase 1: Tier 1 structural validation (effort: M)

- `QAService` with `validate_entry()` and `validate_all()` methods
- Validation rules per entry type (derived from schema + type metadata)
- CLI: `pyrite qa validate [--kb <name>] [--entry <id>] [--fix]`
- MCP: `kb_qa_validate` read-tier tool
- Output: structured issue list, no LLM needed

### Phase 2: QA assessment entry type + storage (effort: M)

- `qa_assessment` entry type with schema
- Link assessments to target entries
- Query interface: "show all entries with open issues", "unassessed entries", "verification rate by capture lane"
- CLI: `pyrite qa status [--kb <name>]` — dashboard of assessment state
- MCP: `kb_qa_status` read-tier tool

### Phase 3: Tier 2 LLM-assisted consistency checks (effort: L)

- LLM evaluation prompts using type AI instructions + KB editorial guidelines
- Consistency scoring against comparable entries (semantic similarity to find comparables)
- Confidence-scored assessments
- CLI: `pyrite qa assess [--kb <name>] [--entry <id>] [--tier 2]`
- MCP: `kb_qa_assess` write-tier tool (creates assessment entries)

### Phase 4: Tier 3 factual verification (effort: XL)

- Research agent with web search for claim verification
- Cross-KB contradiction detection
- Source chain verification (do cited sources actually support the claims?)
- Confidence-scored factual assessments
- CLI: `pyrite qa verify [--kb <name>] [--entry <id>]`

### Phase 5: Continuous QA pipeline (effort: L) — partially done

- ~~Post-save hook triggers Tier 1 validation automatically~~ **Done**: `validate` param on `kb_create`/`kb_update` MCP tools + `qa_on_write: true` KB-level setting in `kb.yaml`. Issues returned as `qa_issues` in MCP response.
- Scheduled batch runs for Tier 2/3 (configurable frequency)
- QA dashboard in web UI: verification rates, issue trends, coverage gaps
- "Entries needing review" collection (virtual collection with QA-based query)

## Plugin architecture

The QA system should be domain-agnostic at core:

- Core: field validation, type consistency, dedup detection, link integrity
- Plugin config: domain-specific evaluation rubrics
  - Legal KB: citation accuracy, procedural correctness
  - Scientific KB: methodology descriptions, statistical claims
  - Investigative KB: sourcing standards, analytical framework consistency

This means the QA service accepts pluggable evaluation criteria, and plugins can register custom Tier 2/3 checks via the plugin protocol.

## Dependencies

- Tier 1: No dependencies (pure validation against existing schema)
- Tier 2: Depends on LLM abstraction service (#6, done) and type metadata (#42, done)
- Tier 3: Depends on Tier 2 + web search capability
- Phase 5: Depends on hooks system (#24, done) and collections (#61, done)
- KB editorial guidelines: Depends on capture lane validation (#72)

## Files likely affected

- New: `pyrite/services/qa_service.py`
- New: `pyrite/models/qa_types.py` (or extension entry type)
- Modified: `pyrite/server/mcp_server.py` (new QA tools)
- Modified: `pyrite/cli/__init__.py` (new `qa` command group)
- New: `pyrite/server/endpoints/qa.py`
- Modified: `pyrite/config.py` (editorial_guidelines in KBConfig)
- New: `tests/test_qa_service.py`
