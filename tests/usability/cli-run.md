# CLI run sheet — Powell lineage usability test

Surface: `pyrite search` / `pyrite get` / `pyrite backlinks`, CLI, stdio.
Protocol: `powell-lineage-search-usability.md`.

Run the task cold — do not read the ground truth first. Record every call, including the ones that
failed. Append findings to `FEEDBACK.md` per `tcp-skills:hallway-agent-testing` and commit
separately.

## Setup

```bash
cd /Users/markr/tcp-kb-internal
pyrite orient -k cascade-research        # recommended first call — test whether it earns that
```

Use `--debug` on every search (gives mode, actual mode, fallback reason, latency, relaxed flag) and
`--fields id,title,entry_type,importance` to keep output readable. **Note how long it takes you to
discover `--fields`** — on the baseline run it was found on a second reading of `--help` and was the
single biggest improvement to the session.

## Baseline (2026-09-18, claude-opus-5, KB cascade-research @ 3,576 entries)

Reference numbers for comparison. A later run diverging from these is itself a finding.

**Latency, same query (`"detention pipeline county"`, `-n 5`):**

| mode | latency |
|---|---|
| keyword | 49.4 ms |
| semantic | 6,001.98 ms |
| hybrid | 8,033.17 ms |

Other runs: semantic 11,144 ms, hybrid 13,337 ms. **~120-270x keyword.** Nothing outside `--debug`
hints at this.

**The planted semantic probes** (`-m semantic -n 10`) — three paraphrases of the memo's own thesis:

| query | returned | Powell entry? |
|---|---|---|
| business must organize politically against critics of free enterprise | 3 | no |
| corporations should fund think tanks to shift public opinion | 3 | no |
| long-term coordinated business counterattack on universities and media | 7 | no |

`-m keyword "Powell memorandum"` returns `1971-08-23-powell-memo` at **rank 1**, 10/10 results.

**Type filter ([#53](https://github.com/markramm/pyrite/issues/53)), query `"accountability bypass"`, `-n 8`:**

| mode | `--type theme` | `--type bogus-xyz` |
|---|---|---|
| keyword | 8, all theme | **0** (correct) |
| semantic | 8 (7 theme, 1 mechanism) | **8, identical** |
| hybrid | 8 (7 theme, 1 mechanism) | **8, identical** |

**`backlinks 1971-08-23-powell-memo`** → 24 entries / 7 types (7 actor, 5 note, 4 organization,
4 mechanism, 2 statistic, 1 scene, 1 event). Best single call in the baseline run for this task.

## Specific things to exercise

1. **Entry-point discovery.** How many calls to `1971-08-23-powell-memo`? Which mode got you there?
2. **The three probes**, in all three modes. Does hybrid recover what semantic missed, or does
   semantic noise displace good keyword hits?
3. **The silent under-return.** `-n 10` → 3 results. Can you find *why* from the CLI alone? Is there
   a threshold flag? Does `--debug` explain it? (Baseline: it does not.)
4. **`--type` while filtering to `theme`** — per #53 you will get unfiltered results in
   semantic/hybrid. Would you have *noticed* mid-task if you didn't know?
5. **`backlinks`** — if you find it unprompted, record what prompted you. If you don't reach for it
   until stuck, that is the finding.
6. **Long-entry handling.** `pyrite get 1971-08-23-powell-memo` returns **34.6 KB**. There is no
   summary/excerpt option. Note what you did instead (baseline: fell back to `sed`/`grep` on the
   file, i.e. left the tool).
7. **Context cost.** Default JSON is ~20 fields per result. At `-n 20` that is ~400 lines to answer
   "what's in here about X."

## Known trap — do not report it as a tool bug

On the baseline run I piped `get` through a Python parser that printed `title=None bodylen=0` and
briefly concluded `get` returns empty bodies. **It does not.** I had mistyped the entry id; `get`
correctly returned `{"error": "...", "error_code": "NOT_FOUND"}` and my parser swallowed it.

Two real lessons, both worth testing deliberately:

- **Verify error handling before reporting it.** `pyrite get totally-bogus-id -k cascade-research`
  returns a proper `NOT_FOUND` payload — but **exit code 0**, so `$?` branching will not catch it.
  Worth confirming whether that is intended.
- **Long ids get truncated in your own notes.** The theme id ends `...powell-memo-to-moral-majority`;
  a display-truncated copy (`...powell-memo-to-`) produced a near-miss id that failed. Ids here run
  to 100+ characters. Does anything support prefix/fuzzy id resolution? (Baseline: no.)

## Report

Per-call log; calls-to-first-correct-entry; total wall-clock; scoring table from the protocol; and
the failed queries. Separate **observations** from **conclusions** — "returned 3 results" is an
observation; "there is a similarity threshold" is a conclusion that may be wrong.
