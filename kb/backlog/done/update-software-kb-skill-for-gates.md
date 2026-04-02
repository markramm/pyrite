---
id: update-software-kb-skill-for-gates
title: "Update software-kb skill to surface DoR/DoD gate results"
type: backlog_item
tags:
- software-kb
- skill
- workflow
- agents
kind: enhancement
priority: high
effort: M
status: done
links:
- target: adr-0021
  relation: implements
- target: definition-of-ready-done
  relation: related
---

## Problem

The `software-kb` skill guides agents through the kanban workflow (claim, work, submit, review). Now that `sw_claim` and `sw_transition` return gate results (DoR/DoD criteria), the skill needs to teach agents how to interpret and act on them.

Currently agents won't know to:
- Check gate results after claiming an item
- Fill DoR gaps (add acceptance criteria, link to ADR, estimate effort) before starting work
- Verify DoD items (tests passing, KB docs updated) before transitioning to done

## Scope

- Update the `software-kb` skill prompt to explain gate results in `sw_claim` / `sw_transition` responses
- Add guidance for handling `judgment` criteria (self-evaluate) vs `checker` failures (fix before proceeding if enforce policy)
- Add guidance for the `warn` vs `enforce` policy distinction
- Include example gate response in the skill so agents know the shape of the data
- Document the DoR self-check loop: claim → read gate → fill gaps → proceed

## Acceptance Criteria

- Agent following the skill correctly interprets gate results after `sw_claim`
- Agent addresses judgment items proactively (e.g., adds ## Acceptance Criteria section)
- Agent does not get stuck on warn-policy failures
