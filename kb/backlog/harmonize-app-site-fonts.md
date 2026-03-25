---
id: harmonize-app-site-fonts
type: backlog_item
title: "Harmonize font stacks between SvelteKit app and static site pages"
kind: enhancement
status: proposed
priority: medium
effort: M
tags: [frontend, design, consistency]
epic: epic-release-readiness-review
---

## Problem

The SvelteKit app uses serif display headings (DM Serif Display) + sans body (Inter), while static site pages use sans headings (DM Sans) + serif body (Source Serif 4). The font choices are inverted. A user navigating between `/site/` and the app experiences a jarring style shift.

## Fix

Decide on one font strategy and apply consistently, or make the contrast intentional with shared colors/spacing as a bridge. Update both `web/src/app.css` and `site_cache.py` template CSS.
