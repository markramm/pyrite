# MCP / Desktop run sheet — Powell lineage usability test

Surface: `pyrite mcp --tier write` via Claude Desktop (`kb_orient`, `kb_search`, `kb_get`,
`kb_backlinks`, `kb_timeline`, `kb_tags`, …).
Protocol: `powell-lineage-search-usability.md`. Paired CLI run: `cli-run.md`.

**Everything below the line can be pasted to the Desktop session as-is.**

---

You are hallway-testing the **pyrite MCP search interface**. Invoke the
`tcp-skills:hallway-agent-testing` skill first and follow its entry format.

Two goals, equal weight: **do the research task properly**, and **report where the interface fights
you**. A silent workaround is the most expensive failure mode — report friction even when you routed
around it, especially then.

## Your research task

The 1971 **Powell Memorandum** ("Attack on American Free Enterprise System") is claimed in this
corpus to be the origin of a fifty-year institutional arc. **Trace that lineage.**

- What did the memo argue?
- What institutions did it produce, in what order?
- **Who carried the ideas between them?** (This is the analytically interesting part. A list of
  institutions is a partial answer.)
- Where does the corpus say the arc ends up today?
- **How confident is the corpus at each link?** Confidence is *not* uniform, and the corpus says so
  about itself. A report that presents the chain as uniformly solid has missed something real.

Report the chain with entry ids. Main KB: `cascade-research` (~3,576 entries). The arc also crosses
into `cascade-timeline`.

No entry ids are given deliberately — finding the entry point is part of the test.

## Run these three probes first, before anything else

Each is a close paraphrase of the memo's own thesis in the memo's own conceptual vocabulary, naming
no proper nouns. Run each in **semantic**, then **keyword**, then **hybrid**, with a limit of 10:

```
business must organize politically against critics of free enterprise
corporations should fund think tanks to shift public opinion
long-term coordinated business counterattack on universities and media
```

On the CLI (2026-09-18), semantic returned **3, 3, and 7** results against a limit of 10, and **none
of the three surfaced the canonical Powell entry** — while keyword `"Powell memorandum"` returns it
at rank 1 instantly.

Record for each: results returned, whether the Powell entry appeared, and latency. Then say whether
**hybrid recovers what semantic missed, or whether semantic noise displaces good keyword hits.**

## Known CLI findings — check whether MCP shares them

**1. Type filter silently ignored in semantic/hybrid** ([#53](https://github.com/markramm/pyrite/issues/53)).
Query `"accountability bypass"`, limit 8: keyword + `type=theme` → 8 themes; keyword +
`type=bogus-xyz` → **0** (correct). Semantic and hybrid → **8 identical results for both**. A
nonexistent type returning a full set means the filter never ran. Also try negation / multiple
values; on the CLI `!task` and `theme,mechanism` both parse as one opaque string and neither errors.

**2. Silent under-return.** Limit 10 → 3 results, no explanation. Is there a similarity threshold?
Is it documented or discoverable from the MCP surface? Can you see *why* it stopped?

**3. Latency cliff.** Keyword 49 ms, semantic 6,002 ms, hybrid 8,033 ms on identical queries (other
runs: 11,144 / 13,337 ms). Does MCP expose timing at all? Does anything warn you before you pick a
mode?

**4. Off-domain semantic drift.** `"accountability disappears through procedural bypass"` ranked a
**Windows 10/11 privacy-hardening note** 4th, above on-topic governance themes. Is there any
relevance floor, and are the score fields (`rank`, `rrf_score`) interpretable enough to act on?

**5. `entry_type` inconsistency** — both `research-note` and `research_note` appear for one
conceptual type. Once filtering works, does filtering one silently miss the other?

## Things to exercise while doing the real work

- **`kb_orient`** is documented as the recommended first call. Does it earn that, or do you
  immediately need something else?
- **`kb_backlinks`.** On the CLI, `backlinks 1971-08-23-powell-memo` returned **24 entries across 7
  types** and was by far the best call for lineage tracing — search gives topical neighbours,
  backlinks gives structural descendants. **Nothing in the search docs points to it.** If you don't
  reach for it until stuck, say so; that discovery gap matters more than any ranking complaint.
- **Long entries.** The Powell event is **34.6 KB** and `get` has no summary/excerpt option. What
  does MCP do — return the whole thing into context? Truncate silently? Note the context cost.
- **Output shape.** CLI default is ~20 fields per result; `--fields id,title,entry_type` fixes it and
  is nearly undiscoverable. Does MCP return a lean shape by default, or the same wall? Is there a
  field-selection equivalent?
- **Long ids.** Ids run past 100 characters. Is there prefix or fuzzy id resolution, or must you
  reproduce them exactly? (CLI: exact only — a display-truncated id fails with `NOT_FOUND`.)
- Also touch **`kb_timeline`** and **`kb_tags`** if exposed, and **verify any filter actually
  filtered** rather than assuming.

## Reporting

Placeholder real people and organisations **under investigation** per the skill (`<person-a>`,
`<vendor-b>`) — but **keep** tool names, flags, entry ids, modes, latencies and output shapes; those
make it reproducible. Note: for *this* task the historical subjects (Powell, Heritage, Weyrich) are
the corpus's public-historical content, not investigation subjects, so entry ids like
`1971-08-23-powell-memo` should be reported as-is.

Append your entry to `/Users/markr/pyrite/FEEDBACK.md` and **commit it yourself**, in its own commit
naming only that file.

Number distinct problems separately with their own severity (`blocked | slowed | annoyed |
cosmetic`). Separate **observations** from **conclusions** — "returned 3 results" is an observation;
"there is a similarity threshold" is a conclusion that may be wrong. Include what **worked well**,
specifically; clean runs are data.

And report the **research findings separately from the tool findings**. If the interface made a real
part of the lineage hard to see, that is the single most valuable thing you can write down.
