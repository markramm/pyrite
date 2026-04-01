---
id: starred-entries-in-sidebar-show-raw-ids-instead-of-titles
title: Starred entries in sidebar show raw IDs instead of titles
type: backlog_item
tags:
- bug
- web
- ux
importance: 5
kind: bug
status: todo
priority: low
effort: XS
rank: 0
---

## Problem

In the web app sidebar, starred entries display the raw entry_id instead of the entry title. The StarredEntryItem type only has entry_id and kb_name, no title field.

## Fix

Resolve entry titles when loading starred entries, either by batch-fetching entry metadata or by storing the title alongside the starred entry.

## Scope

Pyrite-general.
