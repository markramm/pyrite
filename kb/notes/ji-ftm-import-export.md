---
id: ji-ftm-import-export
title: FollowTheMoney (FtM) import/export for Aleph interop
type: backlog_item
tags:
- journalism
- investigation
- ftm
- occrp
- interop
links:
- target: epic-financial-relationship-tracking
  relation: subtask_of
  kb: pyrite
kind: feature
status: proposed
priority: low
effort: L
---

## Problem

OCCRP's Aleph platform uses the FollowTheMoney (FtM) JSON format. Investigative journalists using both Pyrite and Aleph need to move data between them. FtM entities are JSON objects with `{id, schema, properties}` structure. Pyrite entries are markdown files with YAML frontmatter.

## Scope

### Import
- `pyrite investigation import-ftm --file=entities.json --kb=<kb>` reads FtM JSON and creates Pyrite entries
- Map FtM schemata to journalism-investigation types (Person→person, Company→organization, Payment→transaction, etc.)
- Handle FtM's multi-valued string properties → Pyrite single-value fields (take first or concatenate)
- Preserve FtM entity IDs as aliases for deduplication
- Dry-run mode to preview mappings

### Export
- `pyrite investigation export-ftm --kb=<kb> --output=entities.json` produces FtM JSON
- Map journalism-investigation types back to FtM schemata
- Validate output against FtM schema
- Suitable for Aleph bulk import

### Mapping Table

| Pyrite Type | FtM Schema |
|-------------|------------|
| person | Person |
| organization | Company / PublicBody |
| asset | RealEstate / Vehicle / Vessel / Asset |
| account | BankAccount / CryptoWallet |
| transaction | Payment |
| legal_action | CourtCase / Sanction |
| ownership | Ownership |
| membership | Membership / Directorship |

## Acceptance Criteria

- Round-trip: export from Pyrite → import to fresh KB produces equivalent entries
- FtM JSON output validates against FtM schema
- Import handles 10,000+ FtM entities without memory issues
- Unmappable FtM types logged with warnings, not silently dropped

## Open Questions

- Should we depend on the `followthemoney` Python package for validation, or keep it standalone?
- How to handle FtM types we don't have equivalents for (e.g., Vessel, Airplane)?
