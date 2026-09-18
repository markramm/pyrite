# Usability test: trace the Powell Memorandum's idea-lineage

A **task-first** usability test for pyrite search. The tester is given a research goal, not a list
of commands. What we learn is where the interface fails someone who knows the corpus has the answer
but not where it lives.

Run it against both surfaces:

- **CLI** — `pyrite search` / `get` / `backlinks` (`tests/usability/cli-run.md`)
- **Desktop / MCP** — `kb_search`, `kb_get`, `kb_backlinks` (`tests/usability/mcp-run.md`)

Same task, same scoring, so the two runs are comparable. Log findings per
`tcp-skills:hallway-agent-testing`, append to `FEEDBACK.md`, commit separately.

---

## The task given to the tester

> The 1971 Powell Memorandum ("Attack on American Free Enterprise System") is claimed in this corpus
> to be the origin of a fifty-year institutional arc. **Trace that lineage.** What did the memo
> argue, what institutions did it produce, who carried the ideas between them, and where does the
> corpus say the arc ends up today? Report the chain with entry ids, and say how confident the
> corpus is at each link.
>
> You may use any search mode or tool. Note what you tried and what it cost you.

No entry ids are given. Finding the entry point is part of the test.

## Why this task

- The answer genuinely exists and is well-built (a `theme` at importance 9, tier-1 sourced), so a
  failure to find it is a **tool** failure, not a corpus gap.
- The lineage spans `event`, `theme`, `organization`, `actor`, `mechanism`, `scene`, `statistic` —
  it exercises type diversity without being told to.
- The memo's thesis is highly paraphrasable, which is exactly where semantic search should shine.
  **It does not.** See the planted probe below.
- The arc has a documented modern end (Project 2025), so "did the tester get all the way there?"
  is checkable.

## Ground truth

The tester should end up with most of this. Do not show it to them beforehand.

**Entry point:** `1971-08-23-powell-memo` (event, importance 10) — "Lewis Powell Authors the
Corporate Capture Blueprint." Also `powell-memo-scene` (scene, importance 10).

**The synthesis:** `1971-1979-founding-formation-of-the-negative-coalition-powell-memo-to-moral-majority`
(theme, importance 9, `research_status: synthesis`).

**The institutional chain, in order:**

| year | institution | entry |
|---|---|---|
| 1971-08 | the memo itself | `1971-08-23-powell-memo` |
| 1972-01 | Powell sworn in — becomes implementor of his own diagnosis | `1972-01-07--powell-sworn-in-...` |
| 1972-12 | Business Roundtable | (cascade-timeline) |
| 1973-02 | Heritage Foundation | `1973-02-16-heritage-founding`, `heritage-foundation` |
| 1973-09 | ALEC | `alec-founding-structure-research` |
| 1974-77 | Olin / Scaife funding rails | `heritage-funding-network` |
| 1976-01 | *Buckley v. Valeo* — money is speech | `1976-01-30--buckley-v-valeo-money-is-speech` |
| 1979-06 | Moral Majority | (cascade-timeline) |
| 1981-05 | Council for National Policy | (cascade-timeline) |
| 1982 | Federalist Society | `federalist-society` |
| now | Project 2025 | `heritage-foundation` ("Powell Memo to Project 2025") |

**The three "bridges" that carry the ideas** — the analytically interesting part, and the thing a
tester who only lists institutions will miss:

- **Personnel:** Paul Weyrich (`weyrich-paul`) — co-founded Heritage, ALEC, Moral Majority, CNP in
  six years, spanning two doctrinally incompatible vectors.
- **Funding:** Joseph Coors (`coors-joseph`) — seed-funded Heritage *and* Moral Majority.
- **Technology:** Richard Viguerie (`viguerie-richard`) — the Goldwater donor list → direct mail.

**The structural claim:** the coalition is *coordination-of-infrastructure, not coalition-of-ends* —
built by shared operators and funders on a shared-enemy diagnosis, with factions moving into standing
infrastructure as they matured.

**The articulator-implementor seam:** Powell articulated the blueprint in Aug 1971 and implemented it
from the bench (nominated Oct 1971, sworn in Jan 1972, *Buckley* 1976). A strong tester finds this.

**Confidence is NOT uniform — a good report says so.** The theme's own tier-1 pass records that the
Weyrich personnel-bridge claim **did not upgrade**, Business Roundtable's core facts are
**unverified against any primary source**, and Moral Majority has **two unreconciled founding
accounts**. A tester who reports the chain as uniformly solid has missed what the corpus itself says.

---

## Planted probe: the semantic-recall failure

**Run these three before anything else.** Each is a close paraphrase of the memo's actual thesis, in
the memo's own conceptual vocabulary, naming no proper nouns:

```
business must organize politically against critics of free enterprise
corporations should fund think tanks to shift public opinion
long-term coordinated business counterattack on universities and media
```

Measured on the CLI, `-m semantic -n 10`, KB `cascade-research` (2026-09-18):

| query | results returned | Powell entry found? |
|---|---|---|
| 1 | **3** of 10 | no |
| 2 | **3** of 10 | no |
| 3 | **7** of 10 | no |

**None of the three surfaced `1971-08-23-powell-memo`.** Meanwhile `-m keyword "Powell memorandum"`
returns it at rank 1 instantly.

Two things to measure on each surface:

1. **Recall failure.** Semantic misses the canonical entry for a near-paraphrase of its own thesis.
   Does MCP behave the same?
2. **Silent under-return.** `-n 10` returns 3. Nothing says why. Is there a hidden similarity
   threshold? Is it documented? Can the tester discover the cutoff without reading source?

## Failure modes this test is designed to expose

**Semantic/hybrid:**
- *Vocabulary mismatch* — the corpus indexes analytic prose ("corporate capture blueprint"); the
  query uses the source's period vocabulary ("free enterprise system"). Embeddings should bridge
  this and do not.
- *Silent truncation* — fewer results than `-n` with no explanation.
- *Off-domain drift* — `"accountability disappears through procedural bypass"` ranked a **Windows
  10/11 privacy-hardening note** 4th, above on-topic governance themes.
- *Long-document dilution* — the Powell entry is 34.6KB; if embedded whole, its specific thesis is
  averaged away. Does chunking exist?
- *Proper-noun blindness* — semantic is weakest exactly where keyword is strongest, and the tool
  offers no guidance on which to reach for.

**Hybrid specifically:**
- Does fusion *recover* what semantic missed, or does semantic noise *displace* good keyword hits?
  Run `-m hybrid` on the three probes and compare against keyword.
- Hybrid is the natural default for exploration and the slowest mode (8-13s vs 49ms keyword).

**Known open bug ([#53](https://github.com/markramm/pyrite/issues/53)):** `--type` is silently
ignored in semantic and hybrid. A tester filtering to `theme` will get unfiltered results. Check
whether MCP shares this.

## Scoring

| # | Checkpoint | Pass |
|---|---|---|
| 1 | Found `1971-08-23-powell-memo` | in ≤3 calls |
| 2 | Found the founding-formation theme | at all |
| 3 | Named ≥6 institutions in order | with ids |
| 4 | Found ≥2 of the three bridges | Weyrich / Coors / Viguerie |
| 5 | Found the articulator-implementor seam | *Buckley* included |
| 6 | Reached the modern end | Project 2025 |
| 7 | **Reported non-uniform confidence** | named ≥1 of the 3 weak links |
| 8 | Used `backlinks` | see note |

**Checkpoint 8 is the one to watch.** On the CLI run, `backlinks 1971-08-23-powell-memo` returned
**24 entries across 7 types** and was dramatically better for lineage tracing than any search call —
it gives structural descendants directly, where search gives topical neighbours. Nothing in
`search --help` suggests reaching for it. If a tester never discovers `backlinks`, that is a
**discovery** failure worth more than any ranking complaint.

## Record per call

Command as actually run · mode · `-n` · results returned · latency (use `--debug`) · whether the
target was in them · context cost (lines of output).

Then: total calls to first correct entry, total wall-clock, and **what you tried that did not work**
— failed queries are the finding.
