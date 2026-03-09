---
id: ji-connection-entry-types
title: 'Journalism-investigation: connection entry types (ownership, membership, funding)'
type: backlog_item
tags:
- journalism
- investigation
- plugin
- entry-types
- ftm
links:
- target: epic-core-journalism-investigation-plugin
  relation: subtask_of
  kb: pyrite
- target: design-journalism-investigation-plugin
  relation: informed_by
  kb: pyrite
- target: ji-entity-entry-types
  relation: depends_on
  kb: pyrite
kind: feature
status: accepted
priority: high
effort: M
---

## Problem

In investigative journalism, relationships between entities carry their own data — an ownership stake has a percentage, dates, and legal basis. A board membership has a role and term. These can't be represented as simple `links` in YAML frontmatter. Following FtM's edge-entity pattern, connections should be first-class entries.

## Scope

Create 3 connection entry types. Each is an entry that represents a relationship between two entities, with its own properties and body text for narrative context.

### `ownership` (OwnershipEntry)
- Fields: `owner` (wikilink to person/org), `asset` (wikilink to asset/org/account), `percentage`, `start_date`, `end_date`, `legal_basis`, `beneficial` (bool — is this beneficial ownership vs legal?)
- Auto-generates links: `owner → owns → asset`, `asset → owned_by → owner`
- Body: narrative context, sourcing, significance

### `membership` (MembershipEntry)
- Fields: `person` (wikilink), `organization` (wikilink), `role`, `start_date`, `end_date`, `source`
- Auto-generates links: `person → member_of → org`, `org → has_member → person`
- Body: narrative context

### `funding` (FundingEntry)
- Fields: `source` (wikilink to person/org), `recipient` (wikilink to person/org), `amount`, `currency`, `date_range`, `purpose`, `mechanism` (grant, donation, contract, lobbying, dark_money, other)
- Auto-generates links: `source → funds → recipient`, `recipient → funded_by → source`
- Body: narrative context, sourcing

## Design Note

Connection entries live in `connections/` subdirectory. They automatically maintain bidirectional links between the entities they connect. When indexed, the graph service should traverse these to build network views.

## Acceptance Criteria

- All 3 types round-trip correctly with all fields
- Auto-generated links appear in backlinks for both connected entities
- `pyrite backlinks <entity-id>` shows connections linking to that entity
- Connection entries are traversable via graph service
- Subdirectory: `connections/`
- Validators: owner and asset required for ownership, person and organization required for membership, source and recipient required for funding
