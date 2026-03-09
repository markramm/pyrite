---
id: task-service
title: Task Service
type: component
tags:
- core
- coordination
kind: service
path: pyrite/services/task_service.py
owner: markr
dependencies: '["kb_service"]'
---

Operative task service wrapping KBService for the coordination-task extension. Provides task-specific atomic operations: claim (CAS), decompose, checkpoint, and rollup. Handles task lifecycle beyond basic CRUD — dependency-aware claiming, hierarchical decomposition into subtasks, and progress aggregation.
