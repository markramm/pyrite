---
id: container-deployment
title: "Docker Container and One-Click Deployment"
type: backlog_item
tags:
- feature
- distribution
- deployment
- docker
kind: feature
priority: high
effort: M
status: planned
links:
- pypi-publish
- demo-site-deployment
- roadmap
---

## Problem

`pip install pyrite` is the developer install path, but it's not a deployment story. A team lead who wants "Pyrite running for my 5-person team" needs to provision a server, install Python, manage dependencies, configure a reverse proxy, set up TLS, and keep it updated. That's an afternoon of work and ongoing maintenance.

Meanwhile, Notion Team costs $10/user/month ($50/month for 5 people). If Pyrite can run on a $6/month VPS with zero friction, that's a compelling alternative — but only if the deployment is genuinely easy.

## Solution

### Phase 1: Dockerfile + Docker Compose (M)

Production-ready container setup that replaces the current stale Dockerfile (which references the old `cascade_research` module).

**`Dockerfile`:**
- Multi-stage build: build frontend in Node stage, copy into Python stage
- Python 3.12-slim base
- Installs `pyrite[all]` (server + AI + semantic)
- Runs via `uvicorn` with sensible defaults
- Health check endpoint
- Non-root user

**`docker-compose.yml`:**
```yaml
services:
  pyrite:
    build: .
    ports:
      - "8088:8088"
    volumes:
      - pyrite-data:/data
    environment:
      - PYRITE_DATA_DIR=/data
      - PYRITE_AUTH_ENABLED=true
    restart: unless-stopped

volumes:
  pyrite-data:
```

That's the minimal version. Also provide `docker-compose.prod.yml` with:
- Caddy reverse proxy (automatic TLS)
- Optional Postgres backend (for teams wanting more than SQLite)
- Environment variable configuration for all auth settings

**Quickstart:**
```bash
git clone https://github.com/markramm/pyrite && cd pyrite
docker compose up -d
# Visit http://localhost:8088, register first user (becomes admin)
```

Or without cloning:
```bash
curl -O https://raw.githubusercontent.com/markramm/pyrite/main/docker-compose.yml
docker compose up -d
```

### Phase 2: One-Click Deploy Buttons (S)

Add "Deploy to X" buttons to the README. These services read the Dockerfile natively:

- **Railway** — `railway.json` or `railway.toml` config, "Deploy on Railway" button
- **Render** — `render.yaml` blueprint, "Deploy to Render" button
- **Fly.io** — `fly.toml`, `flyctl launch` one-liner

These are thin config files (< 20 lines each) that point at the Dockerfile and set environment variables. Effort is small once the Dockerfile exists.

Priority order: Railway first (simplest DX, free tier available), then Render, then Fly.io.

### Phase 3: DigitalOcean Marketplace (defer)

DO 1-Click Apps require Packer image builds and marketplace submission. Higher effort, lower reach than generic Docker. Defer to 0.13 or later if there's demand.

## Environment Variable Configuration

The container needs env-var overrides for all key settings so users don't need to mount a config file:

| Variable | Maps to | Default |
|----------|---------|---------|
| `PYRITE_DATA_DIR` | Data/KB storage path | `/data` |
| `PYRITE_AUTH_ENABLED` | `auth.enabled` | `false` |
| `PYRITE_AUTH_ANONYMOUS_TIER` | `auth.anonymous_tier` | `none` |
| `PYRITE_AUTH_ALLOW_REGISTRATION` | `auth.allow_registration` | `true` |
| `PYRITE_GITHUB_CLIENT_ID` | `auth.providers.github.client_id` | — |
| `PYRITE_GITHUB_CLIENT_SECRET` | `auth.providers.github.client_secret` | — |
| `PYRITE_OPENAI_API_KEY` | AI provider key | — |
| `PYRITE_ANTHROPIC_API_KEY` | AI provider key | — |

This requires a small config loader change: env vars override YAML config values.

## Files

| File | Action | Phase | Summary |
|------|--------|-------|---------|
| `Dockerfile` | Rewrite | 1 | Multi-stage production build |
| `docker-compose.yml` | Create | 1 | Minimal single-service setup |
| `docker-compose.prod.yml` | Create | 1 | Production: Caddy + optional Postgres |
| `.dockerignore` | Create | 1 | Exclude .git, node_modules, .venv, tests, kb/ |
| `pyrite/config.py` | Edit | 1 | Env var override support in config loading |
| `railway.json` | Create | 2 | Railway deploy config |
| `render.yaml` | Create | 2 | Render blueprint |
| `fly.toml` | Create | 2 | Fly.io config |

## Prerequisites

- PyPI publish (#74) — so the Dockerfile can `pip install pyrite[all]` from PyPI instead of copying source
  - Alternative: Dockerfile can `COPY . .` and `pip install .` if we want to ship before PyPI publish. This works fine and is what most projects do.

## Success Criteria

- `docker compose up` from a clean machine → working Pyrite instance in < 2 minutes
- Data persists across container restarts (volume mount)
- Auth configurable via environment variables alone (no config file editing)
- README "Deploy to Railway" button → working instance in < 3 minutes
- Container image < 500MB

## The Pitch

> Notion Team: $50/month for 5 users.
> Pyrite on a $6 VPS: $6/month, unlimited users, you own your data.
>
> `docker compose up -d` — done.

## Launch Context

Ships as part of 0.12 Distribution track. Phase 1 (Docker) alongside or just after PyPI publish. Phase 2 (deploy buttons) is quick follow-on. This is the primary self-hosting story for non-developer team leads.
