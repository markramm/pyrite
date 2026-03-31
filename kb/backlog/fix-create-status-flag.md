---
id: fix-create-status-flag
type: backlog_item
title: "pyrite create should support --status flag"
kind: feature
status: todo
priority: medium
effort: S
tags: [cli, create, ux]
---

## Problem

Events should have `status: confirmed` or `status: draft` but `pyrite create` doesn't have a `--status` flag, and `-f "status=confirmed"` is silently dropped (same root cause as [[fix-create-f-drops-structured-fields]]).

## Solution

Add `--status` flag to `pyrite create`, defaulting to `draft` for new entries. This is a common enough field to warrant its own flag.

Note: fixing the `-f` silent drop bug would also fix this, but a dedicated `--status` flag is still good UX.

## Reported By

User testing daily-capture skill with cascade-timeline KB (2026-03-31).
