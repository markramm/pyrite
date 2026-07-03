# journalism-investigation

**Status: architecture spike (closed 2026-07) + reference extension.**

Built 2026-03 to explore how FollowTheMoney-class problems (typed
entities, edge relationships, claims/evidence, Aleph interop) fit
pyrite's extensibility framework. The exploration succeeded — it
forced edge entities into core (ADR-0022), stress-tested the plugin
protocol at full width, and exposed the type-scoping gaps now
tracked in `kb/backlog/plugin-type-resolution-scoping.md`. Findings
and disposition: `kb/notes/ji-spike-findings.md`.

**What's load-bearing:** `InvestigationEventEntry` (base class of
the cascade extension's `timeline_event` — thousands of production
entries), `query_network`, the edge-type declarations.

**What's exploratory:** the claims/evidence chain, financial layer,
money-flow/ownership analytics, source-reliability system, FtM
import/export, and the `pyrite investigation` CLI are unused in
production and not maintained as product surface. They stay tested
and compiling as the framework's reference implementation.
FtM/Aleph interop is a Future roadmap idea, gated on a pilot peer
asking for it by name.

This extension is the recommended worked example for plugin
authors: a declarative plugin shell (`plugin.py`) delegating to pure
query modules, per-domain entry types, MCP tool contribution across
tiers, hooks, validators, and KB presets.
