---
id: add-adr-site-cache
title: "Write ADR for site cache / static HTML rendering decision"
type: backlog_item
tags: [docs, adr, site-cache]
kind: enhancement
status: done
effort: S
---

## Problem

The site cache service replaces the earlier Node SSR approach with Python-served static HTML. This significant architectural decision — choosing static rendering over SSR, choosing Python templates over SvelteKit — has no ADR documenting the rationale, alternatives considered, or trade-offs.

## Fix

Write ADR-0023 covering: problem (SEO for 5000+ entries), alternatives (Quartz export, SvelteKit SSR, Python static cache), decision rationale (no Node dependency, cache invalidation on sync, progressive JS enhancement).
