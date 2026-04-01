---
id: bug-about-methodology-page-returns-not-yet-rendered-on-capturecascade-org
title: "Bug: About & Methodology page returns 'not yet rendered' on capturecascade.org"
type: backlog_item
tags:
- bug
- site-cache
- cascade
importance: 5
kind: bug
status: in_progress
priority: critical
effort: S
rank: 0
---

## Status

Link fix shipped: the homepage now only shows the About link when an _about entry exists in the KB.

Remaining work: create the _about entry in cascade-timeline KB with methodology content, then re-render the site cache.

## Problem

/site/cascade-timeline/_about displays 'Page not yet rendered.' This is linked from the homepage twice. It's the credibility page a journalist evaluating sourcing standards would check first.

## Root Cause

The _about entry does not exist in the cascade-timeline KB. The link was hardcoded unconditionally in _render_designed_homepage(). Fixed: link is now conditional on entry existence.

## Remaining

1. Create _about entry in cascade-timeline KB with methodology content
2. Re-render site cache
