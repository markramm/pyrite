---
type: plan
id: workflow-hallway-test-plan
title: "Hallway-test plan: exercise the pyrite CLI through real editorial and research work"
status: draft
date: '2026-09-18'
author: 'claude-opus-5'
tags: [usability, hallway-testing, cli, workflow, plan]
---

# Hallway-test plan — exercise the CLI by doing real work

Six loops. Each does **work worth doing anyway** and, as a side effect, exercises a slice of the CLI
that current workflows never touch. Nothing here is a synthetic probe: if a loop produces nothing
useful to the corpus, it is the wrong loop.

**Governing rule.** The research output and the friction log are *both* deliverables. A loop that
produces good research and no friction notes has failed half its job, and vice versa. Log per
`tcp-skills:hallway-agent-testing`, append to `/Users/markr/pyrite/FEEDBACK.md`, commit separately
naming only that file.

**Placeholder discipline.** `FEEDBACK.md` is public. Replace investigation subjects with stable
placeholders (`<person-a>`, `<vendor-b>`). Keep tool names, flags, entry ids, modes, latencies and
output shapes — those make it reproducible. Historical/public-record content (Powell, Heritage) is
corpus content, not an investigation subject; report those ids as-is.

## Surface coverage

Already tested: `search`, `get`, `orient`, `backlinks`, `index sync`, `task list/get/create/update/claim`.

**Untouched, and covered below:** `create` · `add` · `update` · `rename` · `delete` · `link` ·
`links check|suggest|discover|batch-suggest|orphans|asymmetric` · `batch-read` · `list-entries` ·
`recent` · `timeline` · `tags` · `collections list|query` · `qa validate|assess|status|gaps|stale|
compact|check-urls|coverage` · `investigation network|ownership|claims|evidence-chain` · `task reset|
checkpoint|decompose` · `export` · `import` · `ci`

---

## Loop 1 — `/capture-leads`: creation and duplicate detection under load

**Real work.** Harvest the `leads:` from daily-capture-reports stories and instantiate the ones worth
working as cascade-research tickets. These are currently discarded, including on stories dropped as
duplicates where the story was redundant but the lead is live.

**Features exercised:** `create`, `task create`, `search` as a pre-create duplicate check,
`links suggest`, `qa validate`.

**The question this answers.** Creating an entry is the operation most likely to produce a duplicate,
and duplicate detection is currently done by a hand-written Jaccard sweep in the conductor skill.
**Does the tool help at all?**

Sequence:
1. Before creating each ticket, try to find an existing one covering the same question. Try
   `search` (all three modes), then `links suggest` on the nearest existing entry. Record which
   found the duplicate, if either.
2. Create the surviving tickets with `task create` / `create`.
3. Run `qa validate` after. Does it catch anything about the new entries?

**Watch for:** Does `create` warn on a near-duplicate id or title? (Expected: no.) Does it validate
required frontmatter per type, or accept anything? What happens creating an entry whose id already
exists — overwrite, error, or silent second file? **Test this deliberately on a scratch id.**
Is `links suggest` (FTS5 on title+tags, no LLM) good enough to replace the hand-rolled sweep?

**Known context:** the conductor's duplicate sweep found two real pairs by-eye detection missed,
both where one slug led with the event name and the other with an ISO date.

---

## Loop 2 — Investigation-conductor tick: task lifecycle end to end

**Real work.** One full tick — dispatch, absorb, QC, groom.

**Features exercised:** `task claim|update|reset|checkpoint|decompose`, `recent`, `list-entries`,
`batch-read`.

**The question.** The conductor skill carries elaborate manual workarounds for claim management. Two
were already found to be unnecessary or wrong. **How much of that skill is scar tissue?**

Sequence:
1. Use `recent` instead of the skill's `git log` scan to find what changed since the last tick.
   Does it answer the question?
2. Use `batch-read` to absorb several completions in one call rather than N `get` calls. Measure the
   context saving.
3. On any stale claim, use **`task reset`** rather than the skill's hand-edit (keep `in_progress`,
   blank the assignee, add `parked_awaiting: redispatch-after-*`). Compare: does `reset` leave a
   better audit trail? Does the task correctly read as dispatchable afterward?
4. Use **`task checkpoint`** for absorption notes instead of appending prose to the notes file.
   Is the checkpoint retrievable later? By what command?
5. If a ticket is too big, try **`task decompose`** rather than hand-writing child tickets.

**Watch for:** Does `reset` work on a `blocked` task as the help claims? Does `checkpoint` survive
an `index sync`? Is there any guard against closing a task whose `parked_awaiting` is unresolved —
a real failure that happened and was caught by hand.

**Carry forward:** `task update` still cannot set `parked_awaiting` (pyrite task, p7). Every park in
this loop is a hand-edit; count them and note the cost.

---

## Loop 3 — Cross-corpus theme discovery: the read-side gap

**Real work.** The corpus is written by many independent workers who never see across it. Find
themes that exist *in aggregate* but are not written down anywhere.

**Features exercised:** `tags`, `collections list|query`, `list-entries`, `qa gaps`,
`links orphans|asymmetric|batch-suggest`, `search --expand`.

**The question.** Search finds documents. **Can anything here find a cluster?** This is the highest-
value loop for the design note's §2.7 claim that agents need map-building primitives, not retrieval.

Sequence:
1. `tags -k cascade-research` — does tag co-occurrence reveal clusters? Are tags disciplined enough
   to be a clustering signal, or too noisy?
2. `collections list` / `collections query` — what is a collection here, and does it already do
   what I want? (Genuinely unknown to me; `--help` is two lines.)
3. `qa gaps` — "entries with no outbound/inbound links, sparse types, unused tags." This is
   corpus-shape analysis and may be the single most useful untested command.
4. `links orphans` — **high-importance entries lacking cross-KB connections.** Directly valuable:
   an importance-9 entry nothing links to is either a gap or a missed synthesis.
5. `links asymmetric` between `cascade-research` and `cascade-timeline` — one-directional links are
   exactly the "independent writes never see across the corpus" problem.
6. `search --expand` (AI query expansion) — does it fix the semantic recall failure from the Powell
   test? Run the three Powell probes with `-x` and compare.

**Deliverable:** at least one genuinely new theme candidate, written up as a `theme` entry (which
exercises `create` on a real type), plus a verdict on whether the tooling can support cluster-finding
or whether it is all done by hand today.

---

## Loop 4 — Brief ideas from research: the read→write seam

**Real work.** Identify 2-3 brief-worthy findings sitting in research that nothing has promoted to
`drafts/queue/`. The MI-election audit found five such; there are certainly more in other lanes.

**Features exercised:** cross-KB `search`, `export`, `create` in `drafts`, `link` across KBs,
`batch-read`.

**The question.** Research lives in `cascade-research`, drafts in `drafts`. **How well does the tool
support working across two KBs at once?**

Sequence:
1. Search `cascade-research` for high-importance entries with `research_status: complete`.
   **Note whether `research_status` is even filterable** — the design note flags it as the corpus's
   best metadata and barely surfaced. Expect to fall back to grep.
2. For each candidate, check `drafts` for an existing brief. This is the step-zero duplicate check
   that a prior brief round skipped, producing duplicates of finished drafts.
3. Write briefs with `create -k drafts`.
4. Use `link` to connect the brief to its substrate entries **across KBs**. Does cross-KB `link`
   work? Does it create a real backlink, or just text?
5. `export` the brief set — does any format produce something handable to a human?

---

## Loop 5 — Backlinks for recent actor profiles: `link`, `rename`, and graph repair

**Real work.** Recent actor profiles (Michigan Supreme Court justices, Guadalupe entities, the
redistricting panel judges) were written without timeline backlinks. Wire them up.

**Features exercised:** `link`, `links check`, `links bulk-create`, `links discover`, `backlinks`,
`rename`, `timeline`.

**The question.** `backlinks` was the best call in the Powell test. **How hard is it to *create*
the links that make it good?**

Sequence:
1. `links check -k cascade-research` — find broken links first. Fix what is mechanical.
2. For each recent actor profile, `links discover` against `cascade-timeline` — semantically similar
   entries in another KB. Does it find the right events?
3. `links bulk-create` from a YAML file — the batch path. Does it validate before writing?
4. Verify with `backlinks` that the links landed **bidirectionally**.
5. **`rename` test, deliberately.** Pick one entry with a genuinely bad id (the corpus has 100+
   character ids) and rename it. The help claims it rewrites frontmatter id **and updates
   wikilinks**. Verify that claim: does it catch wikilinks in *other* KBs? Does it update the index?
   **This is the highest-risk command in the CLI and the least tested** — do it on a low-importance
   entry, with a clean git tree, so revert is one command.

---

## Loop 6 — Corpus hygiene: the QA surface, unused entirely

**Real work.** The corpus has known integrity debt: duplicate ids, entries with unverifiable sources,
stale monitors, `research-note` vs `research_note`.

**Features exercised:** the whole `qa` tree, `ci`, `db backup`, `schema`, `protocol`.

Sequence:
1. **`db backup` first.** Everything else in this loop is potentially destructive.
2. `qa status` — the dashboard. Is it actionable or decorative?
3. `qa checkers` — what rubrics exist? Do they match the corpus's actual standards (tier-1 sourcing,
   date-kind discipline, "what this does NOT claim")?
4. `qa stale` and `qa compact` — stale entries and archival candidates. Cross-check against the
   parked-monitor problem: does `stale` flag things that are correctly waiting?
5. **`qa check-urls`** — highest real value in this loop. The corpus asserts tier-1 sourcing
   everywhere; this checks whether the URLs still resolve. Expect link rot. **Do not let it conclude
   a dead URL means a bad source** — a 404 is a liveness fact, not a sourcing verdict. That
   distinction is exactly the `a-passing-gate-is-not-verified-sourcing` failure.
6. `qa fix` — auto-fix safe issues. **Dry-run first if one exists; if not, that absence is the
   finding.** Run on a branch.
7. `ci` — exit 0/1 validation. Does it pass on the current corpus? If not, what does it object to?

---

## Cross-cutting things to record in every loop

- **Does the command say what it did?** The strongest recurring finding so far is silence:
  filters dropped without notice, validators skipped with a traceback and exit 0, `index sync`
  reporting `Updated: 1` while changing nothing.
- **Exit codes.** Several commands return error payloads with **exit 0**. Check before branching on
  `$?`, and never through a pipe — `$?` is the pipe's status.
- **Destructive-command safety.** `delete`, `rename`, `qa fix`, `import` — is there a dry-run? A
  confirmation? Test each on a scratch entry with a clean tree.
- **Context cost.** Lines of output per useful fact. `--fields` where available.
- **Latency**, where it is not obviously instant.
- **What you reached for and could not find.** The most valuable category. `backlinks` was
  undiscoverable from the search docs; `task reset` was undiscoverable from the conductor skill.

## Sequencing

Loops 1-2 are the everyday path and should run first — they are the workflows most likely to hide
scar tissue. Loop 3 is the highest-value unknown. Loop 5 contains the riskiest command (`rename`).
Loop 6 runs last, on a branch, after `db backup`.

One loop per session is enough. **The friction log is the deliverable that expires** — write it
before the session ends, while the annoyance is still specific.
