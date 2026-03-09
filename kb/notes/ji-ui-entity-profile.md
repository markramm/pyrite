---
id: ji-ui-entity-profile
title: Entity profile view aggregating all known information
type: backlog_item
tags:
- journalism
- investigation
- web
- frontend
- entities
links:
- target: epic-investigation-ui-views
  relation: subtask_of
  kb: pyrite
kind: feature
status: proposed
priority: medium
effort: M
---

## Problem

When investigating a person or organization, the journalist needs everything known about that entity in one place: biographical details, organizational affiliations, timeline of involvement, financial connections, related claims, and source documents. Currently this requires multiple searches and manual correlation.

## Scope

### Profile Header
- Name, aliases, type (person/org), importance rating
- Photo/logo placeholder
- Key identifiers (jurisdiction, role, affiliations)
- Tags, cross-KB appearances

### Tabs/Sections

**Timeline** — all events involving this entity, chronological
- Events where they appear as actor/participant
- Transactions where they are sender/receiver
- Legal actions where they are a party

**Connections** — network view centered on this entity
- Ownership stakes (what they own, who owns them)
- Memberships (boards, organizations, roles)
- Funding relationships (who they fund, who funds them)
- Embedded mini network graph

**Claims** — claims involving this entity
- Claims where entity is subject
- Claims status breakdown
- Evidence coverage per claim

**Sources** — source documents mentioning this entity
- Sorted by reliability tier
- URL status indicators
- Source coverage assessment

**Cross-KB** — appearances in other KBs
- Same entity in prior investigations
- Shared reference KB entries
- Suggested merges (fuzzy name matching)

### Edit Mode
- Inline editing of entity fields
- Quick-add: connection, event, claim from the profile view
- Merge: combine duplicate entities with backlink preservation

## Acceptance Criteria

- Profile aggregates all linked entries (events, connections, claims, sources)
- Cross-KB search finds the same entity in other KBs
- Inline editing saves via API without page reload
- Mini network graph renders the entity's immediate connections
