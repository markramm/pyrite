---
type: report
id: cli-hallway-report-2026-09-18
title: "CLI hallway-testing report, 2026-09-18 — findings from using pyrite to do real editorial and research work"
status: final
date: '2026-09-18'
author: 'claude-opus-5 (agent user)'
tags: [usability, hallway-testing, cli, report]
---

# CLI hallway-testing report — 2026-09-18

**Tester:** an agent (claude-opus-5) using the CLI to do real work in a **single ~2-hour session** —
an investigation-conductor tick, a four-way fact-check, a brief-gap audit, corpus-health repair, and
a traced research question. Not a scripted test pass: every command below was run because a task
needed it.

**The session length is itself a finding.** Six issues, including one silent data-corruption defect
reachable from four commands, surfaced in about two hours of ordinary use by one tester. None
required adversarial probing — the corrupting bug was found by running `link` once, on one entry,
while doing corpus-health work, and noticing the diff.

**Corpus:** `cascade-research`, 3,576 entries (1,724 `task`, 441 `actor`, 383 `note`, 264 `theme`,
211 `organization`, 165 `research-note`, 77 `mechanism`). 52 KBs registered.

**Six issues filed:** #48, #51, #52, #53, #54, #87. Two feedback entries appended to `FEEDBACK.md`.

---

## The one-paragraph version

The CLI's **read** surface is strong and its **write** surface has a defect that silently corrupts
entries. Search, `orient`, `backlinks` and the `qa` tree all did real work well — `qa gaps` produced
the single most valuable output of the session. But a body line matching `^[-|\s]+$` (a markdown
table separator or a horizontal rule) causes `link`, `update`, `create --link` and
`links bulk-create` to write frontmatter that no longer parses, while reporting success and exiting
0. Markdown tables are ubiquitous in this corpus, so the corrupting case is the ordinary case. The
correct implementation already exists inside `rename`.

**The recurring theme across every finding is silence.** Filters dropped without notice. A validator
skipped with a traceback and exit 0. `index sync` reporting `Updated: 1` while changing nothing.
`link` reporting `Linked:` while destroying the file. In each case the tool's output was consistent
with success, and only an independent check revealed otherwise. That pattern matters more than any
individual bug.

---

## 1. The severe one: the write path corrupts entries

**#87.** Found while doing corpus-health work — wiring up orphaned entries that `qa gaps` had
surfaced.

### What happens

```bash
pyrite link <entry> <target> -k cascade-research -r documents --note "..."
# Linked: <entry> ----> <target> (in cascade-research)      [exit 0]
```

On a 96-line real entry this produced a **181-line diff (+97/-84)**. The markdown body was folded
into a `body: "..."` YAML scalar; internal `file_path` was written into the file; key order was
scrambled; and `id`, `title`, `type`, `importance`, `tags`, `related_actors` were **dropped**. The
resulting frontmatter does not load:

```
yaml.scanner.ScannerError: while scanning a quoted scalar
  in "<unicode string>", line 11, column 7:
    body: "## What this mechanism is\n\nMi ...
found unexpected end of stream
```

### The trigger, isolated

Six single-construct probes in a sandbox KB, one `link` call each, then `yaml.safe_load`:

| body content | result |
|---|---|
| plain prose | PARSES |
| `A line with "double quotes" in it.` | PARSES |
| `A line with a colon: right here.` | PARSES |
| line ending in `\` | PARSES |
| `[[wikilink]]` | PARSES |
| a markdown table | **UNPARSEABLE** |

Narrowed further: inline pipes are fine, a header row `| a | b |` is fine. **A line consisting only
of hyphens and pipes** — `|---|---|` or a bare `---` — is the trigger. Inside a double-quoted YAML
scalar it terminates the frontmatter block early.

### The blast radius is four commands, and one of them is `update`

The decisive test was a one-flag A/B on the same table-bearing body:

```bash
pyrite create -k cli-sandbox -t note --title "..." --body-file <table-bearing>            # CLEAN
pyrite create -k cli-sandbox -t note --title "..." --body-file <table-bearing> --link X   # UNPARSEABLE
```

So entry persistence is correct; **the defect is in the link-application step.**

| command | corrupts? | `--dry-run`? |
|---|---|---|
| `create` | no | n/a |
| `create --link` | **yes** | n/a |
| `link` | **yes** | **no** |
| `update` | **yes** | **no** |
| `links bulk-create` | **yes** | yes |
| `rename` (subject entry) | writes `body:` into frontmatter | yes |
| `rename` (inbound wikilinks in *other* files) | **no — textual edit** | yes |
| `qa fix` | no | yes |

`update` matters most: it is the ordinary way to change a tag or a status and what every automated
workflow reaches for. **GH #46 and #47 — `update` dropping and blocking frontmatter fields — are
plausibly this same defect from another angle**, as is #51's lost `parked_awaiting`.

Note the correlation in that table: **the two commands that silently corrupt are the two without
`--dry-run`.**

### A second defect inside the first

On table-free entries the body is not *moved* into `body:` — it is **duplicated**, appearing both in
frontmatter and as markdown. Two sources of truth that drift on the next edit. `file_path`, an
absolute machine-local path, is also written into the file and will be wrong in every other
checkout.

### Where the fix lives

`rename` does the right thing for third-party files: its inbound-wikilink rewrite is a **targeted
textual edit**, and the file it edits comes out clean with no `body:` key. Only `rename`'s own
subject entry goes through the broken save. Whatever that link-rewriting path does, `link` and
`update` should do.

**Suggested regression test** (one parametrized case covers all four commands): for each of `link`,
`update`, `create --link`, `links bulk-create`, `rename` — given an entry whose body contains a line
matching `^[-|\s]+$`, assert afterwards that the frontmatter still loads, the body is byte-identical,
and no `body:` or `file_path:` key was introduced.

---

## 2. Search filters are silently dropped in the default mode

**#53.** `--type` is honored in `keyword` and ignored in `semantic` and `hybrid`.

Query `"accountability bypass"`, `cascade-research`, `-n 8`:

| mode | `--type theme` | `--type bogus-xyz` |
|---|---|---|
| keyword | 8 results, all `theme` | **0** ✅ |
| semantic | 8 results — 7 theme, 1 mechanism | **8, identical set** ❌ |
| hybrid | 8 results — 7 theme, 1 mechanism | **8, identical set** ❌ |

`--debug` reports `relaxed=False`, so this is not a documented fallback relaxation. The sharpest
evidence is not the bogus-name test: **`--type theme` returning a `mechanism`** proves the filter
never ran, independent of name validation.

Two defects: the filter is not applied, and an unrecognized type value is accepted silently.

**This was independently confirmed on the MCP surface** (#56, filed the same day by a cold-start
session, which additionally found `tags`, `state` and `fips` dropped the same way). Two testers,
opposite directions, same bug — it is server-wide, not a CLI quirk.

**Why it matters here specifically:** `task` entries are **1,724 of 3,576 (48%)** of this corpus —
workflow bookkeeping, not research. Type filtering is the main way to make the corpus tractable, and
it is missing precisely in the modes you want for thematic exploration.

---

## 3. A validator that never runs, loudly

**#48.** `_validate_cascade_entry()` in the cascade extension takes **one** argument; the registry
calls plugin validators with **three**, then falls back to **two**. Neither matches, both raise
`TypeError`, and the second is swallowed by an `except Exception` logger.

```
$ pyrite task update <id> -k cascade-research --priority 7
Validator fallback failed for task
Traceback (most recent call last):
  File ".../pyrite/schema/kb_schema.py", line 391, in validate_entry
    results = validator(entry_type, fields, ctx)
TypeError: _validate_cascade_entry() takes 1 positional argument but 3 were given
...
Updated task: ...
$ echo $?
0
```

So **every cascade-KB plugin validation is silently skipped**, and every task update prints an
alarming traceback while succeeding. The return contract also mismatches: the definition returns
`list[str]`, the call site expects dicts with a `severity` key.

Two distinct defects — the arity mismatch, and the fact that a validator which never runs is
indistinguishable from one that passes.

---

## 4. The index does not always hold what the file says

**#51.** 20 tasks carry a well-formed `parked_awaiting:` on disk that the API reports as `None`.

| source | parked count (99 `in_progress` tasks) |
|---|---|
| `task list --format json` → `parked_awaiting` | 68 |
| reading each file, matching `^parked_awaiting:` | **88** |

One-directional — the API never over-reports. `task get` agrees with `task list`, so it is the
stored index. **`index sync` does not repair it**: `touch` the file, re-sync, `Updated: 1`, field
still `None`.

All 20 trace to a single bulk commit (2026-08-19) and none has been successfully re-indexed since.
This looks like residue of #15 (unknown frontmatter keys dropped on load), which was **closed at
04:23 that same morning** — the fix stops new losses but nothing re-derives the old rows.

**Operational consequence:** `parked_awaiting` is what a conductor's dispatch gate reads to
distinguish *legitimately waiting* from *stalled*. Under-reporting it makes parked work look
dispatchable. **The documented workaround — read every notes file and regex the body — is currently
more correct than the API**, which is worth knowing before anyone replaces it with the API field.

---

## 5. Where the results fell short, not just the tool

### Semantic search missed a near-paraphrase of a document's own thesis

While tracing the Powell Memorandum's idea-lineage, I ran three close paraphrases of the memo's
argument in the memo's own conceptual vocabulary, naming no proper nouns:

| query (`-m semantic -n 10`) | returned | canonical Powell entry? |
|---|---|---|
| business must organize politically against critics of free enterprise | 3 | **no** |
| corporations should fund think tanks to shift public opinion | 3 | **no** |
| long-term coordinated business counterattack on universities and media | 7 | **no** |

`-m keyword "Powell memorandum"` returns it at **rank 1**.

This is a **vocabulary-register mismatch**: the corpus indexes analytic prose ("corporate capture
blueprint"); the researcher queries in the source's period vocabulary ("free enterprise system").
Same idea, two registers, and embeddings did not bridge them. The failure is invisible — you get
plausible on-topic results and no signal that the best entry was missed.

Note also the **silent under-return**: limit 10, three results back, no explanation. If a similarity
threshold exists it is undocumented and undiscoverable.

**Related off-domain drift:** `"accountability disappears through procedural bypass"` ranked a
**Windows 10/11 privacy-hardening note** 4th, above on-topic governance themes. `rank` and
`rrf_score` appear in every result and neither is interpretable enough to act on; there is no
relevance-floor option.

### The best tool for the job was not a search

`backlinks 1971-08-23-powell-memo` returned **24 entries across 7 types** and traced the lineage
directly — search gives topical neighbours, backlinks gives structural descendants. **Nothing in
`search --help` points to it.** If a tester never reaches for `backlinks`, that discovery failure
costs more than any ranking complaint.

### A latency cliff with no signal

Same query (`"detention pipeline county"`, `-n 5`), via `--debug`:

| mode | latency |
|---|---|
| keyword | 49.4 ms |
| semantic | 6,001.98 ms |
| hybrid | 8,033.17 ms |

Other runs: semantic 11,144 ms, hybrid 13,337 ms. **~120–270×.** Nothing outside `--debug` hints at
it. Not asking for it to be faster — asking for the cost to be discoverable, since hybrid is the
default and the natural choice for exploration.

### Output shape is expensive by default

Default search JSON returns ~20 fields per result, five of which are timestamp/authorship fields that
never inform a search decision. At `-n 20` that is ~400 lines to answer "what's in here about X."
**`--fields id,title,entry_type` fixes it completely** and was the single biggest improvement to the
session — found on a second reading of `--help`, below the fold.

---

## 6. Discoverability: two commands existed that would have saved real work

**#52.**

- **`task reset`** — *"Release a stale in_progress/blocked claim back to `open`… clears the assignee,
  and appends a work-log entry."* The conductor workflow instead prescribes a manual sequence (keep
  `in_progress`, hand-blank the assignee, add `parked_awaiting: redispatch-after-*`) because `review`
  is a one-way door. That workaround is strictly worse — no audit trail, no `--operator` — and exists
  only because `reset` was not known.
- **`task checkpoint`** — logs a checkpoint with `--confidence` and repeatable `--evidence`.
  Absorption notes are currently appended as prose to notes files instead.

Neither is mentioned where you need them. The refusal message for an illegal status transition would
be the natural place to name `task reset`.

Relatedly: **`task status` is marked `[Deprecated]` in `--help` but prints no warning at runtime**,
so downstream docs and agent memory keep recommending it indefinitely. I was carrying exactly that
stale recommendation.

**And the surface is much larger than the workflows use.** Untouched before this session: the whole
`qa` tree, the whole `links` tree, `collections`, `protocol`, `investigation network`/`ownership`,
`rename`, `batch-read`, `export`, `import`. That gap is itself a finding.

---

## 7. What worked — specifically

Naming these precisely, because the list above is longer and would give a misleading impression.

**`qa gaps --format json` was the most valuable command of the session.** It turned "independent
writes never see across the corpus" from a hunch into a number: **1,409 entries with no outbound
links, 1,855 with no inbound, out of 3,576**, broken down by type. Cross-referencing the two lists
gave **12 entries orphaned in both directions at importance ≥ 6** — a short, precise, actionable work
list. Nothing else in the toolchain produces that.

*One caveat:* the rich output omits `no_inlinks` and `distribution` entirely. The more interesting
number is JSON-only.

**`links suggest` is good and cheap.** FTS5 on title+tags, no LLM, no embedding cost. On an orphaned
mechanism entry it returned exactly the right neighbours — the two actor profiles and three source
tasks that mechanism was built from, sensibly ranked. This is a credible replacement for the
hand-rolled Jaccard duplicate sweep in the conductor skill.

**`rename` does everything it claims.** File renamed, frontmatter `id` rewritten, inbound wikilink in
another entry updated, `links_rewritten: 1`, `index_verified: true`, and `--dry-run`. It was the
riskiest command in the plan and it was fine.

**`qa fix` is the best-behaved destructive command in the CLI.** Dry-run available, honest "No
fixable issues found" rather than inventing work, and a separate `not_auto_fixable` bucket with
reasons instead of guessing. Model behavior.

**`pyrite init` is friction-free** — one command, zero prompts, registered and indexed. A usable
sandbox in seconds, which is the only reason destructive commands could be tested at all.

**`orient` earns its "first call" billing** — entry counts and a type histogram let you plan before
searching.

**`--debug` is well-judged**: mode, actual mode, fallback reason, latency, `relaxed` flag. Everything
in it is worth having; the only complaint is that it is opt-in.

**The FTS5 auto-quote documentation in `search --help` is the best writing in the CLI.** It states
the rule *and* names the exact trap — `miller -bannon` parses the hyphen as `NOT`, matching Bannon
entries rather than excluding them. I would have hit that. I did not, because someone wrote it down.

**The `--status` help documents its own limits**, saying outright that other metadata fields such as
`readiness` are unreachable through it. That caveat prevents a silent wrong answer. More flags should
do this.

---

## 8. Things I got wrong

Recorded because a false bug report costs a maintainer more than a missing one.

**I nearly filed "get returns empty bodies."** I saw `title=None bodylen=0` and started writing it
up. It was my own Python swallowing a `NOT_FOUND` error payload — I had truncated a 100-character id
in my own earlier output and guessed the tail wrong. `get` behaves correctly.

Two real findings underneath the false one: entry ids run past 100 characters with **no prefix or
fuzzy resolution**, and `get` returns `NOT_FOUND` with **exit code 0**.

**I built and discarded two root-cause theories for #51.** *Length* — misses were all ≤15 chars and
hits ≥16, a clean split across 88 data points; rewriting one value to 40 chars still failed.
*`status_reason` presence* — 59 tasks without it reported fine. Both spurious. The commit-date
clustering was the real signal.

**I reported a duplicate-`priority` frontmatter bug that did not exist** — my own `grep` and `sed`
ranges each printed the same line. Zero real cases across 154 files.

The common shape: **a filter or parser between me and the tool, mistaken for the tool.** Worth
stating in the docs that exit-code branching through a pipe reads the pipe's status, not the
command's.

---

## Filed

| # | Severity | Title |
|---|---|---|
| [#87](https://github.com/markramm/pyrite/issues/87) | 🔴 blocked | `link` corrupts entries; widened to `update`, `create --link`, `links bulk-create` (3 comments with root-cause isolation and the full matrix) |
| [#53](https://github.com/markramm/pyrite/issues/53) | 🔴 blocked | `--type` silently ignored in semantic and hybrid |
| [#48](https://github.com/markramm/pyrite/issues/48) | 🔴 | Cascade plugin validator never called; validation silently skipped, traceback with exit 0 |
| [#51](https://github.com/markramm/pyrite/issues/51) | 🟠 | `parked_awaiting` missing from the index for 20 pre-#15 tasks; `index sync` does not repair |
| [#54](https://github.com/markramm/pyrite/issues/54) | 🟠 | Search UX: verbose default output, invisible latency cliff, no type exclusion, unreadable scores |
| [#52](https://github.com/markramm/pyrite/issues/52) | 🟡 | `task status` deprecation invisible at runtime; `task reset`/`checkpoint` undiscoverable |

Companion artifacts: `tests/usability/powell-lineage-search-usability.md` (task-first protocol,
CLI + MCP run sheets), `tests/usability/workflow-hallway-test-plan.md` (six work-driven loops),
`kb/designs/search-failure-modes-and-agent-interface.md` (failure modes + proposed agent-shaped
interface), and two entries in `FEEDBACK.md`.

## If only three things get fixed

1. **The link-application step** (#87) — it is silent, it corrupts source-of-truth files, it is
   reachable from `update`, and the correct implementation is already in `rename`.
2. **Report dropped filters** (#53, #56) — a `filters_dropped: []` field present and empty on every
   successful call would make this class of bug self-reporting rather than silent.
3. **`--dry-run` on `link` and `update`** — the two corrupting commands are exactly the two that
   lack it.
