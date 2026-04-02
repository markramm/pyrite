---
id: web-ui-alpha-banner
title: "Web UI Alpha Banner and Feedback Integration"
type: backlog_item
tags:
- ui
- feedback
- launch
kind: feature
status: done
priority: high
effort: S
---

## Problem

The web UI ships without any indication that it's alpha-quality software. Users encountering bugs may not know where to report them, and rough edges create the impression of a finished product falling short rather than an early release inviting feedback.

## Solution

### 1. Persistent Alpha Badge

Small "Alpha" badge in the top bar / sidebar — always visible, not dismissable. Links to a brief "What does alpha mean?" tooltip or popover explaining:
- This is early software, expect rough edges
- Data is safe (git-backed), but UI may have bugs
- Feedback welcome

### 2. Floating Feedback Button

Persistent floating button (bottom-right corner) that opens a GitHub issue with a pre-filled template:
- Auto-includes: Pyrite version, browser, current page URL
- Links to `https://github.com/markramm/pyrite/issues/new?template=bug_report.md`

### 3. Error Pages with "Report This" Links

When the UI hits an error (500, unhandled exception, failed API call):
- Show a friendly error message instead of raw stack traces
- Include a "Report this bug" link that pre-fills a GitHub issue with error context
- Include the error details in a collapsible section for power users

### 4. Known Issues / Changelog Link

Add a link in the sidebar or help menu to:
- GitHub releases page (changelog)
- GitHub issues page (known issues)

## Success Criteria

- Alpha badge visible on every page
- Feedback button accessible from every page
- Error states include "report this" links with pre-filled context
- Users can find changelog and known issues within 1 click
