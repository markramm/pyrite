---
id: document-undocumented-services
type: backlog_item
title: "Create component docs for 9 undocumented services"
kind: enhancement
status: proposed
priority: medium
effort: M
tags: [docs, kb, components]
epic: epic-release-readiness-review
---

## Problem

9 services in code have no component documentation in the KB:
1. site-cache (SiteCacheService)
2. task-service (TaskService)
3. oauth-providers (OAuthProviders)
4. template-service (TemplateService)
5. repo-service (RepoService)
6. url-checker (URLChecker)
7. query-expansion-service
8. index-worker
9. llm-rubric-evaluator

## Fix

Create `type: component` entries for each via `pyrite create -k pyrite -t component`. Include kind, path, owner, dependencies fields.
