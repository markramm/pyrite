---
id: ji-event-entry-types
title: 'Journalism-investigation: event entry types (investigation_event, transaction, legal_action)'
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

Investigative journalism tracks multiple types of dated occurrences: general events, financial transactions ("follow the money"), and legal/regulatory actions. Each has distinct fields beyond a generic event.

## Scope

Create 3 new entry types:

### `investigation_event` (InvestigationEventEntry)
- Extends: EventEntry
- Fields: `actors` (list of strings or wikilinks), `sources` (list), `importance` (1-10), `verification_status` (unverified, partially_verified, verified, disputed)
- Inherits: date, location, participants, notes, status

### `transaction` (TransactionEntry)
- Extends: EventEntry
- Fields: `amount`, `currency`, `sender` (string or wikilink), `receiver` (string or wikilink), `method` (wire, cash, crypto, check, other), `purpose`, `transaction_type` (payment, grant, donation, loan, investment, bribe, kickback, other)
- Inherits: date, location, notes, status, importance

### `legal_action` (LegalActionEntry)
- Extends: EventEntry
- Fields: `case_type` (criminal, civil, regulatory, sanctions, indictment, subpoena, other), `jurisdiction`, `parties` (list), `status` (filed, pending, settled, dismissed, convicted, acquitted), `outcome`, `case_number`
- Inherits: date, location, notes, importance

## Acceptance Criteria

- All 3 types registered in plugin, round-trip correctly
- Transaction validates: amount required if transaction_type is payment/bribe/kickback, sender and receiver required
- Legal action validates: case_type and jurisdiction required
- Subdirectory: `events/` for all 3 types
- MCP timeline tool can query all 3 types with date range filters
