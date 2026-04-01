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
status: todo
priority: critical
effort: S
rank: 0
---

## Problem

/site/cascade-timeline/_about displays 'Page not yet rendered. Run site cache render.' on a blank white page with no site chrome. This is linked from the homepage twice. It's the credibility page a journalist evaluating sourcing standards would check first.

## Fix

Either the about page entry doesn't exist in the KB, or the site cache render didn't include it. Need to create the entry and re-render, or fix the render pipeline to include special pages.

## Scope

Cascade-specific content, but the site cache render gap is Pyrite-general.
