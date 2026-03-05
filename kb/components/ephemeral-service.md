---
type: component
title: "Ephemeral KB Service"
kind: service
path: "pyrite/services/ephemeral_service.py"
owner: "core"
dependencies: ["pyrite.config", "pyrite.storage"]
tags: [core, services, ephemeral]
---

`EphemeralKBService` manages temporary knowledge bases with TTL-based expiration. Extracted from `KBService` in 0.18.

## Methods

| Method | Description |
|--------|-------------|
| `create_ephemeral_kb()` | Create an ephemeral KB with TTL, register in config and DB |
| `gc_ephemeral_kbs()` | Garbage-collect expired ephemeral KBs, remove files and config |

## Related

- [[kb-service]] — facade delegator for ephemeral methods
- [[per-kb-permissions]] — ephemeral KBs used for sandboxed access
