---
id: multi-user-security-review-threat-model-surface-audits-live-personas-and-a-structural-guard
title: 'Multi-user security review: threat model, per-surface audits, live multi-persona testing, and a structural authorization guard'
type: backlog_item
kind: epic
tags:
- security
- multi-user
status: proposed
priority: high
effort: L
---

## Why (maintainer, 2026-09-23)

The multi-user path has had little manual testing, and the automated tests are
not catching everything. On 2026-09-23 a worker securing `/ws` (#218) found
that with auth enabled and no API keys configured, **any** `X-API-Key` or
`Bearer` value was answered "admin" on REST and `/mcp`. Every release from
v0.6.0 through v0.25.0 is affected. The conductor confirmed an anonymous
visitor could list, read and write private KBs. The fix
(`fix/api-key-role-requires-configured-keys`) also exposed a second bug:
`/mcp` session auth crashed.

Before this, 0.25 had already fixed read scoping across six extensions, `/ws`
(#218) and export paths (#221). Each was found one at a time.

## When

**After** the in-flight security fixes land: the key-role fix, #323 (`/ws`)
and #324 (export paths). The review should audit current code, not a moving
target (maintainer's call).

## Shape

1. **Threat model**: one Opus pass, read-only.
   - **Actors:** anonymous visitor, registered user, user with a KB grant, KB
     admin, instance admin, operator API key, and an outside contributor's PR
     (see `outside-prs-screen-before-anything-runs-review-after-ci-one-daily-routine`).
   - **Assets:** private KB content, write access, the server filesystem,
     stored GitHub tokens, sessions.
   - **Entry points:** REST routes, ~120 MCP tools (core and extensions),
     `/ws`, `/auth/*`, export/import, git and GitHub operations, and the
     clipper's URL fetch (SSRF).
   - **Output:** a threat-model document in `kb/designs/`, and the audit
     briefs below.
2. **Per-surface audits**: read-only reviewers, one surface each, taking no
   suite slots.
   - Authentication: sessions, cookies, CSRF, registration, API keys.
   - Authorization of every route and tool, **writes especially**. Reads were
     made structural in 0.25; writes still use per-endpoint checks.
   - Paths and injection: export/import, git, templates, FTS queries.
   - Outbound requests: SSRF through the clipper and the GitHub integration.
   - Extension tools.
   - Triage of the 56 open CodeQL alerts
     (`codeql-triage-and-close-the-56-open-code-scanning-alerts-on-dev`).

   **Every finding needs a reproduction on `dev`, or it is not a finding.**
3. **Live multi-persona testing**: `pyrite-explorer` against a live server
   with auth enabled. Three personas each try to reach the others' private
   KBs through the UI and the API. This takes two suite slots; nothing else
   heavy runs beside it.
4. **Structural guard**: extend `tests/test_read_scoping_is_structural.py` to
   writes and to authentication. The test enumerates every REST route and MCP
   tool, and fails when one lacks a covering read **and** write authorization
   test, so a new route cannot ship unguarded.

## Acceptance

- A threat-model document and a findings document in `kb/`. Each finding is
  reproduced, has a severity, and has a disposition: fixed, issue, or
  accepted with a reason.
- Exploitable findings are fixed forward (alpha; maintainer 2026-09-23), with
  regression tests that fail without the fix. Hardening items go in as issues.
- The structural guard is on `dev`.
- The README states the multi-user status honestly, e.g. "multi-user: alpha,
  security-reviewed <date>, known gaps: <list>".

## Groom 2026-09-26

Read on `dev` e0a6ae11 (ADR-0037 theme 3a, #508, merged). Nothing was run
except reading the tests' own constants. In flight and not re-groomed here:
#509 (safe error messages), #511 (a test leak), #440 (SQLite transaction
mode). ADR-0037 themes 3b–5 are 0.27 (maintainer, 2026-09-25).

**Handling rule for every theme below.** A reproduced exploitable finding
is reported to the conductor only. It is never written into a GitHub issue,
comment or label, a public KB entry, a test name or allowlist, or a PR
body, until its fix is released; the conductor routes it under the
security-brief rule. Hardening that is not exploitable may become an
ordinary backlog item. Fix themes are created per finding by that route and
are not groomed here.

### The structural-guard gap, measured

The DoD asks for a guard that "enumerates every REST route and MCP tool and
fails when one lacks a covering read **and** write authorization test".
What exists on `dev`:

- **3a's guard** (`tests/test_every_entry_point_passes_the_policy.py`)
  checks a *declaration*: every REST operation has exactly one
  `authz.authorize(...)` in its dependant tree, and an MCP handler is
  reached only through `_dispatch_tool`. It does not check any behaviour
  (the ADR itself says a wrong action passes the presence check). For
  writes in 0.26 it enforces nothing:
  - `REST_NOT_YET_MIGRATED` holds 68 operations: every per-KB write route
    and every instance, user, self and capability route;
  - `REST_WRITE_TIER_NOT_YET_MIGRATED` holds 10 more, whose write half is
    still an inline or `requires_tier` check;
  - `MCP_NOT_YET_MIGRATED` holds all 112 tools.
  These lists empty only in themes 3b, 3c and 4, which are 0.27.
- **Theme 0's harness** (`tests/characterization/`) is behavioural. It
  covers 74 REST operations and 106 MCP tools × 7 principals × 4 KB states,
  and a completeness test that every route and tool is either
  characterized or excluded. But:
  1. **It has no oracle.** Each case is compared with a golden recorded
     from today's code. A golden that records a wrong answer passes. The
     ADR's §5.4 ("the case asserts the transport's answer equals what
     `authorize` says for the declared action") is not implemented anywhere.
  2. **No principal can be allowed a per-KB write.** The seven are
     `anonymous`, `local_user`, `global_user` (global role read),
     `granted_user` (a *read* grant on `PRIVATE`), and the three operator
     keys. §5.4's write grant, KB-admin grant and instance-admin session are
     missing. So the allowed side of a per-KB write, a write grant on one KB
     used against another KB, and KB-admin on `/permissions` are never
     exercised by a session principal. The only callers that can write are
     unscoped operator keys.
  3. **75 entry points have no principal matrix.** They are excluded with a
     reason (`REST_ACCESS_EXCLUSIONS` 69, `MCP_ACCESS_EXCLUSIONS` 6):
     `/auth/*`, `/auth/users*`, settings, the merge queue, KB
     administration, the registry tools. What covers them is
     `test_api_authorization_coverage.py`, which checks only that a
     read-tier *key* is refused on mutating routes, plus a few per-feature
     suites.

**The gap in one line:** nothing fails when a route or tool answers a
principal differently from what the policy says, and nothing enumerates
the write-allowed or instance-scoped cases at all. Theme G1 below closes it
without waiting for 3b–5. Whether 0.26 needs G1 is a maintainer question
(see "Decisions needed"): decision 4 of 2026-09-25 named "the §5 guard with
a shrinking allowlist", and §5.4 is part of §5.

### Dispatch order

| # | Theme | Kind | Model | heavy | Cold read | After |
|---|---|---|---|---|---|---|
| T1 | Threat model and audit briefs | spike → kb PR | opus | no | yes | now |
| G1 | Authorization oracle: every entry point × principal checked against the policy | worker → PR | opus | no | yes | #509 merged; maintainer yes |
| L0 | The persona world: a seeded, auth-enabled live server | worker → PR | sonnet | yes (live server) | no | now |
| A1–A8 | Per-surface audits | spikes → findings + tickets | opus | no | n/a (read-only) | T1 |
| L1 | Live three-persona session | explorer run, no PR | inherit (opus) | yes (2 slots, alone) | n/a | L0, T1, A1 and A2 reported |
| D1 | Security disposition sweep | worker → kb PR | sonnet | no | no | A1–A8, L1 |
| R1 | README honest multi-user status | worker → PR | sonnet | no | maintainer reads wording | D1 |

T1, G1 and L0 have disjoint footprints and can run together. The audits
take no suite slots and can run several at once. L1 runs with nothing else
heavy, and not beside #419's Playwright slot.

### T1 — Threat model and audit briefs — model: opus — heavy: no — cold read: yes

Acceptance (from this item's Shape 1 and Acceptance, merged):
- A threat-model document in `kb/designs/` covering:
  - **actors:** anonymous visitor, registered user, user with a KB grant,
    KB admin, instance admin, operator API key, an outside contributor's
    PR, and a KB whose files come from a subscribed or forked repo;
  - **assets:** private KB content, write access, the server filesystem,
    stored GitHub tokens, sessions;
  - **entry points:** taken from `tests/_surface_inventory.py`, not by
    hand. That covers REST, MCP (core and extensions), `/mcp` transports,
    `/ws`, `/site`, `/auth/*`, export/import, git and GitHub operations, the
    clipper's fetch and the CLI.
- For each entry-point class, the trust boundary and the property that
  must hold, stated as a property, not as attack steps.
- One audit brief per surface A1–A8, written into this item as a
  `## Audit briefs` section. Each brief says what to read, the questions
  to answer, and the time box.
- It builds on `kb/designs/hosting-security-requirements.md` and ADR-0037.
  It does not restate them.

Touches: existing: this item (briefs section). New:
`kb/designs/multi-user-threat-model.md`.
Sequence: first; independent of G1 and L0.
Cold read: yes. A `pyrite-reviewer` checks that the entry-point list
matches the inventory and that no attack steps are written down.
Out of scope: findings, reproductions, fixes, and any claim about current
code being vulnerable (that is what the audits do).

### G1 — Authorization oracle — model: opus — heavy: no — cold read: yes — closes the DoD guard clause

Acceptance:
- The characterization world gains the three principals §5.4 names and
  lacks: a user with a write grant, a user with a KB-admin grant, and an
  instance-admin session. It also gains a second private KB, so that a
  grant on one KB used against another is a case. The regenerated goldens
  are their own commit, and that commit only adds keys.
- A new test enumerates **every** entry point in
  `tests/_surface_inventory.py`: every REST operation including `/auth/*`,
  every MCP tool at the admin tier, core and extension, and `/ws`. It fails
  for any entry point that has neither of these:
  - an expected `(Action, Resource)` in a test-side table, with the
    `Action` vocabulary taken from `access_policy.py`; or
  - a `PUBLIC_ENTRY_POINTS` reason.
  This is the "covering read **and** write test" the DoD asks for: a
  mutating entry point's expectation must be a write, admin or capability
  action, never `KB_READ`, unless it is on 3a's `REST_READS_OVER_POST`.
- For each entry point, principal and KB state (or `Instance`/`User` for
  the excluded 75), the test compares the answer's class with
  `AccessPolicy.authorize(principal, action, resource)`:
  - allowed;
  - 401;
  - 403;
  - concealed 404, with a byte-identical body to a missing KB.
- A divergence **toward refusal** (the code refuses where the policy would
  allow) may be pinned in a list that can only shrink, each entry with a
  reason. A divergence **toward access** is never pinned. It is reported
  to the conductor under the handling rule above, and G1 does not merge
  while one is open.
- Where 3a has declared an action, the test also asserts that the table
  agrees with the declaration. 3b, 3c and 4 (0.27) replace table rows with
  declarations, and the table shrinks to nothing.
- The whole module runs in one module-scoped world, as theme 0 does, inside
  the pre-push budget at `-n 4`. Record the wall time in the PR.

Touches: existing: `tests/characterization/world.py`,
`tests/characterization/goldens/*` (additions only),
`tests/characterization/rest_calls.py` and `mcp_calls.py` (calls for the
excluded 75), and `tests/_surface_inventory.py` if an entry point is
missing from it. New: `tests/test_every_entry_point_answers_as_the_policy_says.py`
(or a section of 3a's guard file, as the worker judges; one file, not
both).
Sequence: after #509 merges, because #509 edits
`tests/characterization/conftest.py` and the goldens. It is independent of
T1 and L0. Merge it before D1, since its divergences feed the sweep.
Cold read: yes. It is the DoD's guard, and a wrong expectation table would
bless a hole.
Out of scope: migrating any route to `authorize` (that is 3b/3c/4, 0.27);
fixing any divergence, since each fix is its own theme; the §5.3 grep
ratchet (theme 5); a CLI principal matrix (the CLI is `Principal.local`).

### L0 — The persona world — model: sonnet — heavy: yes — cold read: no

Acceptance:
- One command starts `pyrite-server` with auth enabled, on a per-worktree
  port and a scratch data dir (as `web/e2e/ports.ts` derives them), and
  seeds it through the real admin paths: `pyrite-admin user create` for
  the instance admin, then REST for KBs, default roles and grants. It
  prints the base URL and each persona's credentials to a file outside the
  repo.
- The world holds:
  - **alice**: owns private KB `alpha`, and has a write grant on `shared`;
  - **bob**: self-registered with an invite, owns private KB `beta`, and
    has a read grant on `shared`;
  - **mallory**: self-registered, with no grants;
  - the anonymous visitor;
  - an operator read key.
  Each KB is seeded with entries whose titles name their KB, so a leak is
  visible on sight.
- It stops cleanly and leaves no process behind.
- A runbook explains how to start, reset and stop it.

Touches: new: `scripts/persona-world` (script), `kb/runbooks/live-persona-security-test.md`.
Existing: none, except reusing `web/e2e/ports.ts`'s derivation, read only.
Sequence: independent; now.
Cold read: no. Test scaffolding, no production change.
Out of scope: Playwright specs; any assertion about what personas can
reach (that is L1); changing `pyrite-admin` to add grant commands.

### A1–A8 — Per-surface audits — spikes — model: opus — heavy: no

Each is a `pyrite-spike`, read-only, time-boxed. Each finding must have a
reproduction on `dev` as a single failing test or a request sequence run
alone (no suites). What each spike delivers:
- (a) findings, to the conductor only, under the handling rule;
- (b) hardening items, as backlog items;
- (c) "no finding" per question, with the evidence.

None of them is a worker, and none opens a PR. A fix is a separate theme.
The questions come from T1's brief. The starting footprint:

- **A1 REST authorization, writes first.** The checklist is 3a's
  `REST_NOT_YET_MIGRATED` (68), `REST_WRITE_TIER_NOT_YET_MIGRATED` (10)
  and the 8 `INLINE_ACCESS_DECIDING_ROUTES`. Row-resolved writes, bulk and
  import bodies that name several KBs, the worktree resolver branch in
  `entries.py`, `daily.py`, `repos.py`, `settings_ep.py`, `admin.py`
  grant/revoke. The roadmap's note that REST ignores `Bearer <valid key>`.
- **A2 MCP.** All 112 tools. `_dispatch_tool`, `writable_kbs` on every
  write-tier tool, including the extension write tools (investigation,
  social, zettelkasten, software-kb). `mcp_routes._authenticate`, and the
  `POST /mcp/messages/` session-id trust the roadmap records. Tool
  arguments treated as untrusted: the manual stand-in for #228 until
  CodeQL can see them.
- **A3 CLI.** `Principal.local` by assumption. `pyrite-admin` run as root
  in Docker (see #405). What a KB's own files make the CLI or server
  execute, render or fetch when that KB comes from a subscribed or forked
  repo: `hook_runner.py`, templates, `kb.yaml`, `file_pattern`.
- **A4 `/ws` and `/site`.** The two surfaces outside the `/api` dependency
  tree.
  - `/ws`: events now actually deliver since #326. Check event payload
    scoping, connect authentication, and scope lifetime under ADR-0036.
  - `/site`: on `PUBLIC_ENTRY_POINTS` as "a pre-rendered public cache".
    Check which KBs the render includes, and the path handling in
    `static.py` and `site_cache.py`.
- **A5 Authentication flows.**
  - Sessions and cookie flags, expiry, and invalidation at logout and on
    role change.
  - CSRF on cookie-authenticated mutating routes.
  - Registration and invite codes.
  - API-key hashing and comparison.
  - OAuth state, and GitHub token storage.
  - `auth_rate_limit.py`.
  - The login event-loop stall (#440).
  Files: `auth_endpoints.py`, `auth_service.py`, `api.py`
  (`verify_api_key`), `github_auth.py`, `oauth_providers.py`,
  `user_service.py`, `credential_events.py`.
- **A6 The write path: what a permitted write can reach.** Containment of
  every file the services write. The joins in:
  - `export_service`, `template_service`, `site_cache`, a collection's
    `folder_path`, and the repo clone path;
  - NUL, overlong and drive-relative names, and symlinks out of a KB;
  - `entries/import`;
  - `git_service` arguments;
  - `worktree_service`, `ephemeral_service`;
  - delete precision after ADR-0038 step 1.
- **A7 Outbound requests.** SSRF through `clipper.py` and `url_checker.py`
  (the open items are in
  `web-clipper-response-size-cap-and-dns-rebinding-toctou-defense-r1300-follow-ups`).
  Clone and subscribe URLs and their schemes in `repo_service`. Any
  settings-controlled base URL (LLM, GitHub) that a non-admin can set.
- **A8 CodeQL triage.** This is the spike
  `codeql-triage-and-close-the-56-open-code-scanning-alerts-on-dev`
  already defines; its output goes into that item. It runs after #509
  merges, since #509 addresses the stack-trace-exposure class. Dismissing
  alerts on GitHub is the conductor's action, taken from the spike's
  table.

Sequence: after T1 (the briefs). Otherwise independent; the conductor may
run several at once. A1 and A2 report before L1, so L1 can probe their
hypotheses.
Out of scope: writing fixes; ADR-0037 migrations; a repo-egress capability
split (`repo-access-is-a-capability-not-a-tier`, ADR-0031).

### L1 — Live three-persona session — pyrite-explorer — heavy: yes (two slots, nothing else heavy)

Acceptance:
- Against L0's world, `pyrite-explorer` is run once per persona (alice,
  bob, mallory), and then once as the anonymous visitor. Each run tries to
  reach the other personas' private KBs:
  - through the UI: navigation, search, graph, timeline, daily notes,
    export, the entry editor, settings;
  - through the API with `curl`, using its own session cookie or key:
    REST, `/mcp`, `/ws`, `/site`.
- Each run tries both reads and writes, including a write into `shared` by
  bob (read grant only).
- The brief overrides the agent's default output: findings go to the
  conductor only, never to an issue.
- "Worked as promised" lines become the regression list that D1 records.
Touches: none; no PR. The session log stays with the conductor.
Sequence: after L0 and T1; after A1 and A2 have reported. Not beside #419
or any other Playwright run.
Out of scope: writing Playwright specs (they can be suggested); fixing
anything.

### D1 — Security disposition sweep — model: sonnet — heavy: no — cold read: no

Acceptance:
- Every item tagged `security` in `kb/backlog/` (14 on 2026-09-26) has a
  disposition: fixed (with the PR), scheduled (with the milestone), or
  accepted (with the reason).
- The same holds for the open GitHub issues that are security-adjacent
  (#228 today).
- Stale statuses are reconciled. For example:
  - `authenticate-and-scope-ws-218` and
    `export-and-site-renderers-turn-stored-entry-type-and-id-into-safe-path-segments`
    are still `review`, though #323 and #324 merged;
  - `adr-0037-theme-1-access-policy-module-383` is `in_progress`, though
    theme 1 landed;
  - `auth-service-typed-exceptions` and `unify-rest-mcp-error-response-shape`
    need checking against ADR-0037 theme 2.
- The findings document this item's Acceptance asks for is written,
  containing only what the handling rule allows to be public.
- The hardening items from A1–A8, G1 and L1 are linked from this item.
Touches: existing: `kb/backlog/*.md` (status and disposition lines only),
this item. New: `kb/designs/multi-user-security-review-findings.md`.
Sequence: after A1–A8, L1 and G1.
Out of scope: creating a `security` label or any GitHub issue (see
Decisions); fixing anything.

### R1 — README honest multi-user status — model: sonnet — heavy: no — cold read: maintainer reads the wording

Acceptance:
- The README states "multi-user: alpha, security-reviewed <date>, known
  gaps: <list>".
- Known gaps come only from D1's public dispositions. They include the
  structural ones: writes authorized per route until ADR-0037 3b/3c, and
  MCP tools not yet declared (theme 4).
- `docs/configuration.md`'s "Authentication (multi-user)" section and
  `SECURITY.md` link to it and do not contradict it.
Touches: existing: `README.md` (Deploy section, or a short status line
near the top), `docs/configuration.md`, `SECURITY.md`.
Sequence: last, after D1.
Out of scope: rewriting the README opening
(`reposition-the-readme-opening-and-pyrite-wiki-around-agent-written-human-verified-knowledge`);
deploy docs.

### Decisions needed (maintainer)

1. **Does the DoD guard need G1 in 0.26?** Theme 3a plus the goldens do not
   meet "a covering read **and** write authorization test", for the three
   reasons above. The recommendation is yes. Otherwise, reword the DoD to
   "3a's guard, with its shrinking lists" and move G1 to 0.27.
2. **Where does the findings document live, and when is it published?**
   The Acceptance puts it in `kb/`, which is public. The security-brief
   rule keeps unfixed findings private. The proposal is that D1 writes the
   public document after the fixes are released, and before then only
   counts and structural gaps appear.
3. **There is no `security` label on `pyrite-wiki/pyrite`.** The repo has
   26 labels and none is `security`. So the DoD's "no open issue labelled
   `security` lacks a disposition" is vacuously true. The proposal is to
   reword it to "no `security`-tagged backlog item or security-adjacent
   issue lacks a disposition", and not to create a public label that would
   point at open problems.
4. **#228 / `codeql-models-pyrites-non-web-input-surfaces`.** Seeing MCP
   arguments as tainted requires moving CodeQL from default setup to
   advanced setup, a workflow the project then owns. Until that is
   decided, A2 covers it by reading.

### Remaining milestone issues

- **#405 (config saves are crash-safe): next.** It is groomed (2026-09-25:
  opus, heavy, cold read). Its footprint (`config.py`, `utils/yaml.py`) is
  shared with nothing above. No spike is needed.
- **#419 (QueuePool exhaustion under the seed spec): after #440 merges.**
  Both touch the per-request DB and SQLite connection lifecycle. It takes
  a Playwright slot, so it must not run beside L1. No spike is needed: the
  2026-09-25 groom's hypothesis is strong, and the worker confirms the
  mechanism before fixing it.
- **#244 (`.claude/` by audience): dispatchable when the maintainer
  confirms the loop runs from `tcp-skills`.** Its #393 gate has cleared
  (merged 2026-09-25). It is a docs/process change, not on the security
  path. No spike is needed.
