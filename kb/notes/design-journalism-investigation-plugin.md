---
id: design-journalism-investigation-plugin
title: 'Design: Journalism Investigation Plugin'
type: design_doc
tags:
- journalism
- investigation
- plugin
- ftm
- architecture
links:
- target: epic-core-journalism-investigation-plugin
  relation: informs
  kb: pyrite
- target: epic-financial-relationship-tracking
  relation: informs
  kb: pyrite
- target: epic-evidence-and-claims-management
  relation: informs
  kb: pyrite
- target: epic-refactor-cascade-to-extend-journalism-investigation
  relation: informs
  kb: pyrite
- target: epic-investigation-ui-views
  relation: informs
  kb: pyrite
- target: epic-cross-kb-investigation-search
  relation: informs
  kb: pyrite
---

## Overview

A reusable Pyrite plugin for investigative journalism projects. Provides entry types for entities (people, organizations, assets, accounts), events (dated occurrences, transactions, legal actions), connections (ownership, membership, funding as first-class entries), and investigation-specific types (claims, evidence, investigations).

Informed by OCCRP's FollowTheMoney (FtM) data model (~69 schemata for financial crime investigation) but adapted for Pyrite's markdown-first architecture. FtM is JSON-first with entities as database records; Pyrite entries are markdown files where the body carries narrative context — a strength for journalism.

## Strategic Role

The journalism-investigation plugin (like the software-kb plugin) serves two purposes:

1. **Production use** — real investigative journalism projects (kleptocracy timeline, future investigations). These plugins are not demos; they handle real data at scale (4,400+ events, 1,235 actors, complex relationship graphs).
2. **Platform validation** — exercising Pyrite core with demanding real-world patterns. Every plugin gap discovered (template filter bugs, missing CLI commands, backward status transitions, string-or-ref field handling) drives core improvements. The plugins are the proving ground for the platform.

When designing features for this plugin, optimize for the real use case first. If core doesn't support what the plugin needs, file the core issue — don't work around it. The plugin's job is to find those gaps.

## Journalist Workflow

The investigation workflow is **iterative, not linear**. The journalist cycles through phases as new evidence reshapes understanding:

```
    ┌──────────────────────────────────────────────────┐
    │                                                  │
    ▼                                                  │
 Create        Research &        Build the        Verify &
 Investigation  Gather            Pack             Restructure
    │              │                │                │
    │         ┌────┴─────┐    ┌────┴─────┐          │
    │         │ Pyrite KBs│    │ Actor bios│          │
    │         │ Web search│    │ Timeline  │          │
    │         │ Doc search│    │ Connections│         │
    │         │ Panama    │    │ Claims    │          │
    │         │ Papers MCP│    │ Narrative │          │
    │         └────┬─────┘    └────┬─────┘          │
    │              │                │                │
    │              └────────────────┘                │
    │                     ▲                          │
    │                     │   new evidence           │
    │                     │   reshapes the           │
    │                     │   investigation           │
    │                     └──────────────────────────┘
    │
    ▼
 Publish / Export
```

### Key implications of the iterative model

1. **Everything is provisional** — claims change status, timelines get reordered, entities get merged or split, connections get revised. The system cannot assume forward-only progress.
2. **Context must be cheap to rebuild** — when the journalist returns after days away, "where was I?" must be a single query, not 20 minutes of re-reading files.
3. **Narrative restructuring is first-class** — not just adding entries but reorganizing them: re-linking events to different themes, splitting investigations, promoting minor actors to key figures.
4. **Multi-source research is simultaneous** — the journalist searches Pyrite KBs, the web, document collections, and specialized databases (Panama Papers, corporate registries) in the same research session via MCP tools.

### Primary interfaces

- **Web UI** — timeline visualization, network graphs, investigation dashboard, entity profiles, source management. The journalist persona needs visual tools, unlike the software-kb terminal user.
- **Claude Desktop / Cowork** — MCP server is the primary agent interface. The journalist works conversationally: "What do we know about Company X across all our investigations?"
- **CLI** — secondary interface for scripting, batch operations, CI/CD integration.

## Design Principles

1. **Relationships are entries, not just links.** An ownership stake is an entry with its own properties (percentage, dates, legal basis), body text for context, and source citations. This mirrors FtM's edge-entity pattern.
2. **Claims require evidence chains.** Every factual assertion in an investigation should link to source documents with reliability ratings. This is the core value proposition over FtM, which doesn't model claims.
3. **Start small, extend later.** ~15 entry types vs FtM's 69. Cover the investigative narrative layer, not document forensics or shipping tracking.
4. **Cascade becomes a consumer.** The Cascade plugin extends journalism-investigation base types with domain-specific fields (capture lanes, eras, chapters). No code duplication.

## Entry Types

### Entities (nodes)

| Type | Extends | New Fields | Notes |
|------|---------|------------|-------|
| `person` | Core PersonEntry | (none — use as-is) | Already has aliases, nationality, role, affiliations, importance |
| `organization` | Core OrganizationEntry | (none — use as-is) | Already has org_type, jurisdiction, founded, importance |
| `asset` | Entry | asset_type, value, currency, jurisdiction, registered_owner, acquisition_date | Real estate, vehicles, vessels, luxury goods, IP |
| `account` | Entry | account_type, institution, jurisdiction, holder, opened_date, closed_date | Bank accounts, crypto wallets, shell company accounts |
| `document_source` | SourceEntry | reliability, classification, obtained_date, obtained_method | Primary source documents, filings, leaks, FOIA responses |

### Events (temporal nodes)

| Type | Extends | New Fields | Notes |
|------|---------|------------|-------|
| `investigation_event` | EventEntry | actors, sources, importance, verification_status | General dated occurrence in an investigation |
| `transaction` | EventEntry | amount, currency, sender, receiver, method, purpose, transaction_type | Financial flows — the "follow the money" core |
| `legal_action` | EventEntry | case_type, jurisdiction, parties, status, outcome, case_number | Court cases, sanctions, regulatory actions, indictments |

### Connections (edge-entities)

| Type | Extends | Fields | Notes |
|------|---------|--------|-------|
| `ownership` | Entry | owner, asset, percentage, start_date, end_date, legal_basis, beneficial | Who owns what, including beneficial ownership |
| `membership` | Entry | person, organization, role, start_date, end_date, source | Board seats, executive roles, party membership |
| `funding` | Entry | source, recipient, amount, currency, date_range, purpose, mechanism | Grant, donation, contract, dark money |

### Investigation-specific

| Type | Extends | Fields | Notes |
|------|---------|--------|-------|
| `claim` | Entry | assertion, confidence (high/medium/low), status (unverified/corroborated/disputed/retracted), sources | Specific factual assertion with evidence chain |
| `evidence` | Entry | evidence_type, source_document, reliability, obtained_date, chain_of_custody | Links claims to source documents |
| `investigation` | Entry | subject, scope, status, lead_reporter, publication_date, timeline | Top-level investigation entry — groups claims, events, entities |

## Relationship Types

| Forward | Inverse | Purpose |
|---------|---------|---------|
| `member_of` | `has_member` | Person ↔ Organization |
| `owns` | `owned_by` | Ownership stakes |
| `funded_by` | `funds` | Money flows |
| `sourced_from` | `sources` | Claims/events ↔ Source documents |
| `corroborates` | `corroborated_by` | Cross-source verification |
| `contradicts` | `contradicted_by` | Conflicting evidence |
| `investigated_by` | `investigated` | Legal actions ↔ entities |
| `beneficial_owner_of` | `beneficially_owned_by` | Beneficial ownership (distinct from legal ownership) |
| `transacted_with` | `received_transaction_from` | Transaction counterparties |
| `party_to` | `has_party` | Legal action parties |

## KB Preset

`journalism-investigation` preset creates a KB with:
- All 15 entry types registered
- All relationship types
- Subdirectories: `entities/`, `events/`, `connections/`, `claims/`, `sources/`, `investigations/`
- Default validations: source_required (events need sources), claim_needs_evidence, transaction_needs_parties
- QA rules: source URL liveness, duplicate entity detection, orphan claim detection

## MCP Tools

### Read tier
- `investigation_timeline` — query events with date/actor/tag/type filters
- `investigation_entities` — list persons/orgs/assets with importance/role filters
- `investigation_network` — entity connection graph (ownership chains, funding flows, membership overlaps)
- `investigation_sources` — source document queries with reliability filters
- `investigation_claims` — claims with evidence status, confidence, verification state
- `investigation_money_flow` — trace transaction chains between entities

### Write tier
- `investigation_create_entity` — create person/org/asset/account
- `investigation_create_event` — create event/transaction/legal_action
- `investigation_create_claim` — create claim with evidence links
- `investigation_log_source` — log a source document with reliability assessment

## Cascade Refactoring

After the journalism-investigation plugin exists, Cascade refactors to:

```
journalism-investigation (base)
├── person → actor (adds: tier, era, capture_lanes, chapters)
├── organization → cascade_org (adds: capture_lanes, chapters)
├── investigation_event → cascade_event (adds: era, capture_lanes, chapters)
├── investigation_event → timeline_event (adds: capture_lanes, actors, capture_type, connections, patterns)
├── investigation_event → solidarity_event (adds: infrastructure_types, lineage, legacy, capture_response, outcome)
└── (cascade-only) mechanism, scene, victim, statistic, theme
```

Cascade's existing MCP tools (`cascade_actors`, `cascade_timeline`, etc.) continue to work but delegate to the journalism-investigation base implementations where possible.

## FtM Mapping Reference

For future interop or import/export:

| Pyrite Type | FtM Schema(s) |
|-------------|---------------|
| person | Person |
| organization | Company, PublicBody, LegalEntity |
| asset | RealEstate, Vehicle, Vessel, Asset |
| account | BankAccount, CryptoWallet |
| document_source | Document, Pages |
| investigation_event | Event |
| transaction | Payment |
| legal_action | CourtCase, Sanction |
| ownership | Ownership, Interest |
| membership | Membership, Directorship, Employment |
| funding | (Payment pattern) |
