---
id: ji-auto-generate-bidirectional-links-from-connection-entries
title: 'JI: Auto-generate bidirectional links from connection entries'
type: backlog_item
tags:
- ji
- connections
- graph
kind: feature
status: done
priority: high
assignee: claude
effort: M
---

## Problem

Connection entry types (ownership, membership, funding) exist as data but do not auto-generate bidirectional links in the index. An OwnershipEntry with `owner: [[john-doe]]` and `asset: [[shell-corp]]` should automatically create owns/owned_by links between those entities, but currently these links only exist if manually added to the frontmatter links field.

## Scope

Add a post-save hook or validator-stage enrichment that:

1. Reads connection entries (ownership, membership, funding) after creation/update
2. Extracts the entity wikilinks from their fields (owner/asset, person/organization, funder/recipient)
3. Auto-generates the corresponding relationship links (owns/owned_by, member_of/has_member, funds/funded_by)
4. Stores these as indexed links so they appear in `pyrite backlinks` and `investigation_network` queries

### Design Options

- **Option A**: Plugin validator adds links to the entry frontmatter before save (simple, no core changes)
- **Option B**: Post-index hook adds link rows to the DB (requires hook infrastructure)
- **Option C**: Graph service resolves connection types at query time (no stored links, computed on read)

Option A is simplest and works today.

## Acceptance Criteria

- Creating an ownership entry auto-generates owns/owned_by backlinks
- Creating a membership entry auto-generates member_of/has_member backlinks
- Creating a funding entry auto-generates funds/funded_by backlinks
- `pyrite backlinks <entity-id>` shows connections linking to that entity
- `investigation_network` MCP tool traverses connection links
