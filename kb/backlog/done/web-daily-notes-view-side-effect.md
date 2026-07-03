---
id: web-daily-notes-view-side-effect
title: "Web: visiting Daily Notes silently creates today's entry — navigation with a write side effect"
type: backlog_item
tags: [web, daily-notes, data-integrity, ux-audit-2026-07]
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
importance: 5
kind: bug
status: done
priority: high
effort: S
rank: 0
---

## Problem

Observed live on the demo 2026-07-03 during a READ-ONLY audit:
merely navigating to Daily Notes auto-created "Daily Note -
2026-07-03" in the `guide` KB — Total Entries went 4796 → 4797 and
the note appeared in Recent Entries ("1m ago") without any edit
action. Viewing a date creates data.

Why it matters beyond surprise: (a) GET-with-side-effects violates
the read/write tier model — a read-tier peer on the shared instance
could apparently create entries by browsing; (b) it pollutes the
corpus and git history with empty notes for every date anyone looks
at; (c) count drift erodes trust ("why did the entry count change?
I didn't do anything").

## Root cause

`GET /api/daily/{date_str}` (`pyrite/server/endpoints/daily.py`,
handler literally named `get_or_create_daily_note`) unconditionally
called `svc.create_entry(...)` whenever no note existed for the date,
with zero tier/permission check -- any authenticated (or anonymous,
if the KB's `default_role` allows it) caller triggered a write via a
plain GET. The frontend (`DailyNote.svelte`'s `$effect` on
`selectedDate`/`activeKB` change) calls this on every navigation,
including the initial mount.

## Fix

1. **Backend** (`pyrite/server/endpoints/daily.py`):
   - `GET /daily/{date_str}` no longer auto-creates for a caller
     without write access on the KB. Added a non-raising
     `resolve_effective_kb_role()` helper in `pyrite/server/api.py`
     (extracted from `requires_kb_tier`'s existing resolution chain --
     explicit KB grant → KB default_role → user global role →
     anonymous tier -- so both call sites share one source of truth).
     A sub-write-tier caller gets 404 `NOT_FOUND` instead of a created
     entry. Existing notes are still returned to any tier (reading an
     existing note is fine).
   - New `POST /daily/{date_str}` endpoint, gated
     `requires_kb_tier("write")`, that explicitly creates (or returns,
     if it already exists) the note. This is the only way a note now
     gets created from the web UI.
   - Shared the creation/lookup logic between both handlers via new
     `_load_existing_daily_note()`/`_create_daily_note()` helpers --
     no duplicated logic between GET and POST.
2. **Frontend** (`DailyNote.svelte`, `api/client.ts`):
   - New `api.createDailyNote(date, kb)` client method (`POST`).
   - `loadDailyNote()` now distinguishes a 404 (`ApiError` with
     `status === 404`) from a real error: sets a new `noNoteYet` state
     instead of the scary red error text.
   - New empty state: "No note for this date yet." + a "Start
     today's note" button, which calls `createDailyNote()` explicitly
     -- creation is now a deliberate user action, never a side effect
     of navigation.

## Tests

- `tests/test_daily_endpoints.py` (new, 6 tests, real auth via
  `TestClient` + a registered write-tier admin and a registered
  read-tier user): read-tier viewing a new date creates nothing (204→
  actually 404, verified no file written to disk either); write-tier
  viewing a new date still auto-creates (back-compat for the common
  single-user/self-hosted case); read-tier can still read an existing
  note; explicit `POST` create tests (write-tier succeeds, read-tier
  gets 403 with no file written, idempotent on an already-existing
  note).
- `web/src/lib/components/DailyNote.test.ts` (+4 tests): empty state
  renders on 404 instead of error text; viewing a 404'd date performs
  no write (`createDailyNote` never called); clicking "Start today's
  note" calls `createDailyNote` with the right date/KB.
- Full suites green: 3107 backend tests passed (68 skipped), 382
  frontend unit tests passed, frontend build succeeds.

## Acceptance criteria

- [x] Navigating to any Daily Notes date performs zero writes for a
  sub-write-tier caller.
- [x] A read-tier user browsing Daily Notes triggers no permission
  errors (gets a 404-backed empty state, not a 403) and creates no
  entries.
