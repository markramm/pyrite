---
name: investigation
description: "Use when investigating a specific entity (person, organization, event) across Pyrite knowledge bases. Enforces source chain tracking, relationship mapping, and confidence-rated findings. Every claim must link to a source."
---

# Investigation Skill

Entity-focused investigation methodology for Pyrite knowledge bases. Produces a sourced entity profile with mapped relationships and confidence-rated findings.

**Announce at start:** "I'm using the investigation skill."

**Methodology:** Identify → Collect → Map → Track → Assess

**The non-negotiable rule:** Every factual claim in the output must link to a source entry via `[[wikilink]]`. No exceptions. If there's no source entry, create one first.

---

## Phase 1: Identify Target

Define exactly what entity you're investigating.

```
TARGET DEFINITION:
- Entity name:
- Entity type: person / organization / event / topic
- What specifically do we want to know?
- What KBs are likely relevant?
- Known aliases or alternate names:
```

Check if the entity already has an entry:

```bash
pyrite search "<entity name>" --limit 20
pyrite search "<entity name>" --mode=semantic --limit 10
```

If an entry exists, read it fully: `pyrite get <entry-id>`

Create a task list with TaskCreate to track investigation progress.

---

## Phase 2: Collect Mentions

Systematically find every reference to this entity across all KBs.

```bash
# Direct name search
pyrite search "<entity name>" --limit 50

# Search aliases and alternate spellings
pyrite search "<alias>" --limit 20

# Search by role/title if a person
pyrite search "<role or title>" --type=person --limit 20

# Search related organizations
pyrite search "<org name>" --limit 20

# Timeline search for events involving this entity
pyrite timeline --from=<start> --to=<end>

# Backlinks from known entries
pyrite backlinks <entity-entry-id> --kb=<name>

# Tag-based discovery
pyrite search "<entity>" --tag=<relevant-tag>
```

**For each mention found:**

1. Read the full entry
2. Extract: what does this entry claim about the entity?
3. Note the source tier (see [entity-profile-template.md](entity-profile-template.md))
4. Record the entry ID for the source chain

**If the entity has no entry yet, create one:**

```bash
# Person
pyrite create --kb=<name> --type=person --title="<Full Name>" \
  --body="<initial summary>" --tags="<relevant-tags>" \
  --field role="<primary role>"

# Organization
pyrite create --kb=<name> --type=organization --title="<Org Name>" \
  --body="<initial summary>" --tags="<relevant-tags>"
```

**Collection completeness check:**

```
- [ ] Searched all relevant KBs
- [ ] Searched name + known aliases
- [ ] Searched related entities (employers, associates, counterparts)
- [ ] Checked backlinks from entity's own entry
- [ ] Checked timeline for temporal context
- [ ] Created entries for important sources not yet in the KB
```

---

## Phase 3: Map Relationships

Document how this entity connects to others.

For each relationship discovered:

| From | Relationship | To | Source | Confidence |
|------|-------------|-----|--------|------------|
| `[[entity]]` | employs / funds / opposes / etc. | `[[other-entity]]` | `[[source]]` | High/Med/Low |

```bash
# Find connections through shared tags
pyrite tags --kb=<name>

# Find connections through shared events
pyrite search "<entity>" --type=event

# Trace through backlinks
pyrite backlinks <entity-id> --kb=<name>
pyrite backlinks <related-entity-id> --kb=<name>
```

See [relationship-mapping.md](relationship-mapping.md) for relationship type vocabulary and mapping techniques.

**Mapping checklist:**

```
- [ ] Direct relationships documented (employer, colleague, opponent, etc.)
- [ ] Indirect relationships noted (shared events, shared organizations)
- [ ] Temporal relationships mapped (preceded by, succeeded by, concurrent with)
- [ ] Each relationship has a source entry
- [ ] Relationship strength/confidence noted
```

---

## Phase 4: Track Source Chain

Every claim needs a traceable path back to evidence. This is what separates investigation from speculation.

**Source chain format:**

```
Claim: "<factual statement>"
Source: [[entry-id]] (Tier 1/2/3/4)
Corroboration: [[other-entry-id]] or "none"
```

**Tier definitions:**

| Tier | Type | Example |
|------|------|---------|
| 1 | Primary / direct evidence | Official documents, court filings, public records |
| 2 | Established reporting | Bylined journalism, government reports, academic papers |
| 3 | Secondary analysis | Commentary, think tank reports, expert blog posts |
| 4 | Unverified | Anonymous sources, social media, unattributed claims |

**Source chain rules:**

- A claim with only Tier 4 sources must be flagged as "unverified"
- A claim with contradicting sources must note the contradiction
- "Common knowledge" is not a source — find the entry or create one
- If you can't find a source, say "no source found" — don't omit the claim silently

---

## Phase 5: Assess and Produce Profile

Create the entity profile entry using the template from [entity-profile-template.md](entity-profile-template.md).

```bash
pyrite update <entity-id> --kb=<name> --body="<updated profile>"
```

Or if creating a new investigation summary:

```bash
pyrite create --kb=<name> --type=note --title="Investigation: <entity>" \
  --body="<profile content>" --tags="investigation,<entity-tags>"
```

**Assessment checklist:**

```
- [ ] Every factual claim links to a source via [[wikilink]]
- [ ] Confidence level assigned to each major finding
- [ ] Contradictions between sources explicitly noted
- [ ] Gaps in knowledge explicitly stated
- [ ] Relationships mapped with sources
- [ ] Timeline of key events constructed
- [ ] Unverified claims flagged clearly
```

---

## Anti-Patterns

| Trap | Fix |
|------|-----|
| Writing claims without source links | Every claim gets a `[[source]]`. No exceptions. |
| Treating all mentions as equal weight | Apply tier system. A Tier 4 mention ≠ a Tier 1 document. |
| Ignoring absence of evidence | "No entries found about X's role in Y" is a finding. Document gaps. |
| Circular investigation | If Entry A cites Entry B which cites Entry A, you have one source, not two. |
| Scope creep | Stay focused on the target entity. Note related entities for follow-up, don't investigate them now. |
| Unsourced relationship claims | "X is connected to Y" needs a source entry showing the connection. |
