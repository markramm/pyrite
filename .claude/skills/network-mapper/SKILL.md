---
name: network-mapper
description: "Use when mapping relationships between entities in a journalism-investigation KB. Discovers ownership chains, board memberships, funding flows, and other connections. Creates structured connection entries with sources and identifies multi-hop relationships."
---

# Network Mapper Skill

Relationship discovery and network mapping for journalism-investigation knowledge bases. Traces ownership chains, board memberships, and funding flows to reveal hidden connections between entities.

**Announce at start:** "I'm using the network-mapper skill."

**Methodology:** Scope -> Discover -> Connect -> Trace -> Analyze

**The non-negotiable rule:** Every connection must have a source document logged before the connection entry is created. No exceptions. If no source exists, log one first with `pyrite investigation log-source` or `investigation_log_source`.

---

## Phase 1: Define Network Scope

Establish the focal entity and the boundaries of the mapping exercise.

```
NETWORK SCOPE:
- Focal entity: [[entity-id]]
- KB: <kb-name>
- Relationship types: ownership / membership / funding / all
- Depth: <number of hops from focal entity>
- Time window: <start date> to <end date> (or "current")
```

Check the existing network state before doing any new work:

```bash
# What connections already exist?
pyrite investigation network <entity-id> -k <kb>

# What entries reference this entity?
pyrite backlinks <entity-id> -k <kb>

# Existing ownership chains
pyrite investigation ownership <entity-id> -k <kb>

# Existing money flows
pyrite investigation money-flow <entity-id> -k <kb>
```

**Scope checklist:**

```
- [ ] Focal entity confirmed to exist in KB (create if not)
- [ ] Existing connections reviewed — no duplicate work
- [ ] Relationship types and depth agreed with user
- [ ] Time window established
```

---

## Phase 2: Discover Relationships

For each entity in scope, systematically find connections.

**Discovery order:**

1. Search the KB for known connections
2. Use web search for corporate registries, SEC filings, board listings
3. For each relationship found, log the source before anything else

```bash
# KB searches
pyrite search "<entity name>" -k <kb> --limit 50
pyrite search "<entity name>" -k <kb> --mode semantic --limit 20

# Find related entities by tag
pyrite tags -k <kb>
pyrite search "<entity>" -k <kb> --tag=<relevant-tag>

# List known entities
pyrite investigation entities -k <kb>

# Check for duplicates before creating new entities
pyrite investigation dedup -k <kb>
```

**For each relationship discovered:**

| Step | Action | Why |
|------|--------|-----|
| 1 | Log source document | `pyrite investigation log-source -k <kb> --url "<url>" --title "<title>"` |
| 2 | Determine type | ownership, membership, or funding |
| 3 | Note direction | Who owns/funds/is-member-of whom |
| 4 | Record specifics | Percentage, role, amount, currency |
| 5 | Record dates | Start date, end date (or "current") |

**Discovery checklist per entity:**

```
- [ ] KB searched (keyword + semantic)
- [ ] Backlinks checked
- [ ] Web sources searched (corporate registries, filings, news)
- [ ] All sources logged before connection creation
- [ ] Duplicate entities checked
```

---

## Phase 3: Create Connection Entries

Ensure both endpoint entities exist before creating any connection.

**Create missing entities:**

```bash
pyrite investigation create-entity -k <kb> --type person --title "<Name>" \
  --field role="<role>"

pyrite investigation create-entity -k <kb> --type organization --title "<Org Name>"
```

**Create individual connections:**

```bash
# Ownership
pyrite create -k <kb> -t ownership --title "A owns B" \
  -f owner="[[entity-a]]" -f asset="[[entity-b]]" \
  -f percentage="51" -f beneficial=true

# Membership
pyrite create -k <kb> -t membership --title "Person is Director of Org" \
  -f person="[[person-id]]" -f organization="[[org-id]]" \
  -f role="Director" -f start_date="2019-01-15"

# Funding
pyrite create -k <kb> -t funding --title "Funder funds Recipient" \
  -f funder="[[funder-id]]" -f recipient="[[recipient-id]]" \
  -f amount="500000" -f currency="USD" -f mechanism="grant"
```

**Batch creation (many connections at once):**

```bash
pyrite investigation bulk-edges --file edges.json -k <kb>
```

Or via MCP: `investigation_bulk_edges`

The `edges.json` format should contain an array of connection objects, each with type, endpoints, and fields.

**Connection creation rules:**

- Both endpoint entities must exist before creating the connection
- Source document must be logged before creating the connection
- Check for existing connections to avoid duplicates
- Always include direction — ownership and funding are directional
- Include temporal data when known (start_date, end_date)

---

## Phase 4: Trace Multi-Hop Relationships

Use Pyrite's chain analysis tools to follow connections through intermediaries.

```bash
# Ownership chains up to 5 hops
pyrite investigation ownership <entity-id> -k <kb> --depth 5

# Money flow paths up to 3 hops
pyrite investigation money-flow <entity-id> -k <kb> --hops 3

# Full network view
pyrite investigation network <entity-id> -k <kb>
```

**Patterns to flag:**

| Pattern | What it means | Detection |
|---------|--------------|-----------|
| Circular ownership | Shell company structure, potential money laundering | Entity appears as both owner and asset in chain |
| Hub entity | Central controller or key intermediary | Entity with many connections across chains |
| Long chains (5+ hops) | Intentional obscuring of beneficial ownership | Deep ownership chains with intermediary entities |
| Concentrated control | One entity controls many through intermediaries | Fan-out from single owner through multiple shells |
| Missing links | Gap in ownership or funding chain | Chain ends at entity with no further connections |

**For each chain found:**

1. Calculate effective ownership (multiply percentages along chain)
2. Count shell company indicators for each intermediary
3. Note the chain depth
4. Flag any patterns from the table above

---

## Phase 5: Analyze and Report

Build the network mapping report using the output format below.

**Analysis steps:**

1. Count total entities and connections mapped
2. Rank entities by connection count to find key hubs
3. Identify clusters (groups of closely connected entities)
4. Evaluate each intermediary for shell company indicators
5. Trace beneficial ownership through chains
6. List gaps requiring further research

**Gap identification:**

- Entities with only inbound connections (outbound unknown)
- Entities with only outbound connections (inbound unknown)
- Ownership chains that end at unresearched entities
- Entities with few connections relative to their apparent importance
- Missing intermediaries (ownership gap between known entities)

---

## Connection Type Reference

| Type | Required fields | Key optional fields |
|------|----------------|-------------------|
| ownership | owner, asset | percentage, beneficial, legal_basis, start_date, end_date |
| membership | person, organization | role, start_date, end_date |
| funding | funder, recipient | amount, currency, mechanism, purpose, date_range |

---

## Shell Company Indicators

An entity may be a shell company if it meets multiple criteria:

- It appears as an intermediary (is both owner and asset in different ownership entries)
- It has no membership entries (no people linked to it)
- It is registered in a secrecy jurisdiction
- It has a generic name or P.O. box address
- Multiple unrelated ownership chains pass through it

Flag entities with 2+ indicators. Entities with 3+ indicators are strong shell company candidates.

---

## Key CLI Commands

| Command | Purpose |
|---------|---------|
| `pyrite investigation network <id> -k <kb>` | Get entity connection network |
| `pyrite investigation ownership <id> -k <kb> --depth 5` | Trace ownership chains |
| `pyrite investigation money-flow <id> -k <kb> --hops 3` | Trace money flows |
| `pyrite investigation entities -k <kb>` | List entities |
| `pyrite investigation dedup -k <kb>` | Check for duplicate entities |
| `pyrite investigation bulk-edges --file edges.json -k <kb>` | Batch create connections |
| `pyrite backlinks <id> -k <kb>` | Find entries referencing an entity |

## Key MCP Tools

| Tool | Tier | Purpose |
|------|------|---------|
| `investigation_network` | read | Get entity connection network |
| `investigation_ownership_chain` | read | Trace ownership chains |
| `investigation_money_flow` | read | Trace money flows |
| `investigation_entities` | read | List entities |
| `investigation_find_duplicates` | read | Check for duplicate entities |
| `investigation_bulk_edges` | write | Batch create connections |
| `investigation_create_entity` | write | Create new entities |
| `investigation_log_source` | write | Log sources |

---

## Anti-Patterns

| Trap | Fix |
|------|-----|
| Creating connections without source documents | Log the source first. Always. `investigation_log_source` before any connection. |
| Not checking for existing connections | Search existing network and backlinks before creating. Duplicates corrupt analysis. |
| Mapping only one direction | Ownership and funding are directional. If A owns B, also check what B owns. |
| Ignoring temporal data | Connections have start and end dates. A 2015 ownership may not be current. |
| Not flagging circular structures | Circular ownership is a key investigative finding. Always check for it. |
| Over-connecting | Co-occurrence is not a relationship. Two entities in the same article does not mean they are connected. Require evidence of a specific relationship type. |
| Skipping duplicate checks | Run `pyrite investigation dedup` before creating entities. Duplicate entities fragment the network. |
| Ignoring effective ownership | 100% of 50% is 50%. Multiply percentages along chains to get true control. |

---

## Output Format

Network mapping report:

```
## Network Map: <focal entity>
KB: <kb-name>
Depth: <hops mapped>
Date: <mapping date>

### Network Statistics
- Entities mapped: N
- Connections created: N
- Ownership chains: N (max depth: X)
- Funding flows: N

### Key Hubs (most connected)
1. [[entity-1]] — N connections (person, importance: 9)
2. [[entity-2]] — N connections (organization, importance: 8)

### Ownership Chains
- [[entity-a]] → [[shell-1]] (100%) → [[shell-2]] (100%) → [[entity-b]] (51%)
  Effective ownership: 51% | Shell indicators: 2

### Shell Company Indicators
- [[shell-1]] — intermediary, no memberships, secrecy jurisdiction
- [[shell-2]] — intermediary, no memberships

### Funding Flows
- [[funder-1]] → [[recipient-1]] ($500K via grant)
- [[funder-1]] → [[recipient-2]] ($200K via contract)

### Gaps Identified
- [[entity-x]] has only inbound connections — outbound relationships unknown
- Ownership chain for [[entity-y]] ends at [[unknown-entity]] — needs research

### Sources Used
- [[source-1]] — <title> (Tier 1)
- [[source-2]] — <title> (Tier 2)
```
