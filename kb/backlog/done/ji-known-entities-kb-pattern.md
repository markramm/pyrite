---
id: ji-known-entities-kb-pattern
title: Known entities reference KB pattern
type: backlog_item
tags:
- journalism
- investigation
- entities
- cross-kb
- reference
links:
- target: epic-cross-kb-investigation-search
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
assignee: claude
effort: S
---

## Problem

Across multiple investigations, certain entities (major political figures, government agencies, multinational corporations) appear repeatedly. Each investigation independently creates entries for them. A shared "known entities" reference KB would provide a canonical baseline that investigation KBs can link to, avoiding redundant research and ensuring consistency.

## Scope

- Document and support the "known entities" KB pattern
- Init template: `pyrite init --template known-entities` creates a reference KB with person/organization types
- Convention: investigation KBs link to known-entities KB entries via `same_as` or `references` relation
- Auto-suggest: when creating an entity in an investigation KB, check known-entities KB for existing entry
- Shared entity enrichment: improvements to a known-entities entry benefit all linked investigations
- Read-only from investigation perspective (link to it, don't modify it)

## Acceptance Criteria

- `pyrite init --template known-entities` creates appropriate KB
- Creating an entity in investigation KB triggers known-entities lookup
- Match suggestions shown with confidence (accept creates cross-KB link)
- Known-entities KB can be shared across multiple investigation KBs
