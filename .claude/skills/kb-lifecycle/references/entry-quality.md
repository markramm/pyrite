# Entry Quality Guide for Intellectual Biographies

Standards for creating high-quality entries in intellectual-biography and movement KBs.

## What Makes a Good Entry

### The Core Test

A good entry teaches something a reader couldn't get from 5 minutes on Wikipedia. It should:

1. **Contextualize** -- place the subject within intellectual lineage, not just describe it
2. **Connect** -- link to other entries via `[[wikilinks]]`, building the knowledge graph
3. **Attribute** -- trace ideas to their sources and document the transmission chain
4. **Distinguish** -- separate the subject's original contribution from later interpretations

### Entry Quality Checklist

| Criterion | Test |
|-----------|------|
| **Has substance** | Body is more than 2-3 sentences -- provides real analysis or information |
| **Has context** | Places the topic within the broader intellectual story |
| **Has links** | Contains at least 2 `[[wikilinks]]` to other entries (existing or planned) |
| **Has attribution** | Factual claims reference a source where possible |
| **Has dates** | Time-dependent claims include dates or date ranges |
| **Has the right type** | Entry type matches content -- a concept isn't filed as a note |
| **Has the right importance** | Importance score (1-10) reflects centrality to the KB's story |

## Entry Types -- What Each Should Contain

### Concept Entries (Most Important)

These are the intellectual core of the KB. A concept entry should:

- **Define** the concept in the subject's own terms (quote or paraphrase)
- **Trace origin** -- when and where it first appeared
- **Show evolution** -- how the concept changed over time
- **Document influence** -- who adopted, adapted, or critiqued it
- **Distinguish from misconceptions** -- how it's commonly misrepresented

Bad: "The OODA loop is a decision-making framework."
Good: "Boyd's OODA loop (Observe-Orient-Decide-Act) is commonly reduced to a simple cycle, but Boyd's own formulation emphasizes orientation as the dominant phase..."

### Writing Entries

- **Significance over summary** -- explain WHY this work matters, not just what it says
- **Context** -- what prompted it, what it responded to, what it influenced
- **Key contributions** -- what ideas first appeared or were developed here
- **Reception** -- how it was received, adopted, critiqued

### Person Entries

- **Role** -- their function in the subject's network (mentor, student, collaborator, critic)
- **Relationship specifics** -- not just "worked with X" but how and on what
- **Own contributions** -- what they did independently, not just their connection
- **Dates** -- when the relationship was active

### Era Entries

- **Date range** -- always required
- **Narrative arc** -- what characterized this period intellectually and professionally
- **Key events** -- milestones that define the era's boundaries
- **Transition** -- what changed between this era and the next

### Event Entries

- **Date** -- as specific as possible (YYYY-MM-DD preferred, YYYY-MM acceptable)
- **Significance** -- why this event matters to the intellectual story
- **Participants** -- who was involved
- **Consequences** -- what followed from this event

### Source Entries

- **Source type** -- book, article, interview, documentary, etc.
- **Author and date** -- always required
- **What it contributes** -- why this source matters to the KB, what unique information it provides
- **Reliability assessment** -- is this a primary or secondary source? Known biases?

## Wikilink Discipline

Every entry should contain `[[wikilinks]]` to related entries. This builds the knowledge graph.

```markdown
## Good -- creates a connected knowledge graph
Boyd's [[orientation]] concept draws on [[destruction-and-creation]], his
only formal essay, which applies [[godel-incompleteness-theorem|Godel's
incompleteness theorems]] and [[heisenberg-uncertainty-principle|Heisenberg's
uncertainty principle]] to the problem of generating new mental models.
[[chuck-spinney|Spinney]] and [[pierre-sprey|Sprey]] helped develop the
practical implications for [[defense-procurement-reform|procurement reform]].

## Bad -- isolated entry with no connections
Boyd's orientation concept draws on his essay about destruction and creation.
It applies ideas from mathematics and physics to mental model generation.
His colleagues helped apply these ideas to procurement.
```

If a link target doesn't exist yet, create the link anyway. It becomes a "wanted page" that maps territory the KB should cover. This is valuable signal for gap analysis.

## Importance Scale

Use consistently across a KB:

| Score | Meaning | Example |
|-------|---------|---------|
| 10 | Foundational -- defines the entire KB | OODA loop for Boyd KB |
| 8-9 | Major -- central to understanding the subject | Destruction and Creation for Boyd |
| 6-7 | Significant -- important supporting topic | E-M theory for Boyd |
| 4-5 | Supporting -- provides context or depth | A specific Pentagon office |
| 2-3 | Minor -- peripheral but relevant | A minor acolyte |
| 1 | Minimal -- included for completeness | A tangential reference |

## Common Mistakes

1. **Stub entries that never get expanded** -- Better to write fewer, fuller entries than many stubs. If stubbing, add `research_status: stub` and a body that outlines what the full entry should contain.

2. **Concept entries that just define** -- A dictionary definition is not a KB entry. Trace lineage, show evolution, document influence.

3. **Person entries that are just bios** -- The KB is about the subject's intellectual world. A person entry should explain their role in that world, not just their resume.

4. **Missing cross-KB connections** -- If Deming's PDCA influenced Boyd's OODA, that connection should be explicit in both KBs via cross-KB links.

5. **Inconsistent importance scores** -- Calibrate within a KB. If a foundational concept is importance 8, a minor person shouldn't also be 8.

6. **Source entries without significance** -- Don't just list sources. Explain what each source uniquely contributes to understanding the subject.
