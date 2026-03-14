---
name: fact-checker
description: "Use when verifying claims in a journalism-investigation KB. Evaluates unverified claims, searches for corroborating evidence, updates claim status and confidence, and creates evidence entries linking claims to sources."
---

# Fact-Checker Skill

Claim verification methodology for journalism-investigation Pyrite knowledge bases. Produces a verification report with traceable evidence chains and confidence assessments.

**Announce at start:** "I'm using the fact-checker skill."

**Methodology:** Identify → Gather → Document → Evaluate → Cross-Check

**The non-negotiable rule:** Never change a claim's status without creating at least one evidence entry first. The evidence chain must be traceable: claim → evidence → source. No shortcuts.

---

## Phase 1: Identify Claims to Verify

Find unverified claims and select which to process.

**Using MCP tools (preferred when available):**

Use the `investigation_claims` MCP tool to list claims filtered by status.

**Using CLI:**

```bash
# List all unverified claims
pyrite investigation claims --status unverified -k <kb>

# See all claims to understand the landscape
pyrite investigation claims -k <kb>
```

**Prioritization rules:**

1. High-importance claims first (claims tagged `priority:high` or linked to active investigation threads)
2. Among equal importance, oldest unverified claims first
3. Claims with partial evidence already collected come before cold claims

**Present to user:**

```
UNVERIFIED CLAIMS FOUND: <count>

Recommended next:
1. [[claim-id-1]] — "<assertion>" (importance: high, age: 14 days)
2. [[claim-id-2]] — "<assertion>" (importance: medium, age: 30 days)
3. [[claim-id-3]] — "<assertion>" (importance: medium, age: 7 days)

Select a claim to verify, or I'll start with #1.
```

If the user does not specify, begin with the highest-priority claim.

---

## Phase 2: Gather Evidence

Collect everything relevant to the claim under review.

### 2a: Read the claim

```bash
pyrite get <claim-id> -k <kb>
```

Extract from the claim entry:
- The assertion text (the specific factual statement)
- Named entities (people, organizations, places, dates)
- Any existing `evidence_refs` already linked
- The source that originated this claim

### 2b: Check existing evidence chain

Use the `investigation_evidence_chain` MCP tool to see what evidence already exists for this claim.

```bash
pyrite investigation evidence-chain <claim-id> -k <kb>
```

If evidence entries already exist, read each one. Do not duplicate work.

### 2c: Search for corroborating evidence

Search broadly, then narrow. Use multiple strategies:

```bash
# Search the assertion text directly
pyrite search "<claim assertion>" -k <kb>

# Search for key entities mentioned in the claim
pyrite search "<person name>" -k <kb>
pyrite search "<organization>" -k <kb>

# Semantic search for conceptually related content
pyrite search "<claim assertion>" -k <kb> --mode semantic

# Cross-KB correlation search
pyrite investigation search --correlate -k <kb>

# Find source documents that might corroborate
pyrite investigation sources -k <kb>

# Look up entities mentioned in the claim
pyrite investigation entities -k <kb>

# Search across all investigation KBs
pyrite investigation search-all "<key phrase>"
```

### 2d: Search for contradicting evidence

This is equally important. Actively look for information that challenges the claim:

```bash
# Search for the opposite or alternative
pyrite search "<negation or alternative>" -k <kb>
pyrite search "<entity> NOT <claimed relationship>" -k <kb> --mode semantic
```

### 2e: Follow the source chain

For each piece of evidence found:

1. Read the full entry: `pyrite get <entry-id> -k <kb>`
2. Check what source document backs it: follow `source_document` refs
3. Assess the source tier:

| Tier | Type | Examples |
|------|------|---------|
| 1 | Primary / direct evidence | Court filings, official records, corporate filings, government documents |
| 2 | Established reporting | Bylined investigative journalism, government reports, academic papers |
| 3 | Secondary analysis | Think tank reports, expert commentary, analytical blog posts |
| 4 | Unverified | Anonymous tips, social media posts, unattributed claims |

4. Check if the source is independent (not derived from the same origin as another source)

**Gather completeness check:**

```
- [ ] Read the claim entry fully
- [ ] Checked existing evidence chain
- [ ] Searched claim assertion text (keyword + semantic)
- [ ] Searched each named entity in the claim
- [ ] Used cross-KB correlation search
- [ ] Looked for contradicting evidence
- [ ] Assessed source tier for each piece of evidence
- [ ] Verified source independence (no circular sourcing)
```

---

## Phase 3: Create Evidence Entries

For every piece of evidence found -- corroborating or contradicting -- create an evidence entry. This is mandatory. The evidence chain must be documented before any status change.

```bash
pyrite create -k <kb> -t evidence --title "<concise description of what this evidence shows>" \
  -b "<detailed description of the evidence, what it says, where it comes from>" \
  -f evidence_type=document \
  -f source_document="[[source-id]]" \
  -f reliability=<high|medium|low> \
  --tags "evidence,<claim-topic>"
```

**Evidence types:**

| evidence_type | When to use |
|---------------|-------------|
| `document` | Evidence from a specific document or record |
| `testimony` | Statements from identified individuals |
| `data` | Statistical data, financial records, datasets |
| `media` | Photographs, video, audio recordings |
| `circumstantial` | Indirect evidence that supports inference |

**Reliability assessment:**

| Level | Criteria |
|-------|----------|
| `high` | Tier 1-2 source, verifiable, no known issues with provenance |
| `medium` | Tier 2-3 source, or Tier 1 source with minor provenance questions |
| `low` | Tier 3-4 source, unverifiable, or source with known reliability issues |

After creating evidence entries, link them to the claim by updating the claim's `evidence_refs`:

```bash
pyrite update <claim-id> -k <kb> -f evidence_refs="[[evidence-id-1]],[[evidence-id-2]]"
```

---

## Phase 4: Evaluate and Update Claim

Apply verification rules based on the evidence collected. These rules are not suggestions -- follow them consistently.

### Verification decision matrix

| Condition | New Status | Confidence |
|-----------|-----------|------------|
| 2+ independent sources from different tiers, no contradictions | `corroborated` | `high` |
| 2+ independent sources from the same tier (Tier 1 or 2) | `corroborated` | `high` |
| 2+ independent sources spanning Tier 1 and Tier 2 | `corroborated` | `high` |
| 2+ independent sources from Tier 2-3, no contradictions | `partially_verified` | `medium` |
| 1 source from Tier 1-2, no contradictions | `partially_verified` | `medium` |
| 1 source from Tier 3 only | `partially_verified` | `low` |
| Contradicting evidence found from credible sources | `disputed` | `low` |
| Only Tier 4 sources, no corroboration | remains `unverified` | `low` |
| Evidence actively disproves the claim | `refuted` | `high` |

### Update the claim

```bash
pyrite update <claim-id> -k <kb> \
  -f claim_status=<new-status> \
  -f confidence=<high|medium|low>
```

### Record the reasoning

Add a verification note to the claim body explaining why this status was assigned. Include:
- How many independent sources were found
- What tiers those sources represent
- Whether any contradictions exist
- What gaps remain

---

## Phase 5: Cross-Claim Contradiction Detection

After verifying a claim, check whether it contradicts other claims in the KB. This step catches inconsistencies that single-claim verification misses.

```bash
# Search for other claims about the same entities
pyrite investigation claims -k <kb>
pyrite search "<entity from verified claim>" -k <kb> --mode semantic

# Check for claims about the same event or relationship
pyrite search "<event or relationship>" -k <kb>
```

**For each potential contradiction found:**

1. Read both claims fully
2. Determine if they genuinely contradict (not just different aspects of the same truth)
3. If contradicted, update both claims:

```bash
# Add disputed_by reference to each claim
pyrite update <claim-id-1> -k <kb> -f disputed_by="[[claim-id-2]]"
pyrite update <claim-id-2> -k <kb> -f disputed_by="[[claim-id-1]]"
```

4. Consider whether the contradiction changes either claim's status

---

## Verification Report

After completing all phases, produce a verification report. This is the primary output.

```
## Claim: <title>
ID: [[claim-id]]
Assertion: <assertion text>
Previous status: <old-status> → New status: <new-status>

### Evidence found:
1. [[evidence-id-1]] — <description> (source: [[source-id]], tier: 1, reliability: high)
2. [[evidence-id-2]] — <description> (source: [[source-id]], tier: 2, reliability: medium)

### Confidence: <high|medium|low>
Reason: <why this confidence level — cite number of sources, tiers, independence>

### Contradictions: <none found | list of contradicting claims>

### Gaps:
- <what evidence would strengthen or weaken this claim>
- <what sources were searched but yielded nothing>
```

---

## Key MCP Tools Reference

These are the JI plugin MCP tools available for claim verification:

| Tool | Purpose | Phase |
|------|---------|-------|
| `investigation_claims` | List and filter claims by status, KB | Phase 1 |
| `investigation_evidence_chain` | Trace claim → evidence → source links | Phase 2 |
| `investigation_sources` | Find source documents in the KB | Phase 2 |
| `investigation_entities` | Look up entities mentioned in claims | Phase 2 |
| `investigation_search_all` | Cross-KB search for corroboration | Phase 2 |
| `investigation_create_claim` | Create new claims discovered during verification | As needed |
| `investigation_log_source` | Log new source documents found | Phase 3 |

---

## Anti-Patterns

| Trap | Fix |
|------|-----|
| Changing claim status without evidence entries | Always create evidence entries first. The chain must be: claim → evidence → source. |
| Auto-verifying because "it sounds right" | Apply the decision matrix. No evidence, no status change. |
| Ignoring contradicting evidence | Contradictions are findings. Document them. Update both claims. |
| Treating quantity of Tier 4 sources as quality | Five anonymous social media posts do not equal one court filing. Apply the tier system. |
| Verifying claims about yourself or your own analysis | Circular verification. Only external sources count. Your analysis is not evidence. |
| Skipping the evidence entry creation | Every piece of evidence gets an entry. This is what makes the chain auditable. |
| Counting derived sources as independent | If Source B cites Source A, you have one source, not two. Trace origins. |
| Upgrading confidence without new evidence | Confidence reflects evidence quality, not your feeling. New status requires new evidence. |
| Silently dropping claims you cannot verify | "Remains unverified" is a valid and important finding. Report it. |
