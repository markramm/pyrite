---
id: ji-investigation-pack-export
title: Investigation pack export for publication and review
type: backlog_item
tags:
- journalism
- investigation
- export
- publishing
links:
- target: epic-core-journalism-investigation-plugin
  relation: depends_on
  kb: pyrite
- target: epic-evidence-and-claims-management
  relation: depends_on
  kb: pyrite
kind: feature
status: accepted
effort: M
---

## Problem

The investigation's artifact is the investigation pack — a structured collection of sourced claims, entity profiles, timelines, and evidence chains. Journalists need to share this with editors, legal review, and eventually publish. The pack must be self-contained, with full source attribution and evidence chains.

## Scope

### Export Formats
- **HTML report** — self-contained, styled, navigable. Includes timeline, entity profiles, claims with evidence, source list
- **PDF** — print-ready version of the HTML report
- **JSON** — structured data export for programmatic consumption
- **Markdown bundle** — directory of markdown files (portable, version-controllable)

### Report Sections
1. Executive summary (investigation scope, key findings)
2. Timeline of events (chronological, with importance weighting)
3. Key entities (profiles with connections)
4. Claims and evidence (status, confidence, evidence chains)
5. Source appendix (all sources with reliability ratings, URL status)
6. Network diagram (static SVG of key relationships)

### Options
- `--redact` — remove sensitive source identifiers, replace with "[Source A]", "[Source B]"
- `--claims-only=corroborated` — only include verified claims
- `--since=DATE` — export only recent additions (for incremental review)
- `--include-disputed` — include disputed claims with dispute context

## Acceptance Criteria

- HTML export is self-contained (no external dependencies)
- Evidence chains are navigable: click claim → see evidence → see source
- Source redaction mode produces clean output with no identifying info
- Export handles investigations with 1,000+ entries
- PDF renders correctly from HTML export
