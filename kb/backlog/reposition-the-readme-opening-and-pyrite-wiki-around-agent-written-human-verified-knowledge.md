---
id: reposition-the-readme-opening-and-pyrite-wiki-around-agent-written-human-verified-knowledge
title: Reposition the README opening and pyrite.wiki around agent-written, human-verified knowledge
type: backlog_item
tags:
- positioning
- docs
- go-to-market
importance: 5
kind: improvement
status: proposed
priority: medium
effort: M
rank: 0
---

## Problem

The product page and README lead with "A second brain for you, your agents, and
your teams" — the most crowded headline in the space, against Obsidian / Notion
/ Logseq, where the fight is UI polish. The page names eight audiences; the
"Why Pyrite" grid lists mechanisms rather than problems; and the strongest
material (built for an investigative newsroom, thousands of sourced entries,
trace a claim to the commit that introduced it) sits in the README's last
section and is not on the site at all.

Evidence for what is actually interesting:
- The outside contributor runs it as a **server for agents** (all three PRs fix
  server paths).
- The top referrer is an LLM chat product, so README/page copy is what gets
  quoted — it must be accurate and distinctive.
- `FEEDBACK.md`: parallel agents claiming tasks atomically across 50+ KBs and
  then filing usability reports against the tool. The agent → friction → fix
  loop is the project's most unusual property and is not mentioned anywhere.
- ADR-0014 ("primary consumers are AI agents") and ADR-0019 (human review is the
  constraint — Theory of Constraints) are the thesis; neither is on the page.

## Direction

Lead with "knowledge your agents can write to, and you can verify"; newsroom
origin as proof; drop "second brain". One primary audience.

## Sequencing

After the security fixes (done, `ca0289e`), the MCP tool fixes (done) and the
contributor docs pass — you cannot sell verified, permissioned writes on top of
crashing tools. Page facts (tool and test counts, the no-flag
`pyrite search "career transition"` example, the cascade use case) are covered
by [[docs-counts-generated-or-asserted-from-code]].

Source: 2026-09-17 project review (three read-only audits: docs/contributor, public-repo, code-health). See `kb/positioning/` and the ADR-0031 review response.

## Groom 2026-09-18 (serial)

**Acceptance:** the item's Direction, as the test of the draft — leads with "knowledge your agents can write to, and you can verify"; the newsroom origin as proof; "second brain" gone; one primary audience named. In-repo only: `README.md`'s opening (title block through the first "why" section). pyrite.wiki is outside this repo.
**Regimes:** docs-only — none beyond `tests/test_docs_facts.py` (once it exists) staying green: the rewrite must not reintroduce a count or a name the test then has to chase.
**Touches** — existing: `README.md` (opening only), this item.
**Sequence:** last of the 0.24.2 docs line — after packaged-web-ui-3 and the docs-facts theme (all three edit `README.md`; this one frames facts the other two fix).
**Model:** opus — and the deliverable is **a draft PR for the maintainer to rewrite in his own voice**, not an auto-merged change: this is the paragraph that gets quoted by LLM referrers. **heavy:** no. **Cold read:** no (the maintainer is the review). **Size:** S, ~80 lines.
**Decision flagged:** whether the maintainer wants a worker's draft at all, or writes it himself — asked in `kb/notes/serial-queue-2026-09-18.md`.
**Out of scope:** the site; the "Why Pyrite" grid beyond the opening; any fact correction (docs-facts owns those).
