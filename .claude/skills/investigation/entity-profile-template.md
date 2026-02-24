# Entity Profile Template

Use this structure when producing the final profile for an investigated entity. Adapt sections based on entity type — not all sections apply to every entity.

---

## Template

```markdown
---
type: person  # or organization, event, topic
title: "<Entity Name>"
tags: [investigation, <domain-tags>]
importance: <1-10>
---

# <Entity Name>

**Investigation date:** <When this profile was compiled>
**KBs consulted:** <List>
**Profile confidence:** High / Medium / Low (overall)

## Summary

<2-3 sentence overview of who/what this entity is and why they matter. Every factual claim links to a source.>

## Key Facts

| Fact | Source | Confidence |
|------|--------|------------|
| <Role/position> | [[source-entry]] | High/Med/Low |
| <Affiliation> | [[source-entry]] | High/Med/Low |
| <Notable action> | [[source-entry]] | High/Med/Low |

## Timeline

| Date | Event | Source |
|------|-------|--------|
| YYYY-MM-DD | <What happened> | [[entry-id]] |
| YYYY-MM-DD | <What happened> | [[entry-id]] |

## Relationships

| Entity | Relationship | Source | Since |
|--------|-------------|--------|-------|
| [[person-or-org]] | <type: employs/funds/opposes/advises/etc.> | [[source]] | <date or "unknown"> |
| [[person-or-org]] | <type> | [[source]] | |

## Contradictions

- <Source A says X> ([[source-a]]) vs <Source B says Y> ([[source-b]])
  - Assessment: <which is more credible and why>

## Gaps

- <What we don't know but should>
- <Missing time periods>
- <Unverified claims that need corroboration>
- <Related entities not yet investigated>

## Source Summary

| Entry | Tier | Used For |
|-------|------|----------|
| [[entry-id]] | 1 | <what claims it supports> |
| [[entry-id]] | 2 | <what claims it supports> |
| [[entry-id]] | 4 | <flagged as unverified> |
```

---

## Entity Type Variations

### Person

Include: role/title history, organizational affiliations, known associates, public statements, key actions/decisions.

### Organization

Include: leadership, founding date, mission/purpose, funding sources, key members, notable actions, subsidiaries/affiliates.

### Event

Include: date, location, participants, causes, consequences, media coverage, disputed facts.

### Topic

Include: definition, key proponents/opponents, timeline of development, current status, open questions.
