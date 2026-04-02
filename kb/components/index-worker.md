---
id: index-worker
title: Index Worker
type: component
tags:
- core
- indexing
kind: service
path: pyrite/services/index_worker.py
owner: markr
dependencies: '["index_manager"]'
---

Background index worker with SQLite-backed job tracking. Manages async index sync and rebuild jobs using threads. Follows the same pattern as EmbeddingWorker but tracks per-KB bulk operations rather than per-entry queue items. Provides job submission, status polling, and completion callbacks.
