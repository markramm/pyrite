---
id: relabel-social-zettelkasten-and-encyclopedia-as-example-plugins-wording-only-no
title: Relabel social, zettelkasten and encyclopedia as example plugins (wording only, no moves)
type: backlog_item
tags:
- docs
- extensions
- positioning
importance: 5
status: proposed
priority: medium
rank: 0
---

Nobody uses the `social`, `zettelkasten` and `encyclopedia` extensions. The
maintainer's call (2026-09-19): **relabel, don't remove** — say plainly in the
docs and metadata that they are reference examples of the plugin API, so a
reader stops treating them as supported products. Wording only: no import path,
entry point, package name or directory moves.

## Groom 2026-09-19

### Why relabel rather than remove

They are the only worked examples of a plugin that adds entry types, CLI
commands, MCP tools, a preset and DB tables. `kb/standards/extension-development.md`
is the written guide; these three are what a plugin author reads next. Deleting
them costs the examples; keeping them unmarked costs credibility, because
`docs/plugins.md` currently presents each with an install line and a "use case"
paragraph aimed at end users ("Researchers, writers, and lifelong learners…",
docs/plugins.md:46) that no one is supported on.

### The surface, verified

- `README.md:182-184` — the extensions table lists the three beside
  `software-kb` and the rest with no distinction.
- `README.md:230` — repository layout line naming all six extensions together.
- `README.md:312-314` — three `pip install -e extensions/<name>` lines.
- `docs/plugins.md:32-90` — the three long sections (Zettelkasten :32,
  Encyclopedia :52, Social :73), each with **Install**, capability lists, a
  **Use case** paragraph and a "Full docs" link to the extension directory.
- `docs/getting-started.md:168-169` — `zettelkasten` and `encyclopedia`
  described as KB presets. **Careful here:** line 39 lists `zettelkasten` as a
  *template* name, which is a functioning CLI value, not a label. Reword the
  descriptive lines; do not touch the template/preset names.
- `extensions/social/pyproject.toml:8`,
  `extensions/zettelkasten/pyproject.toml:8`,
  `extensions/encyclopedia/pyproject.toml:8` — the `description` fields
  ("Everything2-inspired social knowledge base extension for pyrite" etc.).
  These are metadata strings, not entry points; changing them is safe.
- KB components: `kb/components/social-extension.md`,
  `kb/components/zettelkasten-extension.md`,
  `kb/components/encyclopedia-extension.md` (all `kind: package`, surfaced by
  `pyrite sw components`).
- `CHANGELOG.md` — one line under Changed.

**Note for the worker:** these three extensions have **no `README.md` files**
(`extensions/<name>/` contains only `pyproject.toml`, `src/`, `tests/`). The
brief's "extensions/*/README.md headers" does not apply as written. Creating
three new READMEs is the natural way to land the label at the directory a
plugin author actually opens, and `docs/plugins.md:48,69,90` already link there
as "Full docs" — those links currently resolve to a bare directory listing. A
short README per extension (what it demonstrates, "example plugin, not a
supported product", pointer to `kb/standards/extension-development.md`) is
in scope and worth doing. Decide once and apply the same wording to all three.

### Acceptance

- A reader landing on `README.md`, `docs/plugins.md`, `docs/getting-started.md`
  or any of the three extension directories learns within the first sentence
  that `social`, `zettelkasten` and `encyclopedia` are **example plugins**
  demonstrating the plugin API, not supported products, and that
  `software-kb`, `journalism-investigation` and `cascade` are not being
  relabelled.
- `docs/plugins.md` keeps the capability detail (it is the value for a plugin
  author) but its "Use case" framing is rewritten from "who should adopt this"
  to "what this example shows a plugin author".
- The three `pyproject.toml` `description` strings say "example plugin".
- The three `kb/components/*-extension.md` entries carry the same label in
  their body; `pyrite sw components` output is unchanged structurally (still
  `kind: package`).
- `kb/standards/extension-development.md` points at the three by name as the
  worked examples to read.
- Each extension directory has a `README.md` carrying the label (see note above).
- CHANGELOG line under Changed.
- **Nothing changes that a machine consumes:** no package `name`, no
  `[project.entry-points]` table, no module path, no preset name, no template
  name, no CLI command name, no MCP tool name, no directory name.

### Regimes

- **Grep gate (the real test):** after the change, `grep -rn "zettelkasten\|encyclopedia\|pyrite_social" --include=*.py --include=*.toml pyrite/ extensions/*/src/ extensions/*/pyproject.toml` returns the same set of *identifiers* as before — only `description =` strings differ. Paste before/after in the PR body.
- **Suite unchanged:** the extension test suites pass untouched. If any test
  needed editing, the change stopped being wording — stop and report.
- **Install still works:** `pip install -e extensions/zettelkasten` resolves
  (the README lines still name a real path).
- **Docs links resolve:** the three "Full docs" links in `docs/plugins.md` point
  at directories that now contain a README.

### Touches

- existing: `README.md`, `docs/plugins.md`, `docs/getting-started.md`,
  `extensions/social/pyproject.toml`, `extensions/zettelkasten/pyproject.toml`,
  `extensions/encyclopedia/pyproject.toml`, `kb/components/social-extension.md`,
  `kb/components/zettelkasten-extension.md`,
  `kb/components/encyclopedia-extension.md`,
  `kb/standards/extension-development.md`, `CHANGELOG.md`
- new: `extensions/social/README.md`, `extensions/zettelkasten/README.md`,
  `extensions/encyclopedia/README.md`

### Sequence

**After the base-frontmatter conformance item.** Same three extensions, and the
point of that item is that these classes currently drop base fields — an example
plugin that demonstrates the API incorrectly is worse than an unlabelled one.
Land the fix, then put the "read this as the example" label on code that is
correct. No file overlap between the two (that one is `src/**/entry_types.py`
and tests; this one is docs, `pyproject.toml` descriptions and KB entries), so
the ordering is about honesty, not merge conflicts — the conductor can overlap
them if the queue demands it, at the cost of labelling wrong examples for a day.

Independent of #173, #175, #180 — no shared files.

### Model

**Sonnet.** Wording with a hard boundary stated above and a mechanical grep gate
to prove the boundary held. A careful junior engineer can do this from the
ticket alone.

heavy: no

### Cold read

**No.** Documentation and metadata strings only; nothing under auth, storage or
server, and the acceptance explicitly forbids touching any machine-consumed
name. The grep gate is the evidence.

### Out of scope

- **Moving or renaming the directories** — the maintainer deferred that to after
  the 0.24.2 release. Explicitly not this ticket.
- Deleting the extensions, their tests, their CLI commands or their MCP tools.
- Changing entry point tables, package names, preset names or template names
  (`zettelkasten` is a live template value at `docs/getting-started.md:39`).
- Relabelling `software-kb`, `journalism-investigation` or `cascade`.
- Deprecation warnings at import time — a label is documentation, not runtime
  behaviour. If a warning is wanted, that is a separate decision.
- Fixing the entry classes (the sibling item owns that).
