---
id: web-ui-user-management
title: "Web UI: User list, roles, and per-KB permissions"
type: backlog_item
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
effort: M
---

## Problem

User management is only accessible via the API and CLI. Administrators cannot view the user list, assign roles, or configure per-KB permissions from the web UI, making multi-user deployments harder to manage.

## Solution

Add a user management section to the settings page showing a list of all users with their roles. Allow administrators to create users, assign and revoke roles, and grant or revoke per-KB permissions (read, write, admin). Include search and filtering for large user lists.
