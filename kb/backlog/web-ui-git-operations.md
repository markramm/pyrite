---
id: web-ui-git-operations
type: backlog_item
title: "Web UI: Git commit, push, pull, and diff operations"
kind: feature
status: proposed
priority: high
effort: L
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

Users who edit knowledge base files through the web UI or locally have no way to commit, push, pull, or view diffs from the browser. All git operations require the CLI or an external git client, breaking the workflow for users who rely solely on the web UI.

## Solution

Add a git operations panel to the KB settings page. Show a list of uncommitted changes (staged and unstaged), allow users to stage files, enter a commit message and commit, push to and pull from the configured remote, and view file-level diffs. Implement via new API endpoints that invoke git operations on the server side with appropriate guards and error handling.
