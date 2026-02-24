---
type: backlog_item
title: "Research Flow Skill for Claude Code"
kind: feature
status: completed
priority: high
effort: L
tags: [ai, claude-code, research, workflow]
---

A Claude Code skill that enforces structured research methodology:

**Methodology:** Gather → Connect → Analyze → Synthesize

**Process:**
1. **Define scope** — What question are we answering? What KBs are relevant?
2. **Gather sources** — Search existing KB, create entries for new sources, capture key findings
3. **Connect** — Add wikilinks between related entries, identify patterns, build timeline of events
4. **Analyze** — Assess source reliability, identify gaps, flag contradictions
5. **Synthesize** — Create summary entry linking all findings, with confidence assessments

**Implementation:**
- `skills/research-flow/SKILL.md` — main skill with checklist
- `skills/research-flow/source-assessment.md` — source reliability rubric
- `skills/research-flow/synthesis-template.md` — template for synthesis entries
- Uses native TaskCreate/TaskUpdate for progress tracking
- Chains to `kb` skill for CLI commands

**Inspired by:** Superpowers' brainstorming + writing-plans pattern, but domain-specific to knowledge management and investigative research.

**Command:** `/research <topic>` invokes this skill.
