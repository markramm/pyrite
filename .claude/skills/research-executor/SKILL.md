---
name: research-executor
description: "Use when conducting web research for an investigation topic. Searches the web, creates well-sourced KB entries with proper source chain tracking, and enforces the source tier system. Every entry created must link to a source."
---

# Research Executor Skill

Web research executor for Pyrite investigation knowledge bases. Searches the web for information on a topic, logs sources, creates entities/events/claims, and enforces source chain integrity throughout.

**Announce at start:** "I'm using the research-executor skill."

**Methodology:** Scope → Search & Collect → Create Entries → Quality Check

**The non-negotiable rule:** NEVER create an entry without a corresponding source document entry. The source entry comes first, always.

---

## Phase 1: Define Research Scope

Before touching the web, understand what you're looking for and what already exists.

```
SCOPE DEFINITION:
- Research question (single sentence):
- Target KB:
- Specific questions to answer:
  1.
  2.
  3.
- Entity types expected (people, organizations, assets, events):
- Date range if applicable:
- What does "done" look like?
```

### Check existing coverage

```bash
# What does the KB already know?
pyrite search "<topic>" -k <kb> --mode hybrid
pyrite investigation entities
pyrite investigation status

# Check for related entries
pyrite search "<related term>" -k <kb> --mode semantic --limit 20

# Review what sources already exist
pyrite search "<topic>" -k <kb> --type document_source
```

### Create a task list

Use TaskCreate to track research progress — one task per specific question or sub-topic. Update tasks as you work through them.

---

## Phase 2: Search and Collect

Search the web systematically. Vary your queries — don't stop at the first result page.

### Search strategy

1. **Start broad** — search the main topic to orient
2. **Go specific** — search each sub-question individually
3. **Search names** — look up specific people, organizations, or entities mentioned in results
4. **Search for primary sources** — court filings, corporate registries, SEC filings, official records
5. **Search for counter-narratives** — what do critics or opponents say?

Use WebSearch for queries and WebFetch to read full pages when a search result looks relevant.

### For each source found

**Step 1: Assess reliability**

| Tier | Type | Examples |
|------|------|----------|
| 1 (high) | Primary / direct evidence | Court filings, official records, SEC filings, public registries, corporate filings, leaked documents with verified provenance |
| 2 (medium) | Established reporting | Bylined investigative journalism, government reports, academic papers, named-source reporting |
| 3 (low) | Secondary analysis | Commentary, think tank reports, expert blog posts, op-eds |
| 4 (unknown) | Unverified | Social media, unattributed claims, anonymous tips, forums |

**Step 2: Log as a source document**

Every usable source becomes an entry BEFORE you create any entities or claims from it.

```bash
pyrite create -k <kb> -t document_source --title "<source title>" \
  -f reliability=<high|medium|low|unknown> \
  -f classification=public \
  -f url="<source url>" \
  -f obtained_date="<YYYY-MM-DD>" \
  -f author="<author if known>" \
  -f publication_date="<YYYY-MM-DD if known>" \
  -b "Key findings from this source:
- Finding 1
- Finding 2
- Finding 3"
```

Or use the MCP tool:

```
investigation_log_source(
  title="<source title>",
  url="<url>",
  reliability="high|medium|low|unknown",
  classification="public",
  body="Key findings: ..."
)
```

**Step 3: Extract structured information**

From each source, note:
- People mentioned (names, roles, titles)
- Organizations mentioned (names, types, jurisdictions)
- Events (what happened, when, where, who was involved)
- Relationships (who is connected to whom, how)
- Claims or allegations (who said what about whom)
- Financial figures (amounts, currencies, dates)
- Dates and timelines

### Collection completeness check

```
- [ ] Searched the main topic broadly
- [ ] Searched each specific sub-question
- [ ] Searched for key people/organizations by name
- [ ] Looked for primary sources (filings, records, registries)
- [ ] Checked for counter-narratives or contradicting information
- [ ] Every usable source logged as a document_source entry
- [ ] Each source has reliability tier, URL, and obtained_date
```

---

## Phase 3: Create Entries

Now create entries from your collected sources. The source document entries must already exist before this phase.

### Before creating anything: check for duplicates

```bash
# Always search before creating
pyrite search "<entity name>" -k <kb> --mode hybrid
pyrite investigation dedup

# Check alternate spellings, abbreviations, maiden names
pyrite search "<alternate name>" -k <kb>
```

### Entities (people, organizations, assets)

```bash
# Person
pyrite create -k <kb> -t person --title "<Full Name>" \
  -f importance=<1-10> \
  -f role="<primary role>" \
  -f nationality="<if known>" \
  -b "## Summary
<one paragraph summary>

## Source references
- [[<source-entry-id>]] — <what this source tells us>
" --tags "<relevant,tags>"

# Organization
pyrite create -k <kb> -t organization --title "<Organization Name>" \
  -f importance=<1-10> \
  -f org_type="<company|government|ngo|...>" \
  -f jurisdiction="<if known>" \
  -b "## Summary
<one paragraph summary>

## Source references
- [[<source-entry-id>]] — <what this source tells us>
" --tags "<relevant,tags>"
```

Or use MCP tools: `investigation_create_entity(...)`

### Events

```bash
pyrite create -k <kb> -t investigation_event --title "<Event Title>" \
  -f event_date="<YYYY-MM-DD>" \
  -f actors="<comma-separated entry IDs or names>" \
  -b "## What happened
<description>

## Source references
- [[<source-entry-id>]] — <what this source tells us>
" --tags "<relevant,tags>"
```

Or use: `investigation_create_event(...)`

### Claims and allegations

Claims are assertions that need verification. They are NOT confirmed facts.

```bash
pyrite create -k <kb> -t claim --title "<Concise claim statement>" \
  -f claim_status=unverified \
  -f claimed_by="<who made the claim>" \
  -f claim_date="<when the claim was made>" \
  -b "## Claim
<full statement of the claim>

## Available evidence
- [[<source-entry-id>]] — <what this source says>

## Counter-evidence
<any contradicting information, or 'None found'>
" --tags "<relevant,tags>"
```

Or use: `investigation_create_claim(...)`

**Claims always start as `unverified`.** The fact-checker skill handles verification separately.

### Connections and relationships

Both endpoints must exist as entries before creating a connection.

```bash
pyrite create -k <kb> -t connection --title "<Entity A> — <relationship> — <Entity B>" \
  -f from_entity="<entry-id-A>" \
  -f to_entity="<entry-id-B>" \
  -f relationship_type="<ownership|membership|funding|employment|...>" \
  -b "## Relationship
<description of the connection>

## Source references
- [[<source-entry-id>]] — <evidence for this relationship>
" --tags "<relevant,tags>"
```

### Entry creation rules

1. **Source first** — the document_source entry must exist before any entry that references it
2. **Check duplicates** — search before creating; merge information into existing entries when possible
3. **Facts vs. claims** — if you can point to Tier 1/2 evidence, it's a fact; if it's an allegation or assertion, create it as a claim with `claim_status: unverified`
4. **Both endpoints first** — connection entries require both entities to exist already
5. **Date everything** — include dates wherever possible (event dates, claim dates, source publication dates)

---

## Phase 4: Quality Check

After creating entries, verify the work.

```bash
# Run the QA report
pyrite investigation qa

# Check for duplicates
pyrite investigation dedup

# Verify source coverage
pyrite investigation status
```

### Quality checklist

```
- [ ] Every entry links to at least one source document via [[wikilink]]
- [ ] No orphaned entries (entities without relationships or context)
- [ ] No duplicate entities (checked with dedup)
- [ ] All claims are marked as unverified
- [ ] Dates are present where applicable
- [ ] Source tiers are consistent (a blog post is not Tier 1)
- [ ] Obtained dates recorded on all sources
- [ ] Gaps in knowledge explicitly noted
```

---

## Key MCP Tools

| Tool | Tier | Purpose |
|------|------|---------|
| `investigation_search_all` | Read | Cross-KB search |
| `investigation_entities` | Read | List existing entities |
| `investigation_status` | Read | Investigation overview |
| `investigation_qa_report` | Read | Quality check |
| `investigation_create_entity` | Write | Create person/org/asset entries |
| `investigation_create_event` | Write | Create event entries |
| `investigation_create_claim` | Write | Create claim entries |
| `investigation_log_source` | Write | Log source documents |

## Key CLI Commands

```bash
pyrite search "<topic>" -k <kb>                  # Keyword search
pyrite search "<topic>" -k <kb> --mode semantic   # Semantic search
pyrite search "<topic>" -k <kb> --mode hybrid     # Combined search
pyrite investigation search --correlate           # Cross-reference search
pyrite investigation status                       # Overview
pyrite investigation qa                           # Quality report
pyrite investigation dedup                        # Duplicate detection
pyrite create -k <kb> -t <type> ...               # Create entries
pyrite get <entry-id> -k <kb>                     # Read full entry
pyrite backlinks <entry-id> -k <kb>               # Find what links to an entry
```

---

## Anti-Patterns

| Trap | Fix |
|------|-----|
| Creating entries without source documents | Log the source FIRST, then create entries that reference it. |
| Not checking for duplicates before creating | Always search by name and aliases before `pyrite create`. |
| Mixing facts and claims | Facts have Tier 1/2 evidence. Everything else is a claim with `unverified` status. |
| Using one source for many unrelated claims | Each claim should be independently traceable. If one source covers multiple topics, that's fine — but note it. |
| Not recording obtained_date on sources | Always set `obtained_date` to today's date when you access a web source. |
| Over-relying on a single source tier | Seek corroboration across tiers. A finding backed only by Tier 3/4 sources is Low confidence. |
| Creating connections before both endpoints exist | Create both entity entries first, then the connection. |
| Treating web search results as sources | The search result snippet is not the source. Fetch and read the actual page. Use WebFetch. |
| Skipping the scope phase | Without clear questions, research sprawls. Define scope first. |

---

## Output Format

At the end of a research session, produce this summary:

```
## Research Session: <topic>
KB: <kb-name>
Date: <date>

### Sources logged: N
- [[source-1]] — <title> (Tier 1, public)
- [[source-2]] — <title> (Tier 2, journalism)

### Entities created: N
- [[entity-1]] — <name> (person, importance: 8)
- [[entity-2]] — <name> (organization, importance: 7)

### Events recorded: N
- [[event-1]] — <title> (2024-01-15)

### Claims filed: N (all unverified)
- [[claim-1]] — <assertion>

### Gaps identified:
- No information found about X's role in Y
- Source needed for claim about Z
- Counter-narrative not yet investigated for W
```
