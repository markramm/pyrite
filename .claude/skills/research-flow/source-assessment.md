# Source Assessment Rubric

Use this rubric when evaluating entries found during research. Every claim in a synthesis should reference its sources with an assessed reliability level.

## Reliability Tiers

### Tier 1 — Primary Sources (Most Reliable)

Direct evidence: official documents, first-person accounts, raw data, court filings, public records.

**In the KB:** Entries of type `document` with clear provenance, entries with `source` metadata linking to verifiable originals.

**Weight:** Can stand alone. A single Tier 1 source supports a High confidence finding.

### Tier 2 — Established Reporting

Bylined reporting from known outlets, academic papers, government reports, investigative journalism with named sources.

**In the KB:** Entries citing specific articles or reports with dates and authors.

**Weight:** Two or more agreeing Tier 2 sources support a High confidence finding. A single Tier 2 source supports Medium confidence.

### Tier 3 — Secondary Analysis

Commentary, op-eds, think tank reports, blog posts from domain experts. Useful for interpretation, not for establishing facts.

**In the KB:** Entries that analyze or interpret other entries. Notes synthesizing patterns.

**Weight:** Supports Medium confidence at best. Never sufficient alone for High confidence findings.

### Tier 4 — Unverified / Uncertain

Anonymous sources, social media posts, unattributed claims, hearsay, entries without clear provenance.

**In the KB:** Entries without `source` metadata, notes without attribution, imported content of unknown origin.

**Weight:** Low confidence only. Flag as requiring corroboration.

---

## Assessment Checklist

For each source used in a synthesis:

```
Source: [[entry-id]]
Tier: 1 / 2 / 3 / 4
Provenance: Where did this information originate?
Date: When was it created/published?
Corroboration: What other sources agree/disagree?
Caveats: Known biases, limitations, or conflicts of interest?
```

## Corroboration Rules

| Scenario | Confidence |
|----------|------------|
| 2+ Tier 1 sources agree | High |
| 1 Tier 1 + 1 Tier 2 agree | High |
| 2+ Tier 2 sources agree | High |
| 1 Tier 2, no contradictions | Medium |
| Tier 3 only, multiple agree | Medium |
| Single Tier 3 or any Tier 4 | Low |
| Sources contradict each other | Note contradiction, investigate further |

## Red Flags

- **Circular sourcing** — Two entries that both cite the same underlying source aren't independent corroboration
- **Temporal distance** — A source written years after the event is less reliable than contemporaneous accounts
- **Missing provenance** — If you can't trace where a claim originated, treat it as Tier 4
- **Selection bias** — If you only searched one KB or one search mode, your sources may be skewed
