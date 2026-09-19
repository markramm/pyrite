---
id: adr-0035
type: adr
title: "Writes are eventually-embedded: auto_embed guarantees embedding, not synchrony"
adr_number: 35
status: proposed
date: 2026-09-19
---

# ADR-0035: Writes are eventually-embedded: auto_embed guarantees embedding, not synchrony

## Context

`settings.auto_embed` (default `True`, `config.py:350`) currently means *this write
blocks until the entry is embedded*. `KBService._auto_embed` (`kb_service.py:140`)
takes the synchronous branch whenever `self._embedding_worker is None`, and a grep
over `pyrite/` shows nothing in production ever sets that attribute — so the
synchronous branch is the only branch that runs, on every surface.

The consequence is #13: on a fresh install the first write imports torch and
downloads the ~90 MB sentence-transformers model *inside the request*, and
`POST /api/entries` blocks for over a minute. #43 is the same trade-off seen from
`pyrite init`: the tutorial's first write pays the same cost, or (with the model
absent and the network unavailable) silently fails to embed and a later
`--mode semantic` returns `[]` with no explanation.

The obvious fix — start a background thread that drains the embed queue — collides
with #102: `index_worker.py` already leaves an unjoined daemon thread holding its
own `index.db` connection, and that race is a live defect, not a pattern to copy.
It also has no honest answer on the one-shot CLI path, where the process exits
before any background work could finish.

Two measurements from the 2026-09-19 spike make the choice tractable:

- `EmbeddingWorker` is a **queue, not a thread**. Constructing one costs 53 ms,
  spawns zero threads and imports no torch; `process_batch()` is a plain
  synchronous method a caller must invoke. There is no lifecycle to own.
- With a worker attached and `auto_embed: true`, a `create_entry` on a cold
  process takes **17 ms**, imports **no** torch or sentence-transformers module,
  leaves the entry immediately keyword-searchable, and records one `pending` row
  in `embed_queue`.

So the fast path is already implemented; it is reachable only through an attribute
nothing assigns.

## Decision

**`auto_embed: true` guarantees that an entry will be embedded, not that it is
embedded when the write returns.** Concretely:

1. A write with `auto_embed: true` enqueues the entry in `embed_queue` and returns.
   It never loads the embedding model and never blocks on the network.
2. The debt is visible: `GET /api/index/embed-status` reports the pending count,
   and `pyrite index embed` / `pyrite index sync` / `pyrite index build` drain it.
   The server additionally drains the queue from the existing
   `prewarm_embeddings` startup hook and at the end of `POST /api/index/sync`.
3. **No new background thread is introduced.** Draining happens on paths that
   already exist and already have a caller who can wait for them. This keeps
   #102's hazard from being duplicated and gives the server, MCP and one-shot CLI
   paths the same answer instead of three.
4. `auto_embed: false` keeps its present meaning exactly: no embedding stack is
   touched at all, nothing is enqueued, keyword search only. The test suite's
   3m37s → 45 s win depends on this and must not regress.
5. Semantic search on a KB with zero embeddings stops returning a silent `[]`.
   `SearchService.search` already records `reason: "semantic_empty_no_embeddings"`
   in its trace; that becomes a `warnings` entry naming `pyrite index embed`,
   using the `warnings: list[str]` out-parameter and response field introduced by
   PR #145 — not a new mechanism.

## Consequences

**Easier.** A fresh install is usable immediately: the first write returns in
milliseconds and the entry is keyword-searchable at once, with or without a model
on disk and with or without a network. The embedding cost moves to a moment the
user chose (`index embed`, a server start with prewarm, an explicit sync) instead
of ambushing the first write. One switch still governs the whole behaviour. The
existing `embed_queue`, `embed-status` endpoint and `index embed`/`index sync`
auto-embed calls all become load-bearing rather than vestigial.

**Harder.** Semantic search is now eventually-consistent: an entry written a second
ago may not be findable by meaning until a drain runs. Callers who need
read-after-write semantic visibility must drain explicitly; the `warnings` field
is how they learn they are behind. Two states now exist that previously did not —
"indexed but not embedded", and a `failed` queue row after `max_attempts` — and
both need to be legible in `index health` and `embed-status` rather than silent.
The queue is per-`index.db`, so a KB whose index is rebuilt from files loses
pending rows; `index build`'s existing auto-embed covers that, but it is a
coupling to remember.

**Rejected alternative.** Start a background drain thread on write. It buys
read-after-write semantic visibility, at the cost of a second unjoined daemon
thread holding an `index.db` connection (#102), a shutdown contract the one-shot
CLI cannot honour, and divergent behaviour between the server, MCP and CLI paths —
the "two switches" outcome this ADR exists to avoid.

## Related

- Issue #13 — first write on a fresh install blocks over a minute downloading the model
- Issue #43 — `pyrite init` / fresh-KB side of the same trade-off
- Issue #102 — `submit_sync` leaves an unjoined daemon thread (the hazard not copied here)
- PR #35 — introduced `settings.auto_embed`
- PR #145 — introduced the `warnings` out-parameter this ADR reuses
