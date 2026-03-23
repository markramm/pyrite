---
id: web-ui-webhook-config
type: backlog_item
title: "Web UI: Webhook and integration configuration"
kind: feature
status: proposed
priority: low
effort: M
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

There is no UI for configuring webhooks or external integrations. Users who want to set up event-driven integrations (e.g., notify an external service when an entry is created or updated) must configure them manually or via the API.

## Solution

Add a webhook/integration configuration page under settings. Allow users to define webhook endpoints with a target URL, select event triggers (entry created, updated, deleted, reviewed, etc.), configure HTTP method and headers, and test the webhook with a sample payload. Show delivery history with success/failure status for debugging.
