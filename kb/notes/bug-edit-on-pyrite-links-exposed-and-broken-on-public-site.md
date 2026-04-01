---
id: bug-edit-on-pyrite-links-exposed-and-broken-on-public-site
title: 'Bug: Edit on Pyrite links exposed and broken on public site'
type: backlog_item
tags:
- bug
- site-cache
- ux
importance: 5
kind: bug
status: todo
priority: high
effort: S
rank: 0
---

## Problem

Every event page on capturecascade.org shows an 'Edit on Pyrite' link that resolves to a JSON error: {"detail":"Not Found"}. These are admin-facing links exposed to the public.

## Fix

Either:
1. Hide 'Edit on Pyrite' links on public/read-only site cache deployments
2. Make them resolve to something useful (e.g., the entry's source file on GitHub)

Option 1 is simpler. The site cache renderer should detect read-only/public mode and omit edit links.

## Scope

Pyrite-general: affects any public site cache deployment.
