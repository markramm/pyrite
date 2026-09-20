---
id: background-embedding-worker
title: Background Embedding Worker
type: component
kind: service
path: pyrite/services/embedding_worker.py
owner: core
tags:
- core
- service
- ai
---

SQLite-backed embed_queue plus EmbeddingWorker. Despite the name it is a **queue, not a thread**: constructing one is a CREATE TABLE IF NOT EXISTS (~50 ms cold, zero threads spawned, no torch imported), and process_batch()/drain() are plain synchronous methods a caller must invoke.

Under ADR-0035 every write with auto_embed: true goes through KBService._auto_embed, which builds a worker lazily and enqueues one pending row; a write never loads the embedding model. That is what makes a fresh install usable (#13) -- the entry is keyword-searchable immediately and the embedding is owed, not skipped.

Drain points, all of them callers who already had somebody willing to wait (no new background thread, deliberately -- see #102): pyrite-server's prewarm_embeddings startup hook (after the model is warm), POST /api/index/sync?wait=true, and pyrite index embed / sync / build. clear_embedded() retires rows that EmbeddingService.embed_all already satisfied from the index side, so GET /api/index/embed-status can reach zero.
