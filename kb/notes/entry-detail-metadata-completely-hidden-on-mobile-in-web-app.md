---
id: entry-detail-metadata-completely-hidden-on-mobile-in-web-app
title: Entry detail metadata completely hidden on mobile in web app
type: backlog_item
tags:
- bug
- web
- mobile
- ux
importance: 5
kind: bug
status: todo
priority: high
effort: M
rank: 0
---

## Problem

In the Pyrite web app:
1. **Entry metadata sidebar** (line 332) has class='hidden ... lg:block' — on mobile, users cannot see entry type, tags, participants, sources, outlinks, dates, or any metadata. No alternative access.
2. **Panel toggle buttons** (Outline, Backlinks, Graph, Version History at lines 253-300) are all 'hidden lg:flex'. No mobile alternative.

## Fix

Options:
- Collapsible metadata section above or below the entry body on mobile
- Bottom sheet pattern for metadata
- Tab bar for switching between content / metadata / backlinks

## Scope

Pyrite-general — affects all web app users on mobile.
