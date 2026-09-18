---
id: roadmap
title: Pyrite Release Roadmap
type: note
tags:
- roadmap
- planning
---

# Pyrite Release Roadmap

## Thesis: agents write, humans verify

Agents produce knowledge faster than people can review it, so human review
attention is the constraint (ADR-0019, Theory of Constraints). Pyrite's job is
to make agent-written knowledge **verifiable**: typed entries, git provenance
down to the commit that introduced a claim, tiered write access, a review
queue, and a UI whose first purpose is oversight of agent work. It was built in
an investigative newsroom, where that property is not optional.

This replaces the earlier "self-configuring infrastructure for agent swarms"
framing (2026-09-17; the old vision doc is kept at
[[bhag-self-configuring-knowledge-infrastructure]]). Autonomous provisioning
may still happen; it is downstream of trust, not the goal.

Every milestone below is judged by one question: does it make agent-written
knowledge easier to trust, for its operator first and for invited readers next?

---

## 0.3 — CLI Foundation (done)

Core CLI, storage layer, service architecture, plugin system (15-method protocol), three-tier MCP server, SvelteKit web UI, content negotiation, collections (phases 1-3, 5), block references (phases 1-2), background embedding pipeline, REST API tier enforcement. 1040 tests.

## 0.4 — MCP Server Hardening (done)

Production-solid MCP for agent workflows. Fixed metadata passthrough bugs, added capture lane validation (`allow_other` on FieldSchema), schema validation on all write paths. 1040 tests.

## 0.5 — QA & Agent CLI (done)

QAService with 9 structural validation rules. `--format json/markdown/csv/yaml` on 11 CLI commands. `pyrite init --template`, `pyrite extension init/install/list/uninstall`. 1086 tests.

## 0.6 — Agent Coordination (done)

Task plugin (7-state workflow, atomic `task_claim` via CAS, `task_decompose`, `task_checkpoint`). Plugin KB-type scoping. Programmatic schema provisioning. QA Phase 2 (assessment entries, post-save validation). 1154 tests.

## 0.7 — Web UI Polish (done)

QA dashboard, graph betweenness centrality, block-ID transclusions, collection embedding in transclusions, WebSocket live updates, cycle detection, transclusion view options, collection nesting. 1000+ entry performance test. 1179 backend + 115 frontend tests.

## 0.8 — UI Design & UX (done)

Brand identity (gold accent, DM Serif Display, "Py" monogram). Dashboard redesign with type distribution chart. Dedicated `/search` page. Responsive sidebar. Keyboard shortcuts modal. Template picker redesign. Page transitions. 1182 backend + 115 frontend tests.

## 0.9 — Code Hardening (done)

Internal quality pass across 8 waves. Key results: `mcp_server.py` 32% smaller (tool schemas extracted), `WikilinkService` extracted from `KBService`, 24 `_raw_conn` calls eliminated, 43 bare `except: pass` replaced with logging, SQL DDL injection prevention, stale `docs/` directory deleted. 1654 backend + 115 frontend tests.

---

## 0.10 — SearchBackend Protocol + PostgresBackend (done)

**Theme:** Pluggable storage backends via a clean protocol abstraction. See [ADR-0014](adrs/0014-structural-protocols-for-extension-types.md) (structural protocols), [ADR-0015](adrs/0015-odm-layer-and-schema-migration.md) (ODM architecture), [ADR-0016](adrs/0016-lancedb-evaluation.md) (LanceDB evaluation).

### Delivered

- **SearchBackend protocol** — 13-method structural protocol in `pyrite/storage/backends/protocol.py`, 66 conformance tests
- **SQLiteBackend** — wraps existing PyriteDB + FTS5 + sqlite-vec (default, local/single-user)
- **PostgresBackend** — tsvector + pgvector, 66/66 conformance tests (~3x indexing, ~2x query overhead vs SQLite — acceptable for server deployments)
- **LanceDB evaluated and rejected** — 49-66x slower indexing, 60-280x slower queries, 25-54x larger disk. See ADR-0016.

---

## 0.11 — ODM Completion (done)

Schema versioning (`_schema_version` tracking, `since_version` field semantics, `MigrationRegistry`, `pyrite schema migrate`). DocumentManager for write-path coordination. Architecture hardening (DDL validation, MCP constants extraction). Test infrastructure (pytest-xdist, extension tests). Docs KB fixes. 1505 tests.

---

## 0.12 — Distribution (done)

PyPI publish, version bump, MANIFEST.in, publish workflow, CHANGELOG, README.

Remaining loose ends (no version bump needed):
- PyPI trusted publisher setup (XS, manual step)
- [[mcp-submission-update]] (#89, XS)

---

## 0.13 — Human & Agent UX Hardening (done)

Web UI hardening (14 items: logout, version history, type colors, page titles, dead code, loading states, accessibility, mobile responsive, collections save, first-run experience, starred entries, full accessibility audit, Playwright tests, review hardening). Agent DX (8 items: PosixPath fix, batch-read, list-entries, kb_recent, search fields, smart field routing, structured errors, file placement fix).

---

## 0.14 — Auth & Rate Limiting (done)

GitHub OAuth login, per-KB read/write/admin permissions, MCP rate limiting.

---

## 0.15 — Deployment & Demo (done)

Docker/Compose, deploy buttons (Railway/Render/Fly.io), pyrite.wiki website, demo site deployment, BYOK AI gap analysis, final UI review.

---

## 0.16 — Ecosystem & Onboarding (done)

Getting Started tutorial, plugin writing tutorial, awesome plugins page, `pyrite ci` command, personal-kb-repo-backing, one-click deploy configs, alpha banner, OpenAI/Gemini MCP integration docs.

---

## 0.17 — Cleanup & Hardening (done)

Bug fixes (entry ID collisions, priority type mismatch, date field reads, status field reads). Reliability (API singletons, plugin hook atomicity, plugin discovery strict mode). Developer experience (MCP body truncation docs, embedding prewarm, import cycle detection, KB compaction, schema validation CLI, plugin registry dedup, factory open/closed, component documentation gaps).

---

## 0.18 — Architecture & Ecosystem (done)

KBService decomposition (extracted GraphService, EphemeralKBService, QuotaService, ExportService). Schema module decomposition. SearchService/KBService overlap resolution. Dynamic subdirectory paths. Reserved field validation. Software-kb plugin. Journalism-investigation plugin. Edge entities (typed relationships as first-class entities). Entry lifecycle and search filtering. DB backup/restore. Kanban workflow for agent teams. Export system (NotebookLM + Quartz renderers).

---

## 0.20.0 — First Public Release

**Theme:** Release readiness. Version bump, CHANGELOG, documentation accuracy, lint cleanup. No new features — polish and ship.

---

## 0.21–0.24 — Shipped between milestones (reconciliation note, 2026-07-02)

Versions 0.21.0 through 0.24.0 were tagged without roadmap or CHANGELOG
entries (CHANGELOG stops at 0.20.0). Highlights recoverable from git:
Tier-A agent-CLI features (`pyrite rename` + wikilink rewrite, `qa
coverage` curation stats), the CLI error-shape consistency sweep (0
ad-hoc sites CLI-wide), `task reset` for stale claims, FTS5 term quoting
in links suggest/discover (fixed the `links orphans` crash), and the
`all_kbs()` enumeration fix for DB-registered KBs. Backfill CHANGELOG as
part of 0.25.

---

## 0.24.1 — First GitHub release (shipped 2026-09-17)

Five months of hardening. Security fixes (token disclosure, git argument
injection, unguarded routes, stored XSS, path traversal through entry ids),
the error-handling contract, MCP tools that failed on every call, create no
longer overwrites, fast commit hooks with the suite at pre-push, CI as the
gate. Installable from the tag with `pip install "pyrite[all] @ git+…@v0.24.1"`
— CLI, REST and MCP work; the web UI is not packaged yet. Release notes in
CHANGELOG. Process decisions: ADR-0032 (branch flow), ADR-0033 (where work is
tracked: bugs and requests on GitHub, roadmap here).

---

## 0.24.2 — Operational (next; target ~3 weeks)

**Theme:** a release should be an unremarkable event, and the tool should be
boring for its operator. No new product surface. Definition of done: the
release is cut by one script from a CI-verified commit under ADR-0032's rules,
and every GitHub issue in the 0.24.2 milestone is closed.

**How this list was chosen:** GitHub issues #9–#21 (the migrated bugs) plus the
2026-09-17 review's process findings. Under ADR-0033, "what is broken" lives in
GitHub — when working toward a release, check `gh issue list --milestone` and
`gh pr list` as well as this file.

### Workstream 1 — Release process, operationalized

- ~~[[make-the-task-claim-concurrency-test-xdist-safe-then-run-pre-push-with-n-auto]]~~
  **done 2026-09-17**: `-n auto` at pre-push and in CI; suite 3m37s → ~45 s
  locally once write-time embedding was switched off for tests (it was the
  whole cost); CI Python jobs 22 min → ~2.5 min tests + 20 s uv install.
- ~~CI change classifier~~ **done 2026-09-17**: `changes` job; test/frontend/
  coverage skip for docs/KB-only pushes; `kb` job validates KB changes in
  ~30 s; coverage in its own non-required job; e2e on `main` and by hand only.
  Auto-merge for KB PRs still to enable (repo setting, with protections).
- Branch protection on per ADR-0032: `dev` and `main` require the three Python
  jobs + `frontend`, up to date, no bypass; linear history; `v*` tags protected;
  Dependabot security updates and private vulnerability reporting enabled.
- `scripts/release.py` — one command: checks CHANGELOG `[Unreleased]` and
  version, waits for CI on the SHA, fast-forwards `main`, tags, creates the
  GitHub release from the changelog, installs from the tag into a clean venv
  and runs the Quick Start. (v0.24.1 took ten manual steps.)
- ~~[[live-server-integration-tests-for-multi-request-flows-plus-regression-tests-for-the-three-outside-prs]]~~
  **done 2026-09-18**: `tests/e2e/` starts `pyrite-server` on a free port
  against a temp data dir and drives it as a client — REST (create a KB, write
  into it, find it, no restart), MCP over SSE (the advertised endpoint path,
  then a full session), MCP over stdio (`pyrite mcp --tier read`), and startup
  prewarm read from `/health`. Each of PRs #3, #4 and #5, reintroduced by hand,
  fails its test while the existing 3316 do not notice.
- Post-tag workflow: install from the tag, run the Quick Start, build the Docker
  image (unverifiable locally on 2026-09-17).
- [[ci-parity-lint-extensions-and-enforce-the-fix-needs-a-test-rule]] (medium, S).
- [[single-source-of-truth-for-the-version-asserted-by-a-test]] — finish:
  `[Unreleased]` discipline asserted by the test.
- Session setup script (worktree + venv + hooks) so ADR-0032's one-branch-per-
  session rule is one command.
- **Every interface has an end-to-end test in CI** (added 2026-09-17):
  - ~~REST and MCP over SSE~~ **done 2026-09-18** — the live-server ticket
    above. `tests/e2e/test_rest_flow.py`, `tests/e2e/test_mcp_sse.py`.
  - ~~**MCP over stdio**~~ **done 2026-09-18** — `tests/e2e/test_mcp_stdio.py`
    spawns `pyrite mcp --tier read` from the installed package and speaks
    JSON-RPC on stdin/stdout: `initialize`, `tools/list`, `kb_search`. Its
    tool list is asserted equal to the SSE one, so the two transports cannot
    drift.
  - ~~**CLI** — [[ci-run-getting-started-tutorial]]~~ **done 2026-09-18**:
    `scripts/run_tutorial.sh` extracts the fenced bash blocks from
    `docs/getting-started.md` and runs them in order in one shell session in a
    temp HOME, against the installed package. It found two real bugs on its
    first run: #43 (semantic search returns 0 on a fresh tutorial KB — nothing
    embeds on write) and #44 (`index health` reports `subdirectory_mismatches`
    on every entry of a correct KB; a trailing slash is not stripped). Both
    are why its assertions are one notch looser than the ticket asked for;
    the code names the TODO.
  - **Web** — [[playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap]]
    (high, M): make Playwright deterministic and blocking. Root cause still
    unconfirmed; if it proves large it slips to 0.25, and that is the only
    item on this list allowed to.

  All of the above run in the `smoke` CI job, gated on the push to `dev` and
  on manual dispatch — never on a pull request, and never in `gate`'s needs
  (ADR-0032 §3a's breadth row).

### Workstream 2 — Bugs (GitHub milestone `0.24.2`)

- **#15** `pyrite update` drops undeclared frontmatter keys — data loss, and it
  blocks tagging roadmap items with `milestone:`.
- **#14** writes accept off-enum field values.
- **#13** first write on a fresh install blocks on the model download.
- **#9** web: search results never render (the flagship flow on the demo).
- **#16, #17** entry-id slugs; **#18** `index health` exit code and `-k`;
  **#21** db backup path.
- ~~One security fix from the release review~~ **done 2026-09-18**: per-KB read
  scoping — private KBs (`default_role: none`) were readable by any logged-in
  or anonymous user on read routes; now 404 / filtered. Pilot prerequisite.

### Workstream 3 — Docs and README

- [[installable-from-github-with-a-working-web-ui-package-the-built-frontend]]
  (high, M) — `uv tool install "pyrite[server,cli] @ git+…@v0.24.2"` gives a
  working UI; README Quick Start leads with it.
- [[reposition-the-readme-opening-and-pyrite-wiki-around-agent-written-human-verified-knowledge]]
  (medium, M) — the README opening matches the thesis above.
- [[docs-counts-generated-or-asserted-from-code]] (medium, S).
- [[contributor-docs-pass-contributing-security-pr-template-credits]] (high, S).

### Pull-forward pool (added 2026-09-18)

The conductor loop finishes the list above; while it runs, well-specified
work that solves real user problems may be pulled into 0.24.2 so the process
gets feedback on more shapes of work. The maintainer's terms: "As long as
features are being developed and tested and our process is improving I do
not think it hurts to pull features and bugfixes and test improvements that
are well specified forward." The rule, which the meta-conductor may apply
without asking:

1. **Well-specified** — acceptance criteria a Sonnet worker could execute
   with no conversation (the `dispatch.md` test). The god-object splits are
   the deliberate exception: Opus, one object per PR, and the acceptance is
   "behaviour unchanged, proven by the existing suite plus a boundary test".
2. **Real** — closes a filed issue, removes a known data-loss or
   non-convergence bug, or is a test that would have caught one.
3. **Cheap to hold** — footprint disjoint from anything in flight; effort
   ≤ M, or L only for the splits below.
4. **Never displaces** — pulled only when fewer than three themes are in
   flight and every definition-of-done item above is claimed or done. The
   release ships when the definition of done is met; a pool item still open
   then rides on `dev` into the next release. Pulling forward must not
   lengthen 0.24.2.

| Theme | Closes | Shape / what it exercises |
|---|---|---|
| Index sync converges and health tells the truth | #6, #7, #8, #22, #19, #47 | Sonnet; a multi-issue theme with a storage cold read |
| Web first-visit fixes | #10, #11, #12 — [[web-kb-context-single-authority]], [[web-fix-dropped-kb-seams]], [[web-light-mode-chrome-repair]] | real UI change → explorer agent + Playwright fan-out; 0.25 pilot prerequisites |
| KB registry as one source of truth | [[collapse-kb-registry-to-one-source-of-truth]] | Opus, cross-cutting; root cause of the PR #4 bug class; first real cold-read test |
| Data-loss class, continued | #46 (`update --tags` rewrites frontmatter — found while tagging this pool), [[typed-entries-silently-drop-the-references-frontmatter-field]] | siblings of #15; the PR #35 write-path tests give them a home |
| Deploy path | #20 (Railway bind host/port) | small; pairs with the packaged web UI |
| God-object splits | [[split-the-remaining-god-objects-software-kb-plugin-kb-service-index-qa-service]], [[split-mcp-server-module]], [[split-entries-endpoint]] | Opus, one object per PR, sequenced; a different set of capabilities — large-diff review, behaviour-preserving refactor, the cold read at scale |
| MCP read-tier ergonomics (hallway test #56–#68, minus #56 which is milestone) | #57 #58 #59 #62 #64 #65 #66 #67 #68 | Sonnet mostly; the read tier is the agent surface, and the report's §2.12 says what not to touch (`kb/notes/hallway-test-read-tier-mcp-2026-09-18`) |
| MCP write-tier correctness (hallway test tier 2) | #95 `kb_bulk_create` not best-effort, #96 `add_type` overwrites silently, #97 `kb_link` accepts a missing target (the mechanism behind #64) | Sonnet; each has a reproduction and acceptance in the issue |
| CLI write-path integrity (CLI hallway test, `tests/usability/cli-hallway-report-2026-09-18.md`) | **#87** `link`/`update`/`create --link`/`links bulk-create` write frontmatter that no longer parses when the body has a `\|---\|` or `---` line, exit 0 — milestone; #48 cascade validator never called; #51 `parked_awaiting` lost from the index; #54 search output shape; #52 `task status` deprecation invisible | #87 is the same serialization fault as #46/#86 seen from the link step — one theme with #69's follow-up, Opus; the rest Sonnet. Report's "if only three things": the link step, `filters_dropped` on every search response, `--dry-run` on `link` and `update` |
| Quality pool for the retro (tagged `quality`) | [[tests-leak-open-pyritedb-connections-into-temporarydirectory-teardown]], [[worktree-no-lost-commits-invariant]], [[index-rebuild-from-files-equivalence-test]], [[regression-test-links-fts-quoting]], [[cli-output-is-inconsistent-when-stdout-is-not-a-tty]] | Sonnet; pre-groomed stock so the retro's quality theme has candidates before it has evidence of its own |

Left out on purpose: the JI UI features and the review surface (0.26 — the
thesis screen deserves its own release), anything `needs-design`.

### Not in 0.24.2

**The journalism-investigation plugin's tool bugs** — #61 (`correlate` groups
nothing), #92/#93 (edges written as index-only ghosts with metadata strings the
read tools never see), #94 (`investigation_create_*` fails on a runtime-
registered KB), #98 — are milestone **0.25** (maintainer, 2026-09-18): real,
reproduced, and a plugin's problem, not the core's; they need the registry
single-source-of-truth item first anyway.

The GitHub-issues importer (ADR-0033 consequence) — not a priority; the
pyrite-dev skill checks GitHub directly instead. New UI surface of any kind.
The remaining web-UX items (0.25). Packaging beyond the git install
([[choose-a-pypi-distribution-name-and-decide-the-fate-of-pyrite-mcp]] stays
open until a name is chosen).

---

## 0.25 — Shared-Instance Pilot (item set to be re-chosen after 0.24.2)

The definition of done is unchanged: one or two invited peers, logged in,
reading the corpus read-only for two weeks with zero operator interventions.
The **2026-07-03 scope freeze is superseded** — much of its Workstream 1 shipped
in 0.24.1, its process items are now 0.24.2, and it could not know two things:
the per-KB read-scoping gap (fixed in 0.24.2) and that the web UI is not
packaged. The item set is re-chosen when 0.24.2 ships, from:
[[epic-shared-instance-readiness]]; the web first-visit fixes
([[web-kb-context-single-authority]], [[web-fix-dropped-kb-seams]],
[[web-sidebar-ia-regroup]], [[web-graph-default-scope-and-guards]],
[[web-light-mode-chrome-repair]]); [[oauth-state-store-persistence]]; the hosting-security static audit; the
invite doc. (Playwright moved to 0.24.2.)

---

## 0.26 — The review surface

"What did agents do since I last looked" as the home screen: a change feed per
agent and per commit with diffs, approve and revert, QA inline, the task board,
provenance on every entry. [[web-the-review-surface-what-did-agents-do-since-i-last-looked-as-the-home-screen]].
This is the screen that demonstrates the thesis, and the shell of the local
daily-driver app that agent integration (ADR-0030) plugs into. Argument in the
ADR-0031 review response.

---

## Later, unscheduled

Type-aware views via a declarative manifest (ADR-0031 open question 4);
agent run control (ADR-0030 Phase 1, Claude adapter first); the GitHub-issues
importer; write access for peers (needs tool-enforced provenance +
[[per-user-fork-directories]]); extension registry; PyPI once a name exists.
