---
id: playwright-integration-tests
title: "Web UI Playwright Integration Tests"
type: backlog_item
tags:
- testing
- frontend
- web-ui
- quality
kind: feature
priority: high
effort: M
status: proposed
links:
- web-ui-auth
- ux-accessibility-fixes
- demo-site-deployment
---

## Problem

The web UI has unit tests (vitest) but no integration tests. Playwright config exists (`playwright.config.ts`) but the `e2e/` directory is empty. Before the demo site goes public, we need confidence that core user flows actually work end-to-end against a real backend.

The web UI has 96 source files across 13 route groups (entries, search, graph, timeline, collections, daily, qa, settings, login, register) plus shared components. None of these flows are tested beyond unit level.

## Proposed Solution

### Phase 1: Core flows (M)

Scaffold `web/e2e/` and write tests for the critical user journeys:

1. **Smoke test** — app loads, sidebar renders, navigation works
2. **Search** — keyword search returns results, click-through to entry
3. **Entry CRUD** — create entry, view it, edit it, delete it
4. **Entry detail** — frontmatter renders, body renders markdown, links work, backlinks show
5. **Graph view** — graph renders nodes, clicking a node navigates
6. **Timeline** — timeline loads, date filtering works
7. **Auth flow** — register, login, logout, protected routes redirect to login
8. **Collections** — list collections, view collection entries

### Phase 2: Edge cases and regression (S, ongoing)

- Error states (404, API errors, empty states)
- Mobile viewport tests (sidebar collapse, toolbar wrap)
- Search modes (keyword, semantic, hybrid) if backend supports them in test env

### Test infrastructure

- Playwright config already set up to start both backend (uvicorn) and frontend (vite dev)
- Tests need a seeded test KB — create a fixture script or use `pyrite init` + `pyrite create` in `globalSetup`
- CI integration: add Playwright to the GitHub Actions CI workflow

## Files

| File | Action | Summary |
|------|--------|---------|
| `web/e2e/*.spec.ts` | Create | Integration test files |
| `web/e2e/fixtures.ts` | Create | Shared test fixtures (auth, seeded KB) |
| `web/playwright.config.ts` | Edit | Add globalSetup for test KB seeding |
| `.github/workflows/ci.yml` | Edit | Add Playwright job |

## Success Criteria

- `npm run test:e2e` runs and passes
- All 8 core flows covered
- Tests run in CI on every PR
- Test run completes in under 2 minutes
