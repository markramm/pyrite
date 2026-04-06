---
id: hosted-instance-infrastructure-for-journalists-pyrite-wiki
title: Hosted Instance Infrastructure for journalists.pyrite.wiki
type: backlog_item
tags:
- deployment
- infrastructure
- hosting
- security
links:
- target: epic-journalists-pyrite-wiki-hosted-research-platform-for-independent-journalists
  relation: subtask_of
  kb: pyrite
- target: hosting-security-hardening
  relation: depends_on
  kb: pyrite
importance: 5
---

## Problem

Need a production deployment of Pyrite for journalists.pyrite.wiki -- a VPS or cloud instance running the full stack (FastAPI backend, SvelteKit frontend, SQLite, git repos) with TLS, backups, and monitoring.

## Solution

1. **Deployment configuration** -- Docker Compose or systemd setup for Pyrite backend + static frontend + reverse proxy (Caddy/nginx)
2. **TLS** -- Automatic HTTPS via Caddy or Let's Encrypt
3. **Backup** -- Automated daily backup of SQLite databases and git repos to off-site storage
4. **Monitoring** -- Basic health checks and uptime monitoring
5. **Domain setup** -- journalists.pyrite.wiki DNS and TLS certificate
6. **Resource sizing** -- Pyrite is lightweight (Python + SQLite + static SPA), a small VPS should suffice for initial user base

## Prerequisites

- [[hosting-security-hardening]] -- security hardening epic (already in backlog)
- Multi-user auth (already built)
- BYOK API key management

## Success Criteria

- Instance running at journalists.pyrite.wiki with HTTPS
- Automated daily backups
- Uptime monitoring with alerting
- Can handle 10+ concurrent users without degradation
