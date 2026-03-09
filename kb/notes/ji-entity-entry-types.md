---
id: ji-entity-entry-types
title: 'Journalism-investigation: entity entry types (asset, account, document_source)'
type: backlog_item
tags:
- journalism
- investigation
- plugin
- entry-types
links:
- target: epic-core-journalism-investigation-plugin
  relation: subtask_of
  kb: pyrite
- target: design-journalism-investigation-plugin
  relation: informed_by
  kb: pyrite
kind: feature
status: accepted
priority: high
effort: M
---

## Problem

The journalism-investigation plugin needs entity entry types beyond what Pyrite core provides (person, organization). Investigative journalism tracks assets, financial accounts, and source documents as first-class entities.

## Scope

Create 3 new entry types in the plugin:

### `asset` (AssetEntry)
- Extends: Entry
- Fields: `asset_type` (real_estate, vehicle, vessel, aircraft, luxury_good, intellectual_property, other), `value`, `currency`, `jurisdiction`, `registered_owner`, `acquisition_date`, `description`
- Importance field inherited

### `account` (AccountEntry)
- Extends: Entry
- Fields: `account_type` (bank, brokerage, crypto_wallet, shell_company, trust, other), `institution`, `jurisdiction`, `holder`, `opened_date`, `closed_date`
- Importance field inherited

### `document_source` (DocumentSourceEntry)
- Extends: SourceEntry
- Fields: `reliability` (high, medium, low, unknown), `classification` (public, leaked, foia, court_filing, financial_disclosure, corporate_registry, other), `obtained_date`, `obtained_method`

Person and organization are reused from Pyrite core — no new types needed.

## Acceptance Criteria

- All 3 types registered in ENTRY_TYPE_REGISTRY via plugin
- Round-trip: create → save → load preserves all fields
- Validators enforce required fields (asset_type, account_type, reliability)
- Types show in `pyrite sw components` when plugin is installed
- Subdirectory: `entities/` for all 3 types
