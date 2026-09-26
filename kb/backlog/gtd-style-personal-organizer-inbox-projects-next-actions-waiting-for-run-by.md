---
id: gtd-style-personal-organizer-inbox-projects-next-actions-waiting-for-run-by
title: 'GTD-style personal organizer: inbox, projects, next actions, waiting-for, run by agents'
type: backlog_item
tags:
- enhancement
- plugin
- agents
importance: 5
kind: feature
status: proposed
priority: low
effort: L
rank: 0
---

Maintainer idea, 2026-09-26. Further down the backlog.

A Getting Things Done style personal filing system on Pyrite. It works through an inbox-first interface, and agents in Claude Code or Cowork act on the user's behalf.

## What it does
- **Capture:** an inbox that agents and the user can drop items into, for example a decision recorded during a session or a follow-up noticed while working. One CLI command, so any agent can use it.
- **Clarify and organize:** inbox items become next actions under a project, reference, someday/maybe, or trash. Agents can propose where each item belongs; the user confirms, or agents file it directly for low-stakes items.
- **Next actions by project,** with contexts (for example @computer or @calls) and an easy "what can I do now" view.
- **Waiting-for:** delegated actions, tracked with who owns them and when to follow up. Agents can file these when they hand work off.
- **The weekly review:** stale projects (no next action), an inbox that has aged, waiting-for items that are overdue.

## Shape (to be decided in a groom or spike)
- **Build it as an out-of-tree plugin on the published plugin contract.** Candidate first plugin for the maintainer's out-of-tree idea (2026-09-26).
- **Use the CLI as the agent interface.** A pi or Claude Code agent uses `pyrite` commands with pipes and `--json`; there is no special agent API.
- **Reuse existing parts where they fit:**
  - the core task type and task_claim/checkpoint (evolved from software-kb's claimable work);
  - links for project membership;
  - the KB as files in git, which gives shared memory across agents and over time.
- **Personal first:** a single user's KB. Multi-user delegation comes later.

## Open questions
- Is a next action a task entry with a project link, or its own type?
- How are contexts modelled: tags or a field?
- What does the inbox-management interface look like: CLI views, the web UI, or both?
- What may an agent file without asking, and what must it propose?
