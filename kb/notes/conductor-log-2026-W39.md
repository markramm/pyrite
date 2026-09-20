---
id: conductor-log-2026-W39
type: note
title: "Conductor log 2026-W39"
tags: [conductor, log]
---

The week's tick log. Per the 2026-09-20 decision the full tick record lives in
the maintainer's desk (`pyrite-desk`, gitignored); this file carries a pointer
per tick plus anything the public repo should keep.

## Tick 2026-09-20T00:05Z — release triage, two dispatches, outside PR sweep

Full record: `pyrite get tick-2026-09-20T0005-release-triage -k pyrite-desk`.

**Dispatched.** Two workers, within the machine budget (load 1.28, 70% free):
`fix/13-writes-never-block-on-embedding` (Opus — server/storage, design-shaped,
implements the now-landed ADR-0035) and `docs/contributor-facing-pass` (Sonnet).

**ADR-0035 was stranded.** It is `status: accepted` and dated 2026-09-19, but
it lived only on the unmerged W38 log branch, so the worker dispatched to
implement it could not read it. PR #70 was flipped and merged to land it (and
the ADR-0033 amendment) on `dev`. A decision that exists only on a branch is
not yet a decision anyone can act on — worth a process note.

**Release triage — what 0.24.2 still owes.** The milestone holds exactly one
open issue, #13, now dispatched. But three issues found *after* the milestone
was drawn are arguably must-haves, and none are in it:

- **#201 — MCP over HTTP has no per-KB read scoping.** The `/mcp` mount is the
  one KB-content surface with no scoping at all; a caller with any read-tier
  credential reaches private-KB content that the REST routes correctly 404.
  This is the same class as #180, which shipped tonight as a security fix. The
  per-tier server cache (`mcp_routes.py:150`) means it cannot be fixed by
  adding a dependency per request. **Shipping a release that fixes the REST
  leak and leaves the MCP one open is the part worth thinking about.**
- **#207 — concurrent first writes segfault.** `_MODEL_CACHE_LOCK`
  (`embedding_service.py:198-225`) guards the cache read and write but not the
  `SentenceTransformer(...)` construction, so N concurrent first calls build N
  models and torch is not safe under that. Found by the #203 cold read;
  pre-existing. #13's fix removes the likeliest *trigger* (the write path) but
  not the bug — `_get_model` stays reachable from search and `index embed`.
- **#186 — read scoping part 2** (`links.py` secondary-KB parameters), the
  explicitly-named remainder of the #180 work.

**Outside PR sweep.** Seven open; the constraint is the maintainer, not the
contributors:

- **#214 arrived mid-tick fixing #213** — the same two files the docs worker
  was editing. The worker was stopped on #213 and rescoped to #212 plus the
  AI-declaration paragraph. Outside work takes precedence; a contributor
  fixing a thing we filed is the system working.
- **#177 and #175**: both verified green merged with current `dev` (5210 and
  5215 passed). Both blocked on `CHANGELOG.md` adjacency alone.
- **#184, #177, #198 sit at `action_required`** — their CI has never run,
  because GitHub holds first-time contributors' workflows for maintainer
  approval. Three PRs blocked on one click only the maintainer can make.
- **#198 closed**: a stake file whose own text says "do not merge stake-only
  as complete", which CONTRIBUTING forbids by name. Closed warmly with the
  documented way to claim #192 instead.

**The release cannot be cut yet, and the script says so precisely.**
`scripts/release.py 0.24.2` (dry run, its default) failed three preconditions
in sequence, each correctly: a dirty checkout (an untracked `Claude outputs/`
directory, the maintainer's hallway-test reports — not gitignored), then HEAD
not equal to `origin/dev`, then `pyproject.toml` at 0.24.1. That is the
release-prep commit, which is delegated work, not a defect.
