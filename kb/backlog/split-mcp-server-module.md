---
id: split-mcp-server-module
type: backlog_item
title: "Split pyrite/server/mcp_server.py (1790 LOC) into per-tier modules"
kind: refactor
status: proposed
priority: low
effort: M
tags: [refactor, mcp, code-quality]
---

## Problem

`pyrite/server/mcp_server.py` is 1790 LOC and growing every time a new tool
is added. It mixes:

- Tool registration for three tiers
- Tool handler implementations (~40 read-tier, ~12 write-tier, ~9
  admin-tier)
- Rate-limiter setup
- Plugin tool aggregation
- Error helpers
- Bearer-token transport hooks

Result: adding a new tool is a long-file diff that's hard to review, and
`grep` for tool definitions returns multiple unrelated matches.

The companion `tool_schemas.py` (1133 LOC) holds the descriptions. So
there are already two giant files where there could be one folder.

## Solution

Adopt the same split pattern that `pyrite/server/endpoints/` uses:

```
pyrite/server/mcp/
├── __init__.py          # PyriteMCPServer class, tier wiring
├── read_tools.py        # all read-tier tool handlers + schemas
├── write_tools.py       # write-tier
├── admin_tools.py       # admin-tier
├── plugin_loader.py     # plugin tool aggregation
├── rate_limiter.py      # already separate, move here
└── errors.py            # _error() helper + error codes
```

Each tool stays a single function with its schema co-located. Server class
imports the lists and registers them.

## Acceptance criteria

- `mcp_server.py` shrinks to < 400 LOC (just the orchestration class).
- All tools and tests pass unchanged.
- No public-API change — bearer-token transport and tier flags work the
  same.
- Adding a new tool is now one file edit, not three.

## Out of scope

- Code-generating tools from a shared schema (see `mcp-rest-tool-parity`).
- Renaming tools (separate ticket if appetite exists).

## Related

- `mcp-rest-tool-parity` — a cleaner module split makes parity audits
  much cheaper
- `split-database-module` (done) — same pattern, prior art
