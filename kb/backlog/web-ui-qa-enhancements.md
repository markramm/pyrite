---
id: web-ui-qa-enhancements
type: backlog_item
title: "Web UI: QA page enhancements (filtering, dismiss, auto-fix, trends)"
kind: feature
status: proposed
priority: low
effort: M
tags: [web, ux]
---

## Problem

The QA page shows a flat list of issues with no way to filter by rule, acknowledge or dismiss known issues, apply automatic fixes for safe issues, or see how quality metrics change over time. This limits the QA page's usefulness for ongoing knowledge base maintenance.

## Solution

Add rule-based filtering dropdowns and severity toggles to the QA page. Implement issue acknowledgment and dismiss actions that persist state. Add an auto-fix button for issues flagged as safely auto-fixable by the backend. Include a historical trend chart showing issue counts over time to help users track quality improvements.
