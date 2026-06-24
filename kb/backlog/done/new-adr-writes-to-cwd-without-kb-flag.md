---
id: new-adr-writes-to-cwd-without-kb-flag
title: "sw new-adr writes ADR to ./adrs when --kb is omitted instead of the KB root"
type: backlog_item
tags: [cli, software-kb, adr, path-resolution]
importance: 5
kind: bug
status: done
priority: medium
effort: S
rank: 0
---

## Problem

`pyrite sw new-adr "<title>"` without `--kb` creates the file at `./adrs/<file>.md`
relative to the current working directory, instead of inside the KB's configured ADR
directory. Run from the pyrite repo root, it created a brand-new `./adrs/` dir at the repo
root while all 27 real ADRs live in `kb/adrs/`. The file then had to be `mv`'d and the
stray dir removed.

This is a **silent-wrong-output** bug, worse than a crash: the command reports
`Created ADR-0028 ... File: adrs/0028-...md` and exits 0, but the file is written somewhere
the KB never indexes — so `pyrite sw adrs`, search, and indexing never see it. The wrong
location even varies with the caller's cwd.

Tell-tale inconsistency: the **numbering** is correct (it picked the right next number, 28)
because the count query defaults the KB, but the **file path** does not use the same
defaulting — so you get a correctly-numbered ADR in the wrong place.

## Root cause

`extensions/software-kb/src/pyrite_software_kb/cli.py:135-141` — KB path is resolved only
when `--kb` is explicitly passed:

```python
kb_path = None
if kb_name:                       # only when --kb given
    kb_conf = config.get_kb(kb_name)
    if kb_conf:
        kb_path = kb_conf.path
if kb_path is None:
    kb_path = Path(".")           # <-- silent cwd fallback
adrs_dir = kb_path / "adrs"
```

Meanwhile the next-number query at `cli.py:122` (`_query_entries(db, "adr", kb_name)`)
handles a `None` `kb_name` fine. So numbering and file-path resolution disagree on how to
treat the no-`--kb` case.

Note also the hardcoded `"adrs"` subdir (`cli.py:143`) ignores the `adr` type's configured
`subdirectory` (`init_command.py:34` / software-kb `preset.py:11` set it to `adrs/`, which
happens to match — but a KB that configured a different ADR subdir would still get `adrs/`).

## Fix

Resolve the KB the same way the numbering query does when `--kb` is omitted: if there is a
single configured KB (or a default/primary KB), use its `.path`; only fall back to `Path(".")`
when no KB can be resolved, and in that case emit a visible warning rather than silently
writing to cwd. Prefer deriving the ADR subdir from the `adr` type's `subdirectory` schema
field instead of the hardcoded `"adrs"`. Add a regression test for the no-`--kb` invocation
(the existing tests at `test_software_kb.py:1917+` all pass `--kb`, which is why this slipped).

## Provenance

Hit 2026-06-23 while creating ADR-0028 via `pyrite sw new-adr` (no `--kb`) from the pyrite
repo root. Diagnosed against `extensions/software-kb/src/pyrite_software_kb/cli.py`.

## Workaround

Pass `--kb <name>` explicitly, or `mv` the file into the KB's `adrs/` dir and remove the
stray `./adrs/` afterward.
