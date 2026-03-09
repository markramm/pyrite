---
id: ji-kb-preset-and-init-template
title: 'Journalism-investigation: KB preset and init template'
type: backlog_item
tags:
- journalism
- investigation
- plugin
- templates
- cli
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

Users need a one-command way to create a journalism-investigation KB with all types, relationships, and directory structure configured.

## Scope

- Add `journalism-investigation` to `BUILTIN_TEMPLATES` in `pyrite/cli/init_command.py`
- Create a preset that registers all 15 entry types with subdirectory routing
- Configure default validations and QA rules
- Include a README with usage guidance

### Directory Structure

```
<kb-name>/
├── entities/          # person, organization, asset, account, document_source
├── events/            # investigation_event, transaction, legal_action
├── connections/       # ownership, membership, funding
├── claims/            # claim, evidence
├── sources/           # document_source (alias for entities/)
├── investigations/    # investigation
└── kb.yaml
```

### kb.yaml Configuration

- All 15 types with fields, subdirectories, and validators
- 10 relationship type pairs
- QA rules: source_required, claim_needs_evidence, transaction_needs_parties
- WIP limits for investigation workflow

## Acceptance Criteria

- `pyrite init --template journalism-investigation` creates a fully configured KB
- `pyrite init --list-templates` shows the new template
- All entry types are discoverable after init
- QA validates correctly out of the box
