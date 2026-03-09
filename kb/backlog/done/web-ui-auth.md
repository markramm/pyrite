---
id: web-ui-auth
title: "Web UI Authentication"
type: backlog_item
tags:
- feature
- web-ui
- auth
- security
kind: feature
priority: high
effort: M
status: done
links:
- permissions-model
- demo-site-deployment
- roadmap
- oauth-providers
---

## Problem

The web UI has no authentication. The REST API has tier enforcement with API keys (#56, done), but the web UI bypasses this — anyone who can reach the server can read and write. This blocks:

- Demo site (needs read-only for visitors, write for admin)
- Corporate teams (need per-user access)
- Any multi-user deployment

## Solution

### Phase 1: Simple Auth (for demo site and small teams) -- DONE

- Session-based authentication with configurable auth backend
- Local user/password as the default (stored in DB, bcrypt hashed)
- API key mapping: authenticated users get a tier (read/write/admin) that maps to the existing REST API tier system
- Demo site runs with anonymous=read-tier, authenticated=write-tier
- Implementation: `AuthService`, `auth_endpoints.py`, migration v6, login/register pages

### Phase 2: SSO / OAuth (for corporate teams) -- see [[oauth-providers]]

- OAuth2/OIDC provider support (GitHub, Google, generic OIDC)
- Group-to-tier mapping (e.g., GitHub org members → write tier)
- Tracked as separate backlog item [[oauth-providers]] (#110)

### Configuration

```yaml
# pyrite.yaml
auth:
  enabled: true
  anonymous_tier: read  # or "none" to require login
  providers:
    - type: local
    - type: github
      client_id: ...
      allowed_orgs: [my-org]
      default_tier: write
```

## Prerequisites

- REST API tier enforcement (done, #56)
- Settings system (done, #30)

## Success Criteria

- Demo site: visitors browse without login, editing requires auth
- Local install: auth disabled by default (current behavior preserved)
- Corporate: SSO login with tier mapping
- All existing API key auth continues to work for MCP/CLI

## Launch Context

Phase 1 needed for demo site (0.8). Phase 2 needed for corporate adoption (post-launch). The three-layer permissions model (git → MCP tiers → application layer) already accounts for this — web UI auth is the application layer entry point.
