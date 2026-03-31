---
id: web-ui-user-management
type: backlog_item
title: "Web UI: User list, roles, and per-KB permissions"
kind: feature
status: done
priority: medium
effort: M
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

User management is only accessible via the API and CLI. Administrators cannot view the user list, assign roles, or configure per-KB permissions from the web UI, making multi-user deployments harder to manage.

## Solution

Add a user management section to the settings page showing a list of all users with their roles. Allow administrators to create users, assign and revoke roles, and grant or revoke per-KB permissions (read, write, admin). Include search and filtering for large user lists.
