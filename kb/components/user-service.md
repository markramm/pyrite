---
id: user-service
title: User Service
type: component
kind: service
path: pyrite/services/user_service.py
owner: core
dependencies:
- pyrite.storage
tags:
- core
- service
- auth
---

Identity management for collaboration. Maps GitHub OAuth identity to local user records. Provides a sentinel "local" user for non-authenticated setups so attribution is always available.

## Related

- [[auth-service]] — session-based authentication
- [[collaboration-services]] — uses user identity for change attribution
