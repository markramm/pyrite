---
id: web-ui-first-run-experience
title: "First-run experience for new installs"
type: backlog_item
tags:
- feature
- frontend
- web-ui
- onboarding
kind: feature
priority: high
effort: S
status: proposed
links:
- web-ui-review-hardening
- demo-site-deployment
---

## Problem

A new user who installs Pyrite and opens the web UI sees a dashboard with zeros and empty lists. It looks broken rather than intentional. There's no guidance on what to do next.

## Solution

When no KBs exist (or the active KB is empty):
- Dashboard shows a welcome/getting-started state instead of empty stat cards
- Guide the user: "Create your first KB" or "Import a KB" with clear CTAs
- Show the CLI quickstart commands as an alternative path

For the demo site, this is less critical (KBs will be pre-loaded), but matters for self-hosted installs.
