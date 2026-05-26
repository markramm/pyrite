---
id: conductor-primitive-kb-driven-orchestration-skill
type: backlog_item
title: "Conductor primitive: KB-driven orchestration skill that reads roles, state machine, QC, and goals from target KB config"
kind: feature
status: proposed
priority: medium
effort: L
tags: [conductor, orchestration, parallel-agents, task-system, skill-design, dry, primitive]
---

## Problem

Three near-duplicate "conductor" skills now exist in the user's plugin set, each running essentially the same orchestration loop against a different Pyrite KB:

- **`tcp-skills:investigation-conductor`** — orchestrates parallel research workers on the `cascade-research` backlog
- **`tcp-skills:draft-conductor`** — orchestrates parallel editorial workers on the `drafts` backlog
- **An emergent triage-conductor pattern** — the same skill running a backlog-grooming pass (validated across 5 waves on the drafts KB in May 2026), but with different roles (triagers vs editors), different state machine (deployability verdicts vs editorial readiness), different QC criteria

All three skills share the same core orchestration primitive:

1. Read backlog state from a Pyrite KB
2. Apply dispatch-policy: select non-overlapping work units, honor parallelism caps, choose model per work type (Sonnet retrieval-heavy / Opus synthesis-heavy)
3. Open atomic-claim Pyrite tasks per work unit (forward-only state machine, `<conductor-id>:<unit-id>:<phase>:<cycle>` naming convention)
4. Launch parallel sub-agents with role-specific briefs via the `Agent` tool
5. Absorb task-notification completions: QC each output, surface findings to the conductor's synthesis layer
6. Exercise synthesis judgment (per-work-unit-state matrix → next action)
7. Loop, with a per-tick report template

They differ only in:

- **Which Pyrite KB they read** (`cascade-research` / `drafts` / `<future-domain>`)
- **Which task naming prefix** (`investigation-conductor:*` / `draft-conductor:*` / etc)
- **Which roles workers can play** (researcher / editor / reviser / fact-checker / cross-link auditor / triager / etc — each with role-specific worker templates)
- **State machine for work units** (per-investigation-task-status vs per-piece-readiness vs per-piece-deployability)
- **Synthesis judgment matrix** (per-state → last-pass-content → next-action)
- **QC criteria per role**

Everything else — the atomic-claim primitive, the dispatch-pattern ceilings, the model-selection rubric, the report template, the loop-mode wakeup protocol — generalizes.

Three near-duplicates means three places to fix every skill-level bug. During the May 2026 conductor build-out, three skill bugs were identified and fixed (bootstrap-mapping for legacy readiness values, editor-Sonnet rule relaxation, published-pre-gate with title confirmation). Each was a single fix in one skill that should have propagated to others. The current pattern means three fixes, or — what actually happened — one fix in the active skill and the others rot.

## Proposed solution

A `pyrite-conductor` skill that reads its operating parameters from the target KB itself.

The KB's `kb.yaml` (or a dedicated `conductor.yaml`) declares:

```yaml
conductor:
  enabled: true
  roles:
    - name: editor
      model: opus  # default; overridable per-task
      model_overrides:
        - condition: register == "RAMM-investigative" AND single_thesis
          model: sonnet
      template: references/editor-role.md
      qc_criteria_ref: references/editor-qc.md

    - name: reviser
      model: sonnet
      model_overrides:
        - condition: notes_include_structural OR substrate_integration
          model: opus
      template: references/reviser-role.md
      qc_criteria_ref: references/reviser-qc.md

    # ...etc per domain

  state_machine:
    work_unit_type: piece  # or "task" or "draft" or "investigation"
    states:
      - name: brief
        next_actions: [drafter]
      - name: first-draft-complete
        next_actions: [editor]
      - name: editorial-pass-N-complete
        next_actions: [reviser, editor]  # judgment matrix decides
      # ...etc

  synthesis_matrix_ref: references/synthesis-patterns.md

  dispatch_policy:
    max_concurrent_workers: 4
    per_role_caps:
      editor: 2
      reviser: 2
      fact-checker: 2
      triager: 5  # higher cap because triage absorption is light
    sonnet_max: 3  # adjustable; triage-mode override allowed
    bootstrap_mapping_ref: references/bootstrap-mapping.md  # legacy-vocabulary → conductor-native

  goals:
    primary: maximize-publishable-per-week  # or "minimize-research-backlog-staleness" / "complete-triage-coverage"
    secondary: [respect-news-cycle-attachments, honor-target-dates]

  qc_global:
    pre_gates:
      - check_substack_published_for_supersession
      - check_in_flight_workers_for_overlap
      # ...
```

The conductor skill then becomes domain-agnostic: it reads the config, applies the orchestration primitive, and dispatches workers whose briefs are constructed from the role templates.

Invocation: `/pyrite-conductor <kb-name>` — single skill, parameterized by which KB it targets.

## What stays domain-specific — and lives in the KB itself

Generalization helps the **orchestration layer**; the **worker bodies** stay specialized — but they don't live in the conductor skill, they live in the KB.

**Proposal: workflows and prompts as first-class KB content, with standard-set-plus-overrides inheritance.**

Today, worker briefs are 200-300 lines of carefully-crafted prose per role (editor / reviser / fact-checker / triager). During the May 2026 triage waves, the conductor wrote 5 such briefs (one per parallel slice) at dispatch time. That doesn't scale, isn't maintainable, and creates the three-skills-duplicating-each-other problem this ticket addresses.

Instead, prompts and workflows should be **KB content**:

```
<kb-path>/
├── kb.yaml                          # existing
├── conductor.yaml                   # NEW: roles, state machine, dispatch policy, goals
└── workflows/                       # NEW: per-KB workflow customization
    ├── _inherits_from: standard     # base workflows from a pyrite-shipped standard set
    ├── editor.md                    # override (or omit to use standard)
    ├── reviser.md
    ├── fact-checker.md
    ├── triager.md                   # this KB has triage; another KB might not
    ├── _extensions.md               # KB-specific prompt fragments appended to all roles
    └── _quality_rules.md            # KB-specific QA criteria
```

Plus a `pyrite-conductor-standard/` shipped with the conductor skill (or in a separate pyrite package), containing baseline workflow templates that 80% of KBs use as-is:

```
pyrite-conductor-standard/workflows/
├── editor.md          # generic editorial-pass template
├── reviser.md
├── fact-checker.md
├── researcher.md
├── triager.md
├── cross-link-auditor.md
├── competitor-scanner.md  # has anyone ELSE broken this story since the draft? (see §below)
└── _dispatch-boilerplate.md  # the shared "you are a worker under the conductor skill..." preamble
```

### Worth specifically calling out: the peer-coverage-scanner role

A specific role that emerged from the May 2026 triage waves but doesn't exist in any current conductor skill: **scanning for other reporters' coverage of overlapping stories** — not to gatekeep against scoops, but to **build the networked-independent-journalism substrate that TCP pieces and the KB depend on**.

The framing matters. Initial drafts of this section talked about "competitor coverage" and treated other reporters' work as something to avoid duplicating. That's wrong. The right framing — which the May 2026 triage work surfaced — is that **peer coverage of overlapping stories is infrastructure, not competition**. The whole point of building this conductor system is to advance independent journalism's capacity to name what must be named and rigorously document accountability. That's a networked enterprise; isolated pieces fail; densely-cross-referenced ones succeed.

So the role's job has two outputs per piece, not one:

**(1) Piece-level action**: how does the peer coverage affect *this draft*?
- `absorb-as-inline-citation` — the default for architecture/pattern pieces; peer coverage becomes substrate the piece cites by name
- `reframe-as-commentary` — peer coverage shifted the story enough that the original framing needs adjustment
- `distinguish-and-ship` — peer coverage is different-angle enough that this piece adds new material
- `archive` — rare; only when peer coverage subsumes the entire structural argument

**(2) KB-level action**: how does the peer coverage strengthen the KB itself?
- `create-cascade-research-note` — peer reporting documents an actor / mechanism / theme not yet in the research KB
- `create-cascade-timeline-event` — peer reporting documents a specific event for the timeline
- `create-peer-coverage-entry` — peer journalist's piece worth catalogging in a peer-coverage KB (new or extended KB)
- `strengthen-existing-actor-profile` — peer coverage adds primary-source material for an actor already in cascade-research
- `no-kb-action-needed` — peer coverage doesn't add substrate beyond what's already captured

The deliverable per piece, appended to frontmatter:

```yaml
peer_coverage_check:
  date_of_check: <ISO date>
  searched: [google, outlet-specific WebFetch where relevant]
  central_thesis_query: "<the piece's load-bearing claim as a search query>"
  named_actors_query: "<top 2-3 named actors>"
  found_peer_coverage:
    - url: <peer URL>
      outlet: <publisher>
      author: <byline>
      date: <when published>
      overlap_type: <fully-overlaps | partially-overlaps-but-misses-architecture | covers-different-angle | none>
      action_for_this_piece: <absorb-as-inline-citation | reframe-as-commentary | distinguish-and-ship | archive>
      action_for_the_kb:
        - <create-cascade-research-note | create-timeline-event | create-peer-coverage-entry | strengthen-existing-actor-profile | no-kb-action-needed>
        - <specific guidance: which note, which actor, what to capture>
```

For most architecture/pattern pieces, the expected pattern is `partially-overlaps-but-misses-architecture` → `absorb-as-inline-citation` for the piece AND `strengthen-existing-actor-profile` or `create-peer-coverage-entry` for the KB.

**The KB-level action is the load-bearing output.** A piece can be `distinguish-and-ship` while generating 5 new KB entries from the peer coverage. The conductor's goal isn't just "ship this piece"; it's "densify the substrate so future pieces can cite this peer journalist's work systematically, and so the KB increasingly reflects the actual state of independent journalism on this beat."

### The implication for the conductor's goal-orientation

This role validates and sharpens the "goals from the KB" design from the earlier section. The goal isn't "ship more TCP pieces." It's something closer to:

```yaml
goals:
  primary: densify-networked-independent-journalism-substrate
  measured_by:
    - tcp_pieces_shipped
    - peer_journalists_cited_by_name_per_piece  # target: ≥3
    - new_peer_coverage_kb_entries_per_week
    - cross_piece_citation_density
    - kb_entries_with_multi_source_primary_documentation
```

A conductor that knows the goal isn't "ship pieces" but "densify the network" makes different synthesis decisions:

- When peer coverage of a draft's central thesis exists, the right move is rarely "kill the piece." It's "absorb peer's work as inline citation; capture peer's piece as a peer-coverage KB entry; flag any new actors/mechanisms for cascade-research; ship the piece with the new substrate."
- When a draft's actor cast has thin KB representation, the right move may be to dispatch researchers to densify those actor profiles *before* dispatching editors on the draft — the editor's structural-argument work depends on substrate that doesn't yet exist.
- When a peer journalist consistently appears in peer-coverage scans across multiple drafts, that's signal: they're working the same beat; building a stable reference relationship with their work serves the longer game.

This is the substantive killer feature. A conductor optimized for `densify-networked-independent-journalism-substrate` is structurally different from one optimized for `maximize-shipped-pieces` — and the difference shows up in *every* dispatch decision, not just at the publication gate.

Wall-clock cost per piece: ~5-10 min for a Sonnet worker doing WebSearch + targeted WebFetch. Triggers naturally on the deploy-ready P9 list (single-news-hook-away pieces), on outlet pitches before submission, and on pieces aged > 7 days regardless of state.

This role is missing from both investigation-conductor and draft-conductor today, and a generalized pyrite-conductor should ship it as part of the standard workflows set. The KB-side companion (a `peer-coverage` KB, or a peer-coverage extension to existing KBs) is a sister-ticket: the role doesn't fully work without a structured place to write the KB-level outputs.

At dispatch time, the conductor does **template assembly**:

```
prompt = standard.dispatch_boilerplate
       + standard.workflows[role]
       + kb.workflows[role]  (overrides if present)
       + kb.workflows._extensions
       + kb.workflows._quality_rules
       + task_specific_briefing
```

That's a **template-construction pipeline** — four or five layers composed at dispatch time, not three separate skills each carrying their own copies.

**Why this is the right design**:

1. **Prompts get versioned alongside the rest of the KB.** When the editor-Sonnet rule changes (as it did mid-session in May 2026), it changes in one place — `pyrite-conductor-standard/workflows/editor.md` — and propagates. KBs that have customized that workflow can see the standard-set diff and decide whether to absorb it. Today the same change took three edits across three skills; one of those three edits was missed.

2. **KB-quality-rules become enforceable.** The drafts KB has implicit rules (e.g., "every load-bearing fact gets a tier-1 citation; tier-3 sources can only support; named-actor attribution requires primary source"). These rules are scattered across worker-template files and not consistently applied. If they live in `<drafts-kb>/workflows/_quality_rules.md` and the conductor injects them into every worker brief, they become **enforced** instead of merely documented.

3. **KB goals become workflow inputs.** The `conductor.yaml` goals (proposed in the previous section) feed into the template-assembly step. A worker doing triage on a KB with `goal: minimize-research-backlog-staleness` gets a different priority-ordering rubric than the same worker on a KB with `goal: maximize-publishable-velocity`. The conductor doesn't have to know the difference — the KB's workflows do.

4. **KB-specific custom workflows become possible without forking the conductor.** Imagine a software-development KB with a `code-reviewer` role that doesn't exist in the standard set. The KB defines `<kb>/workflows/code-reviewer.md` + a `code-reviewer` role in its `conductor.yaml`, and the conductor dispatches it. No need to ship a new conductor variant; the KB carries its own role.

5. **Standard workflows can be improved generationally.** The cumulative learning from running these conductors across many KBs concentrates in the standard set. Per-KB customizations stay light. Improvement flows back to the standard via PRs.

## Synthesis matrices remain per-domain too

Synthesis matrices (the per-state → next-action decision tables that the conductor uses in Step 3) are also KB content:

```
<kb-path>/conductor.yaml:
  synthesis_matrix:
    - from_state: editorial-pass-N-complete
      condition: notes_predominantly_line_level
      next_action: dispatch_reviser
    - from_state: editorial-pass-N-complete
      condition: notes_include_structural
      next_action: dispatch_reviser_then_editor_pass_2
    # ...etc
```

Or in markdown if YAML feels too constrained. The point is: matrix lives in the KB, conductor reads it, conductor applies it. Domain-specific judgment grammar is now first-class KB content.

## Generalization gives you the grammar; KBs provide the content

The conductor primitive provides:
- **Atomic-claim primitive** (open → claimed → in_progress → done/blocked state machine)
- **Parallel-dispatch primitive** (worker count, model selection, non-overlap detection)
- **Absorb-and-synthesize primitive** (task-notification handling, QC absorption, synthesis judgment)
- **Loop-mode primitive** (cron + dynamic ScheduleWakeup)
- **Template-assembly pipeline** (compose worker briefs from standard + KB overrides + task brief)

The KB provides:
- **Roles** (editor / reviser / triager / researcher / custom)
- **State machine** (per-work-unit-states + valid transitions)
- **Synthesis matrix** (state + last-pass-content → next-action)
- **Quality rules** (KB-specific QA criteria that get injected into every worker brief)
- **Goals** (declared, optionally with pressure-windows)
- **Workflow overrides** (only when standard isn't right for this domain)

This is the right division.

## The killer feature: goals from the KB

The most leveraged outcome of this generalization is the `goals` block.

Today, each conductor skill has implicit goals embedded in its operating logic. The investigation-conductor implicitly optimizes for research-coverage; the draft-conductor for publishable-velocity. These are sound defaults but the implicit-default-only pattern makes it hard to redirect a conductor toward a different objective when the situation changes.

If goals are declared in the KB:

```yaml
goals:
  primary: maximize-publishable-pieces-per-week
  pressure_windows:
    - dates: 2026-05-11..2026-05-15
      goal_override: ship-all-may-13-news-pegged-pieces
      drop_other_dispatch: true
```

...then the conductor can read those goals at tick-start and use them to prioritize work-unit selection. The conductor's Step 3 synthesis judgment becomes goal-aware: "given goal X, which work unit should I dispatch next?" rather than "given the matrix, which transition is mechanically required?"

This makes the conductor genuinely **strategic** in a way the current implicit-goals pattern doesn't allow.

## Why this is worth doing now

The pattern has earned the generalization. As of May 2026:

- 30+ ticks logged across the draft-conductor pipeline
- 5 triage waves dispatched (15+15+40 pieces) on the drafts KB
- 3 skill bugs surfaced and fixed in one location only
- The conductor's pre-gate logic (supersession detection via cross-KB hybrid search + title-confirmation) is sophisticated enough that re-implementing it in three places would be expensive
- The triage workflow that emerged in this session has no clean home — it's neither editorial-cycle nor research-extension. A general conductor would absorb it as just-another-role configuration.

The longer the pattern stays scattered across three skills, the more divergence accumulates. Now is the cheapest moment to consolidate.

## Tradeoffs / risks

1. **Config-driven systems are heavier than purpose-built skills.** Loading and parsing a per-KB conductor config adds tokens. Measure cost against the alternative of maintaining three skills.

2. **Worker briefs become harder to author.** A purpose-built skill's worker brief is concrete and inlined; a generalized skill's worker brief is templated and parameterized. New role onboarding becomes a config-and-template task instead of writing prose directly.

3. **State-machine schema becomes load-bearing.** The current per-skill state machines are markdown reference files that workers/conductors read inline. A generalized state machine becomes structured config that needs schema validation, migration, etc.

4. **Backwards compatibility.** investigation-conductor and draft-conductor are working skills with running loops. A migration path matters — the generalization can't break ongoing work.

## Field validation lessons (May 2026 triage waves)

The May 2026 field run of the draft-conductor through 5 waves of triage on 170 pieces (110 drafts + 60 briefs/pointers) validated the primitive AND surfaced specific patterns worth codifying in the generalized conductor:

### 1. Triage is a distinct mode from editorial-cycle work and needs explicit support

Triage doesn't advance work-units through state transitions — it *audits* them and produces deployability/supersession/news-cycle/peer-coverage intelligence. The schema differs from the editorial-cycle log: `triage_log` for drafts, `brief_triage_log` for briefs (different fields because briefs aren't drafts).

The brief-triager's most valuable distinct output is **drafter sizing**: target word count + recommended model (Sonnet/Opus) + complexity + estimated wall-clock per brief. Without this, future drafter dispatch is guesswork. With it, the conductor can pre-allocate resources across dispatch decisions.

Acceptance: pyrite-conductor must support distinct triage-mode roles per work-unit-type (draft-triager, brief-triager, pointer-triager) with schemas declared in the KB's `conductor.yaml`.

### 2. Dispatch caps are mode-dependent

The standard cap of 3 simultaneous Sonnet workers is right for editorial-cycle work (conductor synthesis-bandwidth is binding) but wrong for triage (absorption is much lighter). Triage-mode ran 5 workers × 8 pieces clean. Caps need to be per-mode and per-role, not global.

Acceptance: `conductor.yaml` declares per-mode dispatch caps; conductor primitive enforces the mode-active cap, not a single global value.

### 3. Width-vs-depth tuning is a real choice within triage

Within the triage-mode envelope, there's a tuning choice between fewer-workers-with-more-pieces (5 × 8 = 40) vs more-workers-with-fewer-pieces (8 × 5 = 40 or 10 × 4 = 40). The total work is the same; the dispatch shape affects wall-clock, per-worker context, and per-piece quality.

Empirical observation from May 2026: 5 × 8 worked, but workers near the upper context limit can degrade on the later pieces in their slice. **Going wider with smaller batches** typically gives faster per-worker wall-clock, tighter per-worker context, better per-piece quality on late-slice pieces, and the same conductor absorption load. Modest token cost increase from repeated dispatch boilerplate; usually less than the cost of one wasted-on-poor-quality piece.

The tuning heuristic that worked in the field: **slice along natural sub-cluster lines.** If a slice has natural 4-piece sub-cluster structure (a series, a multi-outlet variant set), use 4-piece workers. If a slice is genuinely 8-piece homogeneous (a coherent 8-part series), use 8-piece workers. Don't pad to 8 if 5 is the natural unit.

Acceptance: `conductor.yaml` supports declarative slice-sizing guidance (e.g., "prefer natural-cluster sizes; fall back to <default> only when no clustering signal exists") and the conductor's dispatch logic honors it.

### 4. Worker output robustness — preliminary frontmatter writes before deep work

Canonical failure mode observed: worker completes analytical work (slice summary file at ~28KB) but crashes (API 500) on the final housekeeping step (per-piece frontmatter writes + Pyrite task creation). The analytical work is preserved in the summary file; the per-piece audit-trail writes are lost.

The robust pattern, documented in the live draft-conductor skill and validated by adoption:

1. On entering each work-unit, write a *preliminary* frontmatter log entry with `status: in-progress` and placeholder verdict fields. Anchors the work-in-progress in the canonical store immediately.
2. Do the analytical work.
3. Update the frontmatter log entry to final values.
4. Create the Pyrite status task.

Mid-run crash leaves per-piece state at "started but not finalized" rather than "no record" — a recovery target rather than a redo.

Acceptance: standard worker-template scaffolding for the pyrite-conductor includes the preliminary-frontmatter-write pattern as default.

### 5. Idempotent dispatch is the right primitive

Double-dispatch was observed in the May 2026 field run (waves 3-G and 3-I both ran twice in parallel because the conductor's wave-rebuild pivot didn't track existing tasks cleanly). One worker's output was wasted; the other became a redundancy-resolution exercise.

Before dispatching a worker, the conductor must check:
- The work-unit's frontmatter for an existing log entry from a worker matching the role + cycle being dispatched
- Pyrite for an existing task with the same `<conductor>:<unit-id>:<phase>:<cycle>` name
- Pyrite task status (a `done` task has already completed once; don't redispatch without a new cycle number)

Acceptance: conductor primitive implements idempotent dispatch by default. Re-dispatch requires either an explicit `--force` flag or a fresh cycle number.

### 6. Cross-piece factual-reconciliation backlog is a first-class deliverable

Triage waves consistently surfaced numerical/dated/attributional discrepancies affecting multiple pieces: ProPublica Palantir-ties count `142 vs 144` showed up in 3 pieces; Carbyne Prepared price `$640M vs ~$800M` showed up in 3 pieces; DOGE federal-jobs count `322K vs ~300K` showed up in 3 squeeze-series pieces; BLS commissioner firing date `Aug 1 vs Sep 4`; Pretti age `32 vs 37`; CITIC ownership `20% vs 40.51%`; Lehman duration `58 vs 61 days`.

The conductor needs a dedicated "Cross-piece factual reconciliation" surface so a single fact-check resolution propagates to every affected piece in one revision pass, rather than being rediscovered per-piece.

Acceptance: tick-report template has a dedicated cross-piece-factual-reconciliation section. A registry artifact (KB entry or markdown file) tracks open discrepancies and their resolution status across pieces.

### 7. Hybrid state model is the right canonical pattern

Across 170 pieces processed in May 2026, the hybrid state model (frontmatter per-piece log + Pyrite tasks as queryable summary) gave the conductor both: scannable per-piece audit trail (frontmatter logs are read in-context) AND aggregate query capability (Pyrite tasks queryable by priority/status/assignee for selecting next dispatch).

The frontmatter log is canonical persistent state; Pyrite tasks are ephemeral atomic-claim primitives that double as queryable summaries. Neither alone would suffice.

Acceptance: pyrite-conductor specifies the hybrid state model as the canonical pattern. Workers write both records; conductor reads both.

### 8. Consolidated deploy-ready index is the load-bearing output for users

110 individual triage-status Pyrite tasks are queryable but not scannable. The user can't read 110 tasks to decide what to ship next. A consolidated `_DEPLOY-READY-INDEX.md` (single document, ~10KB, aggregates findings across all slices) is the artifact that actually answers "what should I ship next?"

Acceptance: triage-mode synthesis produces a consolidated deploy-ready index as a first-class deliverable, not just per-slice summary files.

## Acceptance criteria

- A `pyrite-conductor` skill that accepts a KB name as argument
- Reads `<kb>/kb.yaml` or `<kb>/conductor.yaml` for orchestration config (roles, state machine, synthesis matrix, dispatch policy, goals, quality rules)
- Implements the six-step tick loop (check → absorb → synthesize → groom → dispatch → report) as the primitive
- Bootstrap-mapping for legacy readiness values supported via config reference
- Pre-gate logic (self-supersession check, in-flight overlap detection, promoted-to-draft check for brief→draft promotion, stop-condition checks) parameterized per KB
- Goal-aware Step 3 synthesis (work-unit selection respects declared KB goals)
- **Triage-mode support** with distinct roles per work-unit-type, per-mode dispatch caps, width-vs-depth tuning honoring natural-cluster sizes
- **Worker output robustness pattern** as default scaffolding: preliminary frontmatter write, deep work, final update, Pyrite task creation
- **Idempotent dispatch primitive**: refuses to redispatch a done task without a new cycle number or explicit `--force`
- **Cross-piece factual-reconciliation registry** as a first-class deliverable
- **Peer-coverage scanner role** in the standard workflows set (see "Worth specifically calling out" section)
- **Hybrid state model** (frontmatter logs + Pyrite tasks) as canonical pattern
- **Triage-mode synthesis** produces consolidated deploy-ready index
- Template-assembly pipeline (standard.boilerplate + standard.workflow[role] + kb.workflow[role] + kb._extensions + kb._quality_rules + task_brief) implemented as conductor primitive
- Migration: investigation-conductor and draft-conductor either rewritten as thin wrappers over pyrite-conductor with their domain config + worker templates, OR deprecated with a clean migration window
- Documentation: a "how to add conductor support to a new Pyrite KB" runbook in the pyrite KB

## Related

- `/Users/markr/tcp-skills/plugins/tcp-skills/skills/investigation-conductor/` — current investigation-conductor skill (cascade-research backlog)
- `/Users/markr/tcp-skills/plugins/tcp-skills/skills/draft-conductor/` — current draft-conductor skill (drafts backlog)
- `add-task-reset-command-for-stale-claims.md` — adjacent task-system improvement that the generalized conductor would need
- May 2026 triage waves on drafts KB (15+15+40 pieces) validated the pattern across editorial-cycle AND triage workflows
- The `goals` and `pressure_windows` design echoes the conductor's existing news-cycle-attachment handling but makes it declarative instead of implicit
