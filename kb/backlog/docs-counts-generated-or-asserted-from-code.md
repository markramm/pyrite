---
id: docs-counts-generated-or-asserted-from-code
title: Docs counts generated or asserted from code
type: backlog_item
tags:
- documentation
- testing
- ci
- programmatic-validation
links:
- target: mcp-tool-dispatch-smoke-test-every-registered-tool
  relation: related
  kb: pyrite
importance: 5
kind: improvement
status: proposed
priority: medium
effort: S
rank: 0
---

## Problem

Counts in the docs are written once and never revisited. On 2026-09-17:

| Claim | Where | Actual |
|---|---|---|
| "~2500 tests" | `README.md:317` | 3182 in `tests/` + 899 in extensions |
| "22 ADRs" | `README.md:331` | 31 |
| "Ten built-in entry types" | `README.md:157` | 11 (`task` is registered in core) |
| `get_entry_classes()`, `get_cli_app()` | `README.md:163,167` | `get_entry_types()`, `get_cli_commands()` |
| extensions list includes `task`, omits `journalism-investigation` | `README.md:226` | six in `extensions/`, no `task` |
| "24 MCP tools (14 / +6 / +4)", "1500+ tests" | pyrite.wiki | 48 (29 / +11 / +8); ~4080 |
| "583 tests, 11 ADRs" | `kb/positioning/README.md`, `UPSTREAM_CHANGES.md` | as above |
| `__version__ = "0.12.0"` | `pyrite/__init__.py:7` | `pyproject.toml` 0.24.1; `web/package.json` and `pyrite-mcp` 0.20.0 |
| "tracked" flaky-test ticket | `CLAUDE.md` | ticket is in `backlog/done/` |

This has been fixed by hand before ([[fix-readme-for-release]],
[[docs-onboarding-fiction-sweep]] — both done) and drifted again. A manual
sweep is not a fix; the top GitHub referrer for the repo is chatgpt.com, so
these numbers are what gets quoted to prospective users.

## Proposed validation

Two rules, in order of preference:

1. **Don't state what will drift.** Replace exact counts with links or
   commands where the number adds nothing ("see `pyrite sw adrs`").
2. **Where a number or name earns its place, assert it.** A
   `tests/test_docs_facts.py` that derives each fact from code and checks
   the docs agree:
   - MCP tool counts and names per tier ← `tool_schemas.py`
   - plugin protocol method names and count ← `pyrite/plugins/protocol.py`
   - built-in entry types ← the core registry
   - field types ← `FieldSchema.VALID_TYPES`
   - shipped extensions ← `extensions/*/pyproject.toml`
   - ADR count ← `kb/adrs/`
   - every relative link in `README.md`, `CONTRIBUTING.md`, `docs/` resolves
   - one version: `pyrite.__version__`, `pyproject.toml`,
     `web/package.json`, `pyrite-mcp/pyproject.toml` (or derive
     `__version__` from `importlib.metadata` and delete the literal).

   Test counts cannot be asserted cheaply — apply rule 1 to them.

The pyrite.wiki site lives outside this repo; either generate its stats
block from the same source at build time or drop the stat tiles.

## Acceptance

- [ ] Every row in the table above is corrected or removed.
- [ ] `test_docs_facts.py` fails when a tool is added without the README
      tier table changing (or the table is generated and the test checks it
      is current).
- [ ] A single version source; the test fails on disagreement.
- [ ] Runs in CI on PRs, so an outside contributor's change is held to it.

## Notes

Filed from the 2026-09-17 whole-project review; one of five structural
checks (see [[mcp-tool-dispatch-smoke-test-every-registered-tool]] for the
set).

## Note 2026-09-17

The README numbers were corrected by hand in the docs pass (33 ADRs, ~4100
tests, eleven built-in types, ~40 services, protocol method names). They will
drift again; this ticket is still the fix (assert or generate them).

## Groom 2026-09-18 (serial)

One theme with the remainder of [[single-source-of-truth-for-the-version-asserted-by-a-test]] (tick 6's advice, kept): "docs facts and version discipline are asserted by a test". Closes both items.

**Acceptance:** this item's four criteria, verbatim, with two scopings. (1) "A single version source; the test fails on disagreement" covers `pyrite.__version__`, `pyproject.toml` and `.claude-plugin/plugin.json`; `web/package.json` and `pyrite-mcp/pyproject.toml` stay out — both wait on the ADR-0031 packaging question (the version item's own "Still open" note). (2) From the version item: the top `CHANGELOG.md` version is either `Unreleased` or has a matching git tag. The pyrite.wiki stat tiles live outside this repo: not this theme.
**Regimes:** a shallow clone with no tags (CI's default `fetch-depth: 1`) — the tag assertion must skip with a named reason, not fail and not silently pass; `[Unreleased]` present but empty (the state the changelog-fragments theme creates on `dev`); a relative link with an anchor, a link into `kb/`, and a link inside a fenced code block (not a link); an extension directory without a `pyproject.toml`; a fact stated in two places in the README.
**Touches** — existing: `README.md`, `kb/positioning/README.md`, `UPSTREAM_CHANGES.md`, `CLAUDE.md`, `tests/test_version_consistency.py`, `.claude-plugin/plugin.json`, both backlog items. New: `tests/test_docs_facts.py`.
**Sequence:** after the changelog-fragments theme (it redefines what `[Unreleased]` holds) and after packaged-web-ui-3 (`README.md` — that theme changes the install facts this one asserts). Before the README reposition.
**Model:** sonnet. **heavy:** no. **Cold read:** no. **Size:** M, ~300 lines (test ~180, doc corrections ~120) — at the ceiling; if it grows, the link checker is the piece that splits off.
**Out of scope:** the README's opening (the reposition item); asserting test counts (rule 1: do not state what drifts); `web/package.json`/`pyrite-mcp` versions.
