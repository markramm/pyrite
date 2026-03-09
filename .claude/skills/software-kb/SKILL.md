---
name: software-kb
description: "Use when working with a software-type Pyrite KB for development workflow: pulling work items, checking the board, claiming tasks, submitting for review, or managing backlog. Covers the full kanban cycle via sw_* MCP tools and CLI commands."
---

# Software KB Skill

Pull-based development workflow for software-type Pyrite knowledge bases. Covers the kanban cycle from backlog to done, using `sw_*` MCP tools (for agents) and `pyrite sw` CLI commands (for humans).

**Announce at start:** "I'm using the software-kb skill."

---

## The Development Loop

```
  Pull         Context       Claim         Work         Submit       Review
┌────────┐   ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐
│ What's  │──>│ Gather   │──>│ Lock the │──>│ Do the  │──>│ Move to  │──>│ Approve  │
│ next?   │   │ context  │   │ item     │   │ work    │   │ review   │   │ or reject│
└────────┘   └──────────┘  └──────────┘  └─────────┘  └──────────┘  └──────────┘
sw_pull_next  sw_context    sw_claim       (you)        sw_submit     sw_review
              _for_item
```

### Status Flow

```
proposed → accepted → in_progress → review → done
                          ↑                    │
                          └── changes_requested─┘
```

Side exits: `proposed → wont_do`, `proposed → deferred → proposed`, `done → retired`.

---

## MCP Tools Quick Reference

### Read tier (safe, no side effects)

| Tool | Purpose | Key args |
|------|---------|----------|
| `sw_board` | Kanban board — all items grouped by lane | `kb_name` |
| `sw_pull_next` | Recommend highest-priority unblocked accepted item | `kb_name` |
| `sw_review_queue` | Items awaiting review, sorted by wait time | `kb_name` |
| `sw_context_for_item` | Full context bundle: linked ADRs, components, validations, conventions, reviews | `item_id`, `kb_name` |
| `sw_backlog` | List/filter backlog items | `kb_name`, `status`, `priority`, `kind` |
| `sw_adrs` | List ADRs | `kb_name`, `status` |
| `sw_milestones` | Milestones with completion stats | `kb_name` |
| `sw_component` | Find component docs | `kb_name`, `path`, `name` |
| `sw_validations` | Programmatic checks (pass/fail criteria) | `kb_name`, `category` |
| `sw_conventions` | Development conventions (judgment guidance) | `kb_name`, `category` |
| `sw_standards` | All standards (validations + conventions) | `kb_name`, `category` |

### Write tier (mutates state)

| Tool | Purpose | Key args |
|------|---------|----------|
| `sw_claim` | Claim item: `accepted → in_progress` + set assignee (CAS) | `item_id`, `kb_name`, `assignee` |
| `sw_submit` | Submit for review: `in_progress → review` | `item_id`, `kb_name` |
| `sw_review` | Record review outcome: `review → done` or `review → in_progress` | `item_id`, `kb_name`, `outcome`, `reviewer`, `feedback` |
| `sw_create_adr` | Create auto-numbered ADR | `title`, `kb_name` |
| `sw_create_backlog_item` | Create backlog item | `title`, `kind` |

---

## CLI Equivalents

```bash
pyrite sw board -k <kb>                # Kanban board
pyrite sw backlog -k <kb>              # List backlog
pyrite sw backlog -k <kb> --status accepted  # Filtered
pyrite sw review-queue -k <kb>         # Review queue
pyrite sw claim <item-id> -k <kb> --assignee <name>
pyrite sw submit <item-id> -k <kb>     # Submit for review
pyrite sw adrs -k <kb>                 # List ADRs
pyrite sw new-adr --title "..." -k <kb>  # Create ADR
pyrite sw components -k <kb>           # Component docs
pyrite sw validations -k <kb>          # Validations
pyrite sw conventions -k <kb>          # Conventions
pyrite sw milestones -k <kb>           # Milestones
```

---

## Workflow Protocols

### Starting Work (Agent)

```
1. sw_pull_next(kb_name=...)           → get recommendation
2. sw_context_for_item(item_id, kb)    → read linked ADRs, validations, reviews
3. sw_claim(item_id, kb, assignee=...) → lock the item (CAS — fails if already claimed)
4. Do the work
5. sw_submit(item_id, kb)              → move to review
```

If `sw_pull_next` returns `"reason": "WIP limit reached"`, finish existing in-progress work first.

If `sw_pull_next` returns blocked items, check if you can unblock them by completing their dependencies.

### Reviewing Work

```
1. sw_review_queue(kb_name=...)        → see what needs review
2. sw_context_for_item(item_id, kb)    → check prior reviews, linked validations
3. Evaluate the work against Definition of Done
4. sw_review(item_id, kb,
     outcome="approved"|"changes_requested",
     reviewer=...,
     feedback=...)                      → record outcome
```

- `approved` → transitions to `done`
- `changes_requested` → transitions back to `in_progress` (feedback required)
- Prior review feedback is surfaced in `sw_context_for_item` so rework addresses specific issues
- `rework_count` in the review queue shows how many times an item has been sent back

### Checking the Board

```
sw_board(kb_name=...)
```

Returns lanes with item counts and WIP limit status. Use this for situational awareness — where is work piling up?

---

## Backlog Item Fields

| Field | Values | Notes |
|-------|--------|-------|
| `kind` | `feature`, `bug`, `tech_debt`, `improvement`, `spike`, `epic` | What type of work |
| `status` | `proposed`, `accepted`, `in_progress`, `review`, `done`, `wont_do` | Where in the flow |
| `priority` | `critical`, `high`, `medium`, `low` | Pull order |
| `effort` | `XS`, `S`, `M`, `L`, `XL` | T-shirt sizing |
| `assignee` | string | Set by `sw_claim` |

### Priority Semantics

- **critical** — blocking other work or production issue; pull immediately
- **high** — important for current milestone; pull before medium
- **medium** — default; pull in order
- **low** — nice-to-have; pull when nothing else is available

`sw_pull_next` ranks by priority then age (oldest first within same priority).

---

## Dependencies

Backlog items can have `blocked_by` / `blocks` relationships:

- `sw_pull_next` skips blocked items automatically
- `sw_claim` refuses to claim a blocked item
- `sw_context_for_item` shows dependency status (resolved or not)
- Blocked items appear in `sw_pull_next` response under `blocked_items`

To unblock work, complete the blocking item first.

---

## Linking to Context

Backlog items gain value from links to other entries:

| Link target | Why |
|-------------|-----|
| ADRs | Architectural decisions that constrain the work |
| Components | Code areas affected |
| Validations | Automated checks to run |
| Conventions | Style/approach guidance to follow |
| Milestones | Which milestone this contributes to |
| Other backlog items | `blocked_by` / `blocks` dependencies |

`sw_context_for_item` assembles all of these in one call. Use it before starting work — it's the single source of truth for what an item needs.

---

## Anti-patterns

| Don't | Do instead |
|-------|------------|
| Skip `sw_context_for_item` before working | Always gather context — prior reviews, linked validations, dependencies |
| Claim multiple items at once | Respect WIP limits; finish one before pulling another |
| Submit without running validations | Check `sw_context_for_item` for linked programmatic validations; run them |
| Review without feedback | Always provide `feedback`, even for approvals ("LGTM" is fine) |
| Ignore `rework_count` | Items sent back multiple times likely need a different approach |
| Create items without `kind` | Kind drives board grouping and reporting |
