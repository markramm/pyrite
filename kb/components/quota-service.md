---
type: component
title: "Quota Service"
kind: service
path: "pyrite/services/quota_service.py"
owner: "core"
dependencies: ["pyrite.config"]
tags: [core, services, auth]
---

`QuotaService` enforces usage tier limits for KB and entry creation. Extracted from `KBService` in 0.18.

## Methods

| Method | Description |
|--------|-------------|
| `check_kb_creation_allowed()` | Check if user can create another KB based on tier limits |
| `check_entry_creation_allowed()` | Check if adding another entry is within tier limits |

## Related

- [[kb-service]] — facade delegator for quota methods
- [[auth-service]] — uses quota checks during KB creation
