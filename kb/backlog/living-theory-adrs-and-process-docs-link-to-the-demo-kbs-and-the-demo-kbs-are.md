---
id: living-theory-adrs-and-process-docs-link-to-the-demo-kbs-and-the-demo-kbs-are
title: 'Living theory: ADRs and process docs link to the demo KBs, and the demo KBs are kept current'
type: backlog_item
tags:
- docs
- kb
- process
- enhancement
importance: 5
kind: feature
status: proposed
priority: medium
effort: M
rank: 0
---

Maintainer idea, 2026-09-26.

The pyrite KB's ADRs, process skills and retros already lean on lean and systems theory: Theory of Constraints (ADR-0019), the Poppendiecks' seven wastes and 'amplify learning', Deming's common-cause variation, TPS five whys and A3, Goldratt's current reality tree. They cite it in prose. The demo KBs (tps, goldratt, deming, poppendiecks, flow, devops, boyd, demarco and others) hold that theory as structured entries.

## Goal state
- **Linked.** An ADR, a standard or a skill that rests on a theory links to the theory entry itself (a cross-KB wikilink such as [[goldratt:five-focusing-steps]]), with a stated relation such as grounded_in or applies. A reader, or an agent, can follow a decision back to its reasoning.
- **Living.** The demo KBs become part of the project's documentation of the systems and process theory behind Pyrite, not a static demo. They are kept current: agents research new material on lean and systems thinking in the age of AI (AI-assisted development, agent loops, constraints when the builder is a model), with sources and provenance, and it goes through the same review as code.
- **Checked.** Cross-KB theory links are validated: a dangling link, or a theory entry with no source, is reported by qa / index health.

## Open questions
- Where do the demo KBs live and how are they versioned: the pyrite-demo repo, subscribed? How does a reader of the public pyrite KB (and /site) follow a link into them?
- What is the link convention: a frontmatter field (for example theory: [...]) or body wikilinks with a relation? And which relation names (grounded_in, applies, departs_from)?
- The research lane: cadence, source standards (primary sources, dated), and who reviews additions.
- Should retros (the meta-conductor) cite the theory entries they apply? It already names tps five-whys, deming, goldratt and poppendiecks.

## First step
A small spike: inventory the theory the pyrite KB already invokes (grep the ADRs, skills and retros), map each use to an existing demo-KB entry or a gap, and propose the link convention. The deliverable is this ticket, groomed.
