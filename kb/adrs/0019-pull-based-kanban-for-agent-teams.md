---
id: adr-0019
type: adr
title: "Pull-Based Kanban Workflow Over Sprint Iterations for Agent Teams"
adr_number: 19
status: proposed
deciders: ["markr"]
date: "2026-03-08"
tags: [architecture, agents, workflow, software]
links:
  - target: "software-project-plugin"
    relation: "refines"
    note: "Replaces sprint planning with kanban flow model in Wave 2 scope"
---

# ADR-0019: Pull-Based Kanban Workflow Over Sprint Iterations for Agent Teams

## Context

The software-kb extension's Wave 2 plan (see `software-project-plugin`) originally included sprint/iteration planning as a core workflow primitive — time-boxed iterations with capacity and velocity tracking, modeled on Scrum. This assumed agent dev teams would organize work the same way human-only teams do.

But sprint ceremonies exist to solve a **communication problem**: they're synchronization rituals where humans exchange tacit knowledge — blockers, discoveries, complexity surprises — through a bandwidth-constrained channel (a meeting). In an agent team where the knowledge base *is* the shared context, that synchronization is performed continuously by the system itself. Agents write discoveries back into component docs, express blockers as dependency links, and surface complexity as ADR proposals. The KB becomes a persistent, always-current standup.

Meanwhile, agents introduce a new bottleneck that sprints don't address: **human review capacity**. Agents can produce work faster than any human team can review it. Sprint planning optimizes for *production* throughput; agent teams need to optimize for *review* throughput. Unthrottled agent output overwhelms reviewers, and reviewers facing 40 pending items rubber-stamp; reviewers facing 4 actually think.

This is a constraint problem in the Goldratt (Theory of Constraints) sense: the system's throughput is determined by its bottleneck, and in agent teams the bottleneck is unambiguously human attention.

### Options Considered

1. **Sprint iterations** — time-boxed planning with velocity tracking, adapted for agents
2. **Pure kanban** — pull-based flow with WIP limits, no time boxes
3. **Hybrid** — kanban flow with periodic planning checkpoints

## Decision

Adopt a **pull-based kanban workflow** as the primary work management model for the software-kb plugin. Replace the planned `sprint` entity type with `milestone` (goal-oriented grouping, no time box) and `review_queue` (first-class human attention management). Design all workflow primitives around flow control and constraint optimization rather than time-boxed iteration.

### Core Principles

**Pull-based work.** Agents pull from the backlog when they have capacity, rather than being assigned work in batches. The system answers three questions for the agent: "What can I pull? What are my WIP constraints? What context do I need to start?"

**WIP limits at the review boundary.** Work-in-progress limits are enforced primarily at the human review stage. This throttles agent output to match human review bandwidth — not to limit agent productivity for its own sake, but to protect review quality and prevent rubber-stamping.

**Executable transition policies.** "What does it mean for an item to move from one state to another?" For agents, these aren't social agreements — they're executable rules. An item moves from `in_progress` to `review` when it passes automated checks defined in its acceptance criteria. An item moves from `review` to `done` when a human approves it.

**Context assembly at pull time.** When an agent pulls a backlog item, the system provides the item *plus* every relevant ADR, component doc, programmatic validation, and development convention it needs. The kanban doesn't just control flow — it packages context. This is where Pyrite's KB layer becomes the critical differentiator over conventional project management tools.

### Entity Model Changes

**Replace `sprint` with:**

- **`milestone`** — A goal-oriented grouping that says "these items collectively deliver this capability." Milestones complete when their items complete. Velocity is tracked as an emergent property rather than a planning input.
- **`review_queue`** — The human-facing view of what needs attention: agent-proposed ADRs awaiting approval, completed items awaiting review, component doc updates to sanity-check. First-class because it represents the system's primary constraint.

**Add:**

- **`lane`** — A workflow stage with configurable WIP limits and transition policies. Lanes define the flow topology.

**Replace `standard` with two distinct entry types:**

- **`programmatic_validation`** — Specifications that have a programmatic check. Linting configs, test patterns, commit message formats, required file structures. The defining characteristic: there is a gate the agent must pass, and the system can evaluate compliance as pass/fail. Existing standards with `enforced: true` (Testing Standards, Python Code Style, Git Workflow) migrate here.
- **`development_convention`** — Guidance for making judgment calls. "We prefer composition over inheritance." "Error messages should tell the user what to do next." "When adding a new MCP tool, follow the pattern in kb_search." These are carried as context when an agent starts work — the agent *should* follow them, but the system doesn't fail the build if it doesn't. Compliance is a human review judgment. Existing standards with `enforced: false` (API & MCP Tool Design, Extension Development Standards) migrate here.

This split is ontological, not just a metadata toggle. A programmatic validation is a *specification* — it describes a verifiable property of the output. A development convention is a *heuristic* — it describes a quality of the process. The names themselves do the explanatory work: an agent (or human) never has to ask "which type should this be?" If you can write a check for it, it's a `programmatic_validation`. If you can't, it's a `development_convention`.

This maps directly to the review workflow. When an agent completes work, the system runs all relevant `programmatic_validations` automatically. The reviewer sees "all validations pass" as a pre-condition. Then the reviewer evaluates whether the work follows the relevant `development_conventions` — and that's the part that requires human judgment. The type split *is* the trust boundary. Everything on the validations side can eventually be automated out of the review loop. Everything on the conventions side is where human attention stays valuable.

### MCP Tool Changes

**Replace `sw_sprint_status` with:**

- **`sw_pull_next`** — Given agent capabilities and current WIP state, recommend what to work on. Encodes flow logic so the agent doesn't just see the board — the system tells it what to pull based on system-wide flow state.
- **`sw_context_for_item`** — Given a backlog item, assemble the bundle of ADRs, components, programmatic validations, and development conventions the agent needs. This is the "context assembly" tool — arguably the most valuable primitive in the system.
- **`sw_review_queue`** — Surface the human review bottleneck: what needs attention, what's been waiting longest, what's blocking downstream work.

**Add:**

- **`sw_validate`** — Run all relevant `programmatic_validations` against proposed changes. Returns pass/fail per validation. This is the automated gate that must clear before work moves to human review.
- **`sw_changelog_entry`** — Structured changelog entry produced when an agent completes work. Feeds the `release` entity type and creates the audit trail.

### Bottleneck Optimization Hierarchy

The system design follows Goldratt's Five Focusing Steps applied to the human review constraint:

1. **Identify** — Human review attention is the constraint.
2. **Exploit** — Make each review faster via context assembly, structured diffs, convention compliance reports, and pre-verified automated checks. The reviewer sees "here's what changed, here's why, here's what we already verified, here's what needs your judgment."
3. **Subordinate** — WIP limits on the review queue ensure agents don't outpace review capacity. Agents can shift to lower-risk work when the review queue is full.
4. **Elevate** — Trust tiers allow low-risk changes (typo fixes, dependency bumps passing all tests, component doc updates reflecting code changes) to bypass full human review. Agents with a track record of good work in a specific domain earn lighter review. Review capacity grows as trust is earned.
5. **Repeat** — Track review throughput, latency, and rejection rate. When rejection rate drops, loosen WIP limits. When a new bottleneck emerges, re-identify.

## Consequences

### Positive

- Better fit for how agent teams actually work — continuous flow rather than artificial time boxes
- Human attention is explicitly managed as the scarce resource, not an afterthought
- Context assembly at pull time solves the "agent has to figure out its own context" problem
- WIP limits protect review quality by preventing reviewer overload
- Trust tiers create a natural path from high-oversight to high-autonomy as agents prove reliability
- Velocity becomes an emergent, measurable property rather than a planning guess
- Simpler entity model (milestone + lane vs full sprint planning apparatus)
- `programmatic_validation` / `development_convention` split gives agents and reviewers clear, self-explanatory signals about what can be automated vs what needs judgment
- Stronger launch narrative: "we rethought workflow for agent teams" vs "agents can do sprint planning too"

### Negative

- Teams accustomed to sprint ceremonies may find the model unfamiliar
- No built-in "planning ritual" — teams must find their own cadence for reprioritization
- Trust tier calibration requires data; early usage will be conservative
- WIP limit tuning is non-trivial and context-dependent
- Migrating existing `standard` entries to two new types requires a one-time migration

### Neutral

- Sprint support could be added later as a plugin if demand emerges; this decision doesn't foreclose it
- The `milestone` entity covers the goal-setting function that sprints partially served
- The old `standard` type could be retained as an alias during a transition period if needed
