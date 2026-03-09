---
id: epic-software-kb-quality-gates-and-rubric-automation
title: 'Epic: Software KB Quality Gates and Rubric Automation'
type: backlog_item
tags:
- epic
- software-kb
kind: epic
priority: high
effort: XL
---

Follow-up epic to the kanban flow work. Adds structured quality enforcement to the software KB workflow.

## Scope

1. **Named Rubric Checkers** — Explicit binding between rubric items and validation functions so reviews can be partially automated *(done)*
2. **Migrate All Rubric Items to Named Checkers** — Convert all demo/pyrite KB rubric items to named format, add migration tooling, remove legacy regex path *(done)*
3. **Definition of Ready / Definition of Done** — Gate transitions (e.g. accepted→in_progress, review→done) with configurable checklists *(done)*
4. ~~**Policy Rubric Checkers**~~ — Moved out of scope; see `policy-rubric-checkers` backlog item
5. **Enhance orient for software-type KBs** — Surface kanban board state, architecture context (ADRs, components), and active work items in the orient command *(done)*
6. **Update software-kb skill for gates** — Teach agents to interpret and act on DoR/DoD gate results; see `update-software-kb-skill-for-gates`
7. **Backlog refinement workflow** — Proactive DoR checking and grooming without claiming; see `backlog-refinement-workflow`

## Success Criteria

- `sw_transition` can enforce DoR/DoD checklists before allowing transitions
- Named rubric checkers run automatically during `sw_review`
- `pyrite orient -k <software-kb>` shows board summary, active items, and relevant ADRs
- Agents interpret gate results and address DoR/DoD gaps in their workflow
- Backlog items can be checked for readiness without claiming them
