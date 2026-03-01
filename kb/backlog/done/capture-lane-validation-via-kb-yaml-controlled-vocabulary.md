---
id: capture-lane-validation-via-kb-yaml-controlled-vocabulary
title: Capture Lane Validation via kb.yaml Controlled Vocabulary
type: backlog_item
tags:
- feature
- cascade
- schema
kind: feature
status: completed
priority: medium
effort: M
---

## Problem

Capture lane values are free-text strings with no validation. This leads to inconsistency (kebab-case vs Title Case, typos, synonyms) that breaks filtering and aggregation.

## Proposed Solution

Define capture lanes as a controlled vocabulary in \`kb.yaml\`:

\`\`\`yaml
types:
  timeline_event:
    fields:
      capture_lane:
        type: enum
        values:
          - immigration-enforcement
          - executive-power
          - judicial-independence
          - press-freedom
          # ...
        description: "Primary thematic lane for this event"
\`\`\`

Then enforce at write time:
1. Schema validation in \`KBSchema.validate_entry()\` checks enum membership
2. \`kb_create\` / \`kb_update\` MCP handlers reject invalid lanes
3. CLI \`pyrite create\` validates before saving

## Considerations

- Migration path for existing entries with non-canonical lane names
- Whether to allow multi-lane assignment (array of enums)
- Whether validation should warn vs error for unknown lanes
