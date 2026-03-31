---
id: bulk-import-from-directory
type: backlog_item
title: "Bulk import entries from a directory"
kind: feature
status: proposed
priority: low
effort: M
tags: [cli, import, ux]
---

## Problem

When 243 files needed to be copied from the old timeline path to the Pyrite KB, the workflow was `cp` + `pyrite index sync`. This works but is manual.

## Solution

`pyrite import /path/to/files/ -k cascade-timeline` that copies files and indexes them in one step. Would also be useful for the social-archive-to-KB pipeline.

## Workaround

`cp` files into KB directory + `pyrite index sync` works today.

## Reported By

User testing daily-capture skill with cascade-timeline KB (2026-03-31).
