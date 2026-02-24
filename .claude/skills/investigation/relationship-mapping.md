# Relationship Mapping Guide

How to document connections between entities during an investigation.

## Relationship Type Vocabulary

Use consistent relationship types so connections are searchable and comparable across investigations.

### Person → Organization

| Type | Meaning |
|------|---------|
| `employs` / `employed_by` | Current or former employment |
| `founded` / `co-founded` | Created the organization |
| `leads` / `led` | Director, CEO, chair, etc. |
| `advises` / `advised` | Advisory role, board member |
| `funds` / `funded_by` | Financial support |
| `represents` / `represented_by` | Legal, political, or lobbying relationship |
| `member_of` | Membership without leadership role |

### Person → Person

| Type | Meaning |
|------|---------|
| `colleague` | Work at same organization |
| `mentor` / `mentored_by` | Professional guidance relationship |
| `appointed` / `appointed_by` | Placed into a role |
| `succeeded` / `preceded_by` | Held same role at different times |
| `opposes` | Public adversarial relationship |
| `collaborates_with` | Working together on specific efforts |

### Organization → Organization

| Type | Meaning |
|------|---------|
| `subsidiary_of` / `parent_of` | Ownership hierarchy |
| `funds` / `funded_by` | Financial flows |
| `partners_with` | Formal partnership or alliance |
| `opposes` | Adversarial relationship |
| `regulates` / `regulated_by` | Regulatory oversight |
| `succeeded` / `preceded_by` | One replaced or evolved from the other |

### Any → Event

| Type | Meaning |
|------|---------|
| `participated_in` | Was involved in the event |
| `caused` / `caused_by` | Causal relationship |
| `responded_to` | Reacted to the event |

---

## Mapping Techniques

### 1. Start from the target entity

Read all entries that mention the target. For each mention, extract who else is named and what the relationship is.

### 2. Follow backlinks

```bash
pyrite backlinks <entity-id> --kb=<name>
```

Every entry that links TO your target is a potential relationship source.

### 3. Shared event participation

Search for events involving the target, then check who else participated:

```bash
pyrite search "<entity>" --type=event
# For each event found:
pyrite get <event-id>
# Check the participants/actors list
```

### 4. Shared tags

If two entities share specific tags (beyond generic ones like "politics"), that's a signal to investigate their connection.

### 5. Temporal proximity

Events happening close together involving different entities may indicate a connection worth investigating.

---

## Documenting Relationships

For each relationship, record:

```
From: [[entity-a]]
To: [[entity-b]]
Type: <relationship type from vocabulary above>
Direction: bidirectional / A→B / B→A
Source: [[source-entry]]
Confidence: High / Medium / Low
Time period: <when this relationship was active, or "ongoing">
Notes: <any relevant context>
```

### When to create a relationship entry

If a relationship is significant enough to warrant its own entry (complex, contested, or central to the investigation):

```bash
pyrite create --kb=<name> --type=relationship --title="<Entity A> — <Entity B>" \
  --body="<relationship details with source links>" \
  --tags="relationship,<entity-a-tag>,<entity-b-tag>"
```

For simpler relationships, documenting them in the entity profile's relationship table is sufficient.
