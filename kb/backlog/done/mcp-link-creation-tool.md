---
id: mcp-link-creation-tool
title: MCP Link Creation Tool
type: backlog_item
tags:
- feature
- mcp
kind: feature
status: completed
priority: medium
effort: M
---

## Problem

Backlinks and network queries exist for reading the link graph, but there's no MCP tool to create or manage links between entries. Agents discovering connections during research have no way to persist them without editing raw markdown frontmatter.

## Proposed Solution

Add a \`kb_link\` write-tier MCP tool:

\`\`\`
kb_link:
  source_id: str        # Source entry ID
  target_id: str        # Target entry ID  
  kb_name: str          # KB name
  relation: str         # Relationship type (related_to, influences, caused_by, etc.)
  note: str (optional)  # Description of the relationship
  bidirectional: bool   # Create inverse link too (default: false)
\`\`\`

Also consider \`kb_unlink\` for removing relationships.

## Context

This is especially important for the longform writing use case where tracing connections across actors/events/themes is the core activity. Currently the link graph is populated only during indexing from frontmatter \`links:\` arrays — there's no runtime API for graph enrichment.

## Related

- kb_backlinks handler (read-side already exists)
- Link model in pyrite/schema.py
- pyrite/storage/queries.py graph queries
