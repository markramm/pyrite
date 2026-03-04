---
id: cryptographic-reviews-agent-trust
type: backlog_item
title: "Spike: Cryptographic reviews and agent web of trust"
kind: feature
status: proposed
priority: low
effort: L
tags: [agents, trust, reviews, federation, spike]
---

# Spike: Cryptographic reviews and agent web of trust

## Goal

Explore a review system that gives AI agents mathematical certainty about knowledge provenance. Agents lack human heuristics for judging staleness or trustworthiness — a computable trust signal attached to every entry would let them operate confidently on KB content.

## Core design (from exploration)

Reviews are **not** a protocol mixin or base class field. They're infrastructure built from existing primitives:

1. **`review` entry type** — standalone entries with `target_id`, `target_blob_hash`, `status`, `reviewed_at`. Stored in their own collection, append-only.
2. **Link with `relation: "reviews"`** — connects review to target. Backlinks discovery works automatically via existing `pyrite backlinks`.
3. **Query-layer trust enrichment** — when returning any entry via MCP or API, check for review backlinks, compare current `git hash-object` against stored blob hash, attach trust context.

No entry type needs to opt in. Every entry is reviewable by virtue of the review system existing.

## Trust context (proposed MCP response enrichment)

```json
{
  "id": "adr-0004",
  "title": "Use SQLite FTS5 for Search",
  "trust_context": {
    "current_blob_verified": true,
    "reviews": [
      {"author": "markramm", "status": "approved", "age_days": 12, "blob_match": true},
      {"author": "qa_agent_01", "status": "approved", "age_days": 3, "blob_match": true}
    ]
  }
}
```

Transparent array format preferred over opaque score — let the consuming agent decide its own trust threshold.

## Blob hash binding

Each review captures `git hash-object` of the target file at review time. If the file changes by a single byte, the hash no longer matches and `current_blob_verified` flips to `false`. Binary, fast, no heuristics.

## Layered approach to crypto

1. **v1:** Reviews as entries + blob hash binding + trust context enrichment. No custom crypto.
2. **v1.5:** Verify git commit signatures on review entries as optional trust signal.
3. **v2:** Standalone cryptographic signatures (ed25519 keypairs) for federation across repos.

Don't build key management until federation is actually needed.

## Spike scope

- Draft ReviewEntry type (fields, to/from frontmatter)
- Prototype blob hash capture and verification
- Prototype trust context enrichment in `kb_get` MCP tool
- Evaluate: does the transparent review array give agents enough signal, or is a computed score needed?
- Identify what (if anything) needs to change in base Entry or IndexManager

## Open questions

- Trust score: opaque number vs transparent array? Start with array, see if agents need a single number.
- Staleness decay: should old reviews on unchanged files lose trust weight over time?
- Who configures trust graph weights in federated case? Per-KB, per-repo, per-agent?
- Should `pyrite review <entry-id>` be a core CLI command or extension?
