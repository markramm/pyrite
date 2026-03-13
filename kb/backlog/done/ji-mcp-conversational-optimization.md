---
id: ji-mcp-conversational-optimization
title: MCP tool optimization for conversational journalist workflows
type: backlog_item
tags:
- journalism
- investigation
- mcp
- ux
links:
- target: epic-core-journalism-investigation-plugin
  relation: depends_on
  kb: pyrite
kind: improvement
status: done
assignee: claude
effort: S
---

## Problem

The journalist's primary agent interface is Claude Desktop/Cowork via MCP. Tool descriptions, parameter names, and output formats need to be optimized for conversational use — not just programmatic correctness.

## Scope

### Tool Descriptions
- Write tool descriptions as capabilities: "Search for events involving a person or organization" not "Query investigation_event entries by actor field"
- Include example invocations in descriptions
- Group related tools logically for tool-use selection

### Output Formatting
- Structured but human-readable (not raw JSON dumps)
- Include natural language summaries alongside structured data
- Truncate long results with "showing 10 of 247 — use limit parameter for more"
- Include action suggestions: "3 claims are unverified — use investigation_claims to review them"

### Contextual Defaults
- `kb_name` defaults to the most recently used investigation KB
- Date ranges default to investigation's active period
- Importance thresholds default based on investigation size

### Session Continuity
- MCP tools should support a "continue" pattern: "Show me more results" or "Now filter by actor X"
- Investigation context persists across tool calls within a session

## Acceptance Criteria

- Tool descriptions are conversational and include examples
- Output includes natural language summaries
- Defaults reduce parameter verbosity for common operations
- Journalist can work fluidly via Claude Desktop without knowing internal field names
