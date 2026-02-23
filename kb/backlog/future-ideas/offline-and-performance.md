---
type: backlog_item
title: "Offline Support and Large-KB Performance"
kind: feature
status: proposed
priority: medium
effort: L
tags: [web, performance, phase-5]
---

Offline resilience and performance for large KBs (5000+ entries):

**Offline:**
- IndexedDB cache for offline reads (entries, KBs, search index)
- Save queue for offline writes — sync when connection restored
- Service worker for asset caching
- Visual indicator for offline/online status

**Performance:**
- Virtual scrolling for entry lists (handle 5000+ entries without DOM bloat)
- Lazy loading for graph data
- Debounced search with client-side caching

npm dependency: `idb` (IndexedDB wrapper)
