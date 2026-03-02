---
id: git-service
title: Git Service
type: component
kind: service
path: pyrite/services/git_service.py
owner: core
tags:
- core
- service
---

Git operations service using subprocess. Provides commit log, diff, blame, and push operations. Deliberately avoids gitpython/pygit2. Used by version history endpoint, kb_commit/kb_push MCP tools, and CLI git commands.
