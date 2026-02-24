---
name: research-flow
description: "Use when conducting structured research on a topic across Pyrite knowledge bases. Enforces a Gather-Connect-Analyze-Synthesize methodology with source tracking and confidence assessments."
---

# Research Flow Skill

Structured research methodology for Pyrite knowledge bases. Produces a synthesis entry backed by sourced evidence.

**Announce at start:** "I'm using the research-flow skill."

**Methodology:** Gather → Connect → Analyze → Synthesize

---

## Phase 1: Define Scope

Before searching, establish what you're looking for and why.

```
SCOPE CHECKLIST:
- [ ] Research question stated as a single sentence
- [ ] Relevant KBs identified (pyrite list)
- [ ] Known entry types to look for (events, people, organizations, documents)
- [ ] Date range if applicable
- [ ] What would a "complete" answer look like?
```

Create a task list with TaskCreate to track progress through the phases.

---

## Phase 2: Gather Sources

Search systematically — don't stop at the first few results.

```bash
# Broad keyword search
pyrite search "<topic>" --limit 30

# Narrow by KB and type
pyrite search "<topic>" --kb=<name> --type=event
pyrite search "<topic>" --kb=<name> --type=person

# Semantic search for conceptually related content
pyrite search "<topic>" --mode=semantic --limit 20

# Hybrid for best coverage
pyrite search "<topic>" --mode=hybrid --limit 20

# Tag-based discovery
pyrite tags --kb=<name>
pyrite search "<topic>" --tag=<relevant-tag>

# Timeline for temporal context
pyrite timeline --from=<start> --to=<end>
```

**For each relevant result:**

1. Read the full entry: `pyrite get <entry-id>`
2. Check backlinks: `pyrite backlinks <entry-id> --kb=<name>`
3. Note key claims and their source quality (see [source-assessment.md](source-assessment.md))

**If information is missing from the KB:** Note the gap. If you have reliable external information, create an entry:

```bash
pyrite create --kb=<name> --type=document --title="<source title>" \
  --body="<key content>" --tags="source,<topic>"
```

**Gather completeness check:**

```
- [ ] Searched all relevant KBs (not just one)
- [ ] Used multiple search modes (keyword, semantic, hybrid)
- [ ] Followed backlinks from key entries
- [ ] Checked timeline for temporal context
- [ ] Noted gaps where KB coverage is thin
```

---

## Phase 3: Connect

Map relationships between findings.

1. **Identify patterns** — What themes repeat across sources? What entities appear in multiple contexts?
2. **Build a timeline** — Order events chronologically. Note what happened before/after key events.
3. **Map actors** — Who is connected to whom, through what events or organizations?
4. **Follow link chains** — Use backlinks to find entries you didn't find through search.

```bash
# Find connections from a key entry
pyrite backlinks <entry-id> --kb=<name>

# Get full entry with links
pyrite get <entry-id>
```

**Connection checklist:**

```
- [ ] Key entities listed with their roles
- [ ] Timeline of relevant events constructed
- [ ] Relationships between entities documented
- [ ] Unexpected connections noted
```

---

## Phase 4: Analyze

Assess what the evidence actually supports.

For each major claim or finding:

| Question | Answer |
|----------|--------|
| How many independent sources support this? | |
| What is the highest-quality source? | |
| Are there contradictions between sources? | |
| What is NOT said that you'd expect? | |
| What alternative explanations exist? | |

**Use the source assessment rubric** from [source-assessment.md](source-assessment.md) to rate each source.

**Analysis checklist:**

```
- [ ] Each claim attributed to specific source(s)
- [ ] Contradictions between sources identified
- [ ] Gaps in evidence noted explicitly
- [ ] Alternative interpretations considered
- [ ] Confidence level assigned (high/medium/low) per finding
```

---

## Phase 5: Synthesize

Create a synthesis entry that brings it all together.

Use the template from [synthesis-template.md](synthesis-template.md) to structure the output.

```bash
pyrite create --kb=<name> --type=note --title="Research: <topic>" \
  --body="<synthesis content>" --tags="research,synthesis,<topic>"
```

**The synthesis entry must include:**

1. **Research question** — What was asked
2. **Key findings** — Numbered list, each with confidence level
3. **Evidence summary** — Which entries support each finding (use `[[wikilinks]]`)
4. **Gaps and limitations** — What the KB doesn't cover
5. **Recommendations** — Next steps for deeper investigation

**Synthesis checklist:**

```
- [ ] Research question clearly stated
- [ ] Each finding has a confidence level (high/medium/low)
- [ ] Each finding links to supporting entries via [[wikilinks]]
- [ ] Contradictions and alternative interpretations noted
- [ ] Gaps explicitly listed
- [ ] Recommendations for follow-up research
```

---

## Confidence Levels

| Level | Meaning |
|-------|---------|
| **High** | Multiple independent, reliable sources agree. No significant contradictions. |
| **Medium** | Supported by at least one reliable source, but not fully corroborated. Minor gaps. |
| **Low** | Single source, or sources of uncertain reliability. Significant gaps or contradictions. |
| **Speculative** | Inference from indirect evidence. Explicitly flagged as interpretation. |

---

## Anti-Patterns

| Trap | Fix |
|------|-----|
| Stopping after first search | Use all 3 search modes. Check backlinks. Search related terms. |
| Treating all sources equally | Apply source assessment rubric to every source. |
| Ignoring contradictions | Contradictions are signal. Investigate, don't smooth over. |
| Presenting speculation as fact | Always tag confidence level. Use "suggests" not "proves" for medium/low. |
| Skipping the gaps section | Knowing what you don't know is as valuable as what you do know. |
| Monster entry with everything | Findings should be concise. Link to full entries for detail. |
