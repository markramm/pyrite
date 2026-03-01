---
id: demo-site-deployment
title: "Demo Site Deployment"
type: backlog_item
tags:
- feature
- infrastructure
- launch
- deployment
kind: feature
priority: high
effort: M
status: planned
links:
- launch-plan
- extension-registry
- roadmap
---

## Problem

Visitors from HN, Reddit, or blog posts need to experience Pyrite immediately — without installing anything. A live demo site with pre-loaded data turns "interesting concept" into "I want to try this." Without a demo site, every potential user faces a cold install before they can evaluate whether Pyrite fits their needs.

## Solution

A hosted demo instance with pre-loaded KB data, accessible via the web UI. Showcases the knowledge graph, entry editor, collections, timeline, QA dashboard, and (read-only) AI features.

### Architecture

Pyrite's architecture is self-contained: FastAPI backend + SQLite database + static SvelteKit frontend. No external services required (Postgres, Redis, etc.). This makes hosting simple and cheap.

### Hosting Options (evaluated)

| Option | Monthly Cost | Notes |
|--------|-------------|-------|
| Fly.io (1 shared CPU, 256MB) | ~$3-5 | Persistent volume for SQLite, auto-sleep on idle |
| Railway | ~$5 | Simple deploy from Dockerfile |
| Render | Free tier available | 750 hrs free, spins down on idle |
| VPS (Hetzner) | ~$4 | Full control, cheapest long-term |

**Recommended:** Fly.io or Railway for simplicity. ~$5/month.

### Demo Data

Pre-loaded with interesting, browsable content:

- **Pyrite's own KB** — dogfooding, shows a real software project KB
- **Extension registry KB** — demonstrates the extension ecosystem
- **Sample investigation KB** (if wave 3 ready) — "follow the money" with public data

### Deliverables

1. **Dockerfile update**: Production-ready container with pre-built frontend, optimized for deployment
2. **Deploy config**: `fly.toml` or `railway.json` with correct settings
3. **Demo data seeding**: Script to load pre-built KB data into demo instance
4. **Read-only mode**: Demo site runs with read-tier API keys only (visitors can browse but not modify)
5. **Reset mechanism**: Cron or manual script to reset demo data periodically

## Prerequisites

- Web UI stable and demo-ready (0.7 polish)
- At least one interesting KB to showcase
- Dockerfile exists (basic version in repo)

## Success Criteria

- Demo site accessible at a public URL
- Page loads in under 3 seconds
- Knowledge graph renders smoothly with 100+ entries
- Visitors can browse entries, explore the graph, search, and view collections
- Monthly hosting cost under $10
- Auto-resets weekly to clean state

## Launch Context

Ships with wave 1 (0.8 alpha). The demo site is the first thing linked in every blog post, HN comment, and README. It's the difference between "read about it" and "try it now."
