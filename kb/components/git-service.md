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

Git operations service wrapping gitpython. Provides commit log, diff, blame, and push operations. Used by version history endpoint, kb_commit/kb_push MCP tools, and CLI git commands.
