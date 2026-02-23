---
type: backlog_item
title: "Expose Semantic Search to Plugin MCP Tools"
kind: improvement
status: proposed
priority: medium
effort: S
tags: [search, plugins, mcp]
---

Plugin MCP tools currently query via raw SQL on the entry table. They could benefit from using the semantic search (vector embeddings) already available in the index. Need to expose the EmbeddingService or a search helper in the plugin tool handler context.
