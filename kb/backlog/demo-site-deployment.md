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
- pyrite-website
- awesome-plugins-page
- launch-plan
- extension-registry
- roadmap
---

## Problem

Visitors from HN, Reddit, or blog posts need to experience Pyrite immediately — without installing anything. A live demo site with pre-loaded data turns "interesting concept" into "I want to try this." Without a demo site, every potential user faces a cold install before they can evaluate whether Pyrite fits their needs.

## Solution

A hosted Pyrite instance running the full web UI at `demo.pyrite.dev`, loaded with curated KBs from the awesome-list. Part of the three-layer web presence (see [[pyrite-website]]).

### Architecture

The demo site runs Pyrite's full stack on the PostgresBackend (0.10 delivered):

```
Internet → [Reverse proxy (Caddy)] → [Uvicorn :8088]
                                          ↓
                              [PostgresBackend (knowledge index)]
                              [SQLite or Postgres (app state)]
                              [Static SvelteKit frontend]
```

No AI inference runs server-side. All AI features (summarize, auto-tag, chat sidebar, semantic search) are BYOK — they only fire when a user provides their own API key through settings. Hosting costs are just compute + database, no GPU, no embedding pipeline.

### Hosting

| Option | Monthly Cost | Notes |
|--------|-------------|-------|
| Fly.io (1 shared CPU, 256MB) | ~$3-5 | Persistent volume, auto-sleep on idle |
| Railway | ~$5-7 | Simple deploy from Dockerfile |
| VPS (Hetzner) | ~$4 | Full control, cheapest long-term |

**Recommended:** Fly.io or Railway for simplicity. ~$5-20/month depending on traffic.

### Curated KB Loading (Awesome-List Model)

The demo site loads KBs from curated git repos on the awesome-list, not user-generated content:

1. Author creates a KB locally with `pyrite init`, pushes to GitHub
2. Author submits to the awesome-list (PR, reviewed for quality)
3. Once accepted, the demo site pulls the repo, runs `pyrite index sync`, and the KB is searchable

**Launch KBs:**
- **Journalism KBs** (CaptureCascade) — "follow the money" investigation data, the visual wow factor
- **Pyrite's own KB** — dogfooding credibility, also serves the docs layer on pyrite.dev

**Community KBs (post-launch):**
- As the awesome-list grows, the demo accumulates interesting KBs from different domains
- Visitors see the breadth of what Pyrite handles without us building it all

### Access Model

| Role | Access | Auth Required |
|------|--------|---------------|
| Anonymous visitor | Browse, search, explore graph on curated KBs | No |
| Registered user | All anonymous features + BYOK AI features | Yes |

No user-generated content on the demo site. Users who want to publish KBs create git repos and submit to the awesome-list. This eliminates content moderation overhead — curation criteria replace community guidelines.

### Deliverables

1. **Dockerfile update**: Production-ready container with pre-built frontend
2. **Deploy config**: `fly.toml` or `railway.json`
3. **KB seeding pipeline**: Script to clone awesome-list repos, index, and serve
4. **Auth integration**: Web UI auth (Phase 1, #94) with read-only anonymous + registered tiers
5. **Rate limiting**: MCP rate limiting (#97) for public-facing endpoints
6. **Sync mechanism**: Periodic pull of awesome-list repos to pick up updates

## Prerequisites

- Web UI auth Phase 1 (#94) — anonymous read-only + registered tiers
- MCP rate limiting (#97) — protect public-facing endpoints
- PostgresBackend (done, 0.10) — multi-user concurrent access
- At least one impressive KB to showcase (journalism KBs)
- Pyrite website (#110) — demo site is linked from pyrite.dev

## Success Criteria

- Demo site accessible at demo.pyrite.dev (or similar)
- Page loads in under 3 seconds
- Knowledge graph renders smoothly with 500+ entries across multiple KBs
- Visitors can browse, search, and explore without auth
- Registered users can use BYOK AI features
- Monthly hosting cost under $20
- Awesome-list KB updates reflected within 24 hours

## Launch Context

Ships as part of 0.12 launch prep. The demo site is linked from pyrite.dev, the blog post, HN comments, and README. It's the "try before you install" experience. Hosting costs are minimal because AI features are BYOK — no inference costs. If usage grows, the architecture supports federation or paid tiers naturally.
