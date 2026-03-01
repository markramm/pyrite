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

SQLite-backed embed_queue with EmbeddingWorker. Processes embedding requests asynchronously with retry and batching. Triggered by KBService._auto_embed() after entry creation/update. Status available via GET /api/index/embed-status.
