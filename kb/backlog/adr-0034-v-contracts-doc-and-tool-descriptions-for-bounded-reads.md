---
id: adr-0034-v-contracts-doc-and-tool-descriptions-for-bounded-reads
title: 'ADR-0034 (v): docs/json-contracts.md, tool descriptions and agent-facing setup for bounded reads'
type: backlog_item
tags:
- mcp
- agent-ux
- bounded-reads
- adr-0034
- blocked
importance: 5
kind: improvement
status: proposed
priority: medium
effort: S
rank: 0
---

**BLOCKED — not dispatchable. ADR-0034 ("Agent-facing reads are bounded by default", PR #170) is `proposed`, not accepted.** The numbers in rule 4 are the maintainer's to set. Re-read the ADR as accepted before dispatching: if a number, a variable name or the CLI default changed, this item changes with it.

## Problem

The `body_*` marker keys and `has_more` are a contract three surfaces share and no document states. ADR-0034 rule 7: "The `body_*` keys and the `has_more` flag join `docs/json-contracts.md`; tool descriptions state the default and the ceiling in numbers." Rule 5: "Agent-facing setup (the MCP/CLI docs, `CLAUDE.md` templates, the skills) sets [`PYRITE_BODY_LIMIT`]; scripts and terminals do not."

## Acceptance

1. `docs/json-contracts.md` gains a "Bounded reads" section: the four marker keys, `has_more`, their meaning per surface (MCP default-bounded, CLI opt-in, REST opt-in), the continuation call for each, and the rule that a marked body is refused on write.
2. `docs/configuration.md` lists the four variables with defaults and the fail-at-start rule.
3. Agent-facing setup sets `PYRITE_BODY_LIMIT`: the MCP integration docs (`docs/gemini-mcp-integration.md`, `docs/openai-mcp-integration.md`), the `CLAUDE.md` template `pyrite init` writes (if one exists), and this repo's `CLAUDE.md` "Using the KB" section.
4. A test in `tests/test_docs_facts.py` (or beside it) asserts the numbers quoted in the docs equal the defaults in `pyrite/services/body_bounds.py`, and that every marker key named in the doc is one the code emits.

## Groom 2026-09-18 (serial)

**Regimes:** docs-only plus one facts test — the regime is drift: the test must fail when a default changes in code and the doc does not.

**Touches** — existing: `docs/json-contracts.md`, `docs/configuration.md`, the two MCP integration docs, `CLAUDE.md`, `pyrite/server/tool_schemas.py` only if (i) left a description without numbers. New: the facts test (or a section of `tests/test_docs_facts.py` if the docs-facts theme has landed).

**Sequence:** last of the five — after (i)–(iv), so it documents what shipped, and after the docs-facts theme if that created `tests/test_docs_facts.py`.

**Model:** sonnet. **heavy:** no. **Cold read:** no. **Size:** S, ~150 lines of prose + ~40 of test.

**Out of scope:** any behaviour change; the README.
