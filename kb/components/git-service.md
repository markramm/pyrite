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

Git operations service using subprocess. Provides commit log, diff, blame, push, clone, pull, fork, and PR creation. Deliberately avoids gitpython/pygit2. Stateless class with all `@staticmethod` methods.

Used by version history endpoint, kb_commit/kb_push MCP tools, CLI git commands, ExportService (export-to-repo), and RepoService (subscribe, fork, sync). See [[collaboration-services]] for full method listing.
