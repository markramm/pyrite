---
id: private-kb-read-scoping-covers-every-content-route-enforced-by-a-structural
title: Private-KB read scoping covers every content route, enforced by a structural test (part 1)
type: backlog_item
tags:
- security
- bug
- auth
importance: 5
kind: bug
status: in_progress
priority: critical
assignee: agent:pyrite-worker
effort: M
rank: 0
---

## Problem

Per-KB read scoping (`readable_kbs`, `get_readable_kbs`, `requires_kb_read`,
`assert_kb_readable`, `kb_not_found` in `pyrite/server/api.py`) was added to the
entry, search, graph, link and KB routes, and the `[Unreleased]` changelog says
private KBs are protected on every read route. They are not: sixteen endpoint
modules that serve KB content have no scoping at all, so on an auth-enabled
instance a caller who cannot read a private KB (a logged-in peer, or an
anonymous visitor) still receives content from it while the entry route itself
correctly returns 404. Found by the 2026-09-19 design review; reproduced in the
fixtures of `tests/test_private_kb_read_scoping.py`.

Nothing enforces that a new route is scoped, which is how this happened: the
rule lives in a docstring.

## Groom 2026-09-19 (conductor; maintainer priority 1)

Model: opus (auth/permissions). Cold read: **mandatory**. heavy: no. Never an
outside-contributor task. Sequence: first; nothing in flight touches these
modules except #161 (`endpoints/repos.py`, part 2 of this work — see Out of scope).

This is **part 1 of 2**: the structural gate plus every route that returns
KB *content*. Part 2 (meta/admin routes) removes the remaining allowlist entries.

### Acceptance

1. **A structural test** (`tests/test_read_scoping_is_structural.py`) walks the
   real FastAPI app's routes and fails for any route under `/api` — any HTTP
   verb — that is neither (a) scoped: `requires_kb_read()` in its dependencies,
   or a `get_readable_kbs` / `readable_kbs` / `assert_kb_readable` use in its
   dependant tree or handler, nor (b) on an explicit allowlist in that test
   file, where every entry carries a one-line reason ("serves no KB content",
   "admin tier only", "part 2: …"). Adding a new unscoped route must fail the
   test with a message that says what to do.
2. **Every content route is scoped**, with the existing conventions: a route
   that names a KB (`kb` / `kb_name` in query, path or body) uses
   `requires_kb_read()` and answers **404 `KB_NOT_FOUND`**, never 403, for a KB
   the caller may not read — byte-identical to the response for a KB that does
   not exist; a route that spans KBs filters with `get_readable_kbs` (push the
   filter into the service/query where one exists, as `search.py` does with
   `kb_names=`; do not fetch everything and filter in Python where that breaks
   `limit`/`count`). Routes: `tags.py` (`/tags`, `/tags/tree`), `timeline.py`,
   `qa.py` (`/qa/status`, `/qa/validate`, `/qa/validate/{entry_id}`,
   `/qa/coverage`), `versions.py` (both), `blocks.py`, `daily.py`
   (`/daily/dates`, `/daily/{date}`), `collections.py` (all four), `tasks.py`,
   `starred.py`, `templates.py`, `reviews.py` (all three), and the four
   `ai_ep.py` POST routes (`/ai/summarize`, `/ai/auto-tag`,
   `/ai/suggest-links`, `/ai/chat` — retrieval must only see readable KBs).
3. **Behavioural tests** extend `tests/test_private_kb_read_scoping.py`: for
   every route above, a parametrized case as `peer` and as `anon` against the
   private KB (seed it with a tagged, dated `event` entry so timeline, tags and
   QA have something to leak) asserting no private id, title, tag, body text or
   KB name appears in the response, that a named private KB gives the same 404
   as a nonexistent KB, that `admin` and a granted peer still see it, and that
   an unscoped caller (auth disabled / operator API key) is unchanged.
4. No route's response changes for a caller who can read everything; existing
   suites pass unchanged.
5. `CHANGELOG.md`: fold into the existing `[Unreleased] ### Security` entry
   about private KBs so that its "every read route" sentence becomes true;
   name the routes.

### Regimes (each needs a test that enters it)

- a KB-spanning route with **no `kb` parameter** (the aggregate leak: `/tags`,
  `/timeline`, `/qa/status`, `/starred`, `/tasks`, `/ai/chat`);
- a named private KB vs a nonexistent KB — identical status and body;
- an entry id that exists only in a private KB, addressed **without** `kb`
  (`/entries/{id}/versions`, `/entries/{id}/blocks`, `/qa/validate/{entry_id}`);
- counts and pagination: `count`/`total`/`has_more` must not include or reveal
  private rows (a count of 3 for a KB you cannot read is a leak);
- error messages: no private KB name or entry id echoed in a 404/400 body;
- a caller with a grant on the private KB; a global admin; auth disabled;
- `ai/chat` and `ai/suggest-links` with the AI provider stubbed — assert on the
  retrieval call's `kb_names`, not on model output.

### Touches

Existing: the endpoint modules named above; their services only where a
`kb_names` filter must be threaded (`KBService.get_tags`/`get_tag_tree`/
`get_timeline`, QA service, collections, tasks, starred, reviews — read each
before deciding); `tests/test_private_kb_read_scoping.py`; `CHANGELOG.md`.
New: `tests/test_read_scoping_is_structural.py`.

### Out of scope (part 2 — put on the allowlist with "part 2" reasons)

`admin.py` (`/stats`, `/plugins*`, `/ai/status`, `/usage/me`,
`/index/embed-status`, `/kbs/{name}/permissions`), `settings_ep.py`,
`repos.py` (open PR #161 touches it), `worktree.py`, `git_ops.py`
(`/kbs/{kb_name}/changes` has a tier check but no KB check), export routes,
the SEO/sitemap router (public by design: `default_role == read` only), and
**MCP over HTTP** (`mcp_routes.py` — tier by key, no per-KB scoping today):
inventory what you find there in the report's "Left", do not change it.
