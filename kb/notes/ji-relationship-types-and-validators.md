---
id: ji-relationship-types-and-validators
title: 'Journalism-investigation: relationship types and validators'
type: backlog_item
tags:
- journalism
- investigation
- plugin
- validation
links:
- target: epic-core-journalism-investigation-plugin
  relation: subtask_of
  kb: pyrite
- target: ji-entity-entry-types
  relation: depends_on
  kb: pyrite
- target: ji-event-entry-types
  relation: depends_on
  kb: pyrite
- target: ji-connection-entry-types
  relation: depends_on
  kb: pyrite
kind: feature
status: proposed
priority: medium
effort: S
---

## Problem

The journalism-investigation plugin needs its own relationship types (10 pairs) registered with Pyrite's relationship registry, and field validators for each entry type.

## Scope

### Relationship Types (10 bidirectional pairs)

| Forward | Inverse |
|---------|---------|
| `member_of` | `has_member` |
| `owns` | `owned_by` |
| `funded_by` | `funds` |
| `sourced_from` | `sources` |
| `corroborates` | `corroborated_by` |
| `contradicts` | `contradicted_by` |
| `investigated_by` | `investigated` |
| `beneficial_owner_of` | `beneficially_owned_by` |
| `transacted_with` | `received_transaction_from` |
| `party_to` | `has_party` |

Note: `member_of`/`has_member` and `funded_by`/`funds` overlap with Cascade's existing types. Need to handle gracefully (shared definition or plugin precedence).

### Validators

- `investigation_event`: requires `date`, `title`; warns if no `sources`
- `transaction`: requires `date`, `title`, `sender`, `receiver`; warns if no `amount`
- `legal_action`: requires `date`, `title`, `case_type`, `jurisdiction`
- `asset`: requires `title`, `asset_type`
- `account`: requires `title`, `account_type`
- `document_source`: requires `title`, `reliability`
- `ownership`: requires `owner`, `asset`
- `membership`: requires `person`, `organization`
- `funding`: requires `source`, `recipient`
- `claim`: requires `title`, `status`; warns if no evidence links
- `evidence`: requires `title`, `source_document`

## Acceptance Criteria

- All 10 relationship pairs registered and bidirectional
- Validators run on save, produce clear error messages
- No conflicts with Cascade relationship types (shared or namespaced)
- `pyrite qa validate` catches missing required fields
