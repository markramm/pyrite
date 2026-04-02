---
id: harmonize-app-site-fonts
title: "Harmonize font stacks between SvelteKit app and static site pages"
type: backlog_item
tags: [frontend, design, consistency]
kind: enhancement
status: done
effort: M
---

## Problem

The SvelteKit app uses serif display headings (DM Serif Display) + sans body (Inter), while static site pages use sans headings (DM Sans) + serif body (Source Serif 4). The font choices are inverted. A user navigating between `/site/` and the app experiences a jarring style shift.

## Fix

Decide on one font strategy and apply consistently, or make the contrast intentional with shared colors/spacing as a bridge. Update both `web/src/app.css` and `site_cache.py` template CSS.
