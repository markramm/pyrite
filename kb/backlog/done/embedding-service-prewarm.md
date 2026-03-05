---
id: embedding-service-prewarm
type: backlog_item
title: "Add embedding service pre-warm option to reduce cold-start latency"
kind: improvement
status: completed
milestone: "0.17"
priority: medium
effort: S
tags: [ai, search, performance]
links:
- embedding-service
- background-embedding-pipeline
---

# Add embedding service pre-warm option to reduce cold-start latency

## Problem

The embedding service is lazily initialized — the first semantic search request triggers model loading (1-5s depending on model size). This creates a noticeable delay for the first user/agent query after server startup.

## Solution

1. Add `PYRITE_PREWARM_EMBEDDINGS=true` environment variable
2. On server startup (FastAPI `lifespan`), optionally initialize the embedding service and load the model
3. Add a `/health` endpoint field indicating embedding readiness
4. Keep lazy loading as default for CLI and lightweight deployments

## Files

- `pyrite/services/embedding_service.py` — initialization logic
- `pyrite/server/api.py` — lifespan event for pre-warm
- `pyrite/config.py` — new config option
