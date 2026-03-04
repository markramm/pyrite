# Awesome Pyrite Plugins

Curated list of Pyrite plugins. Plugins add custom entry types, MCP tools, CLI commands, validators, and presets.

## Official Plugins

These plugins ship in-tree in the [`extensions/`](https://github.com/markramm/pyrite/tree/main/extensions) directory and are installable as separate packages.

---

### Software KB

Structured knowledge management for software teams -- ADRs, design docs, coding standards, component documentation, backlog tracking, and runbooks.

**Install:** `pip install -e extensions/software-kb`

**Adds:**

- **Entry types:** `adr`, `design_doc`, `standard`, `component`, `backlog_item`, `runbook`
- **MCP tools:** `sw_adrs`, `sw_component`, `sw_standards`, `sw_backlog`, `sw_create_adr`, `sw_create_backlog_item`
- **CLI commands:** `pyrite sw`
- **Preset:** `software`
- **Workflows:** ADR lifecycle, backlog workflow
- **Relationships:** `implements`, `supersedes`, `documents`, `depends_on`, `tracks` (and inverses)

**Use case:** Engineering teams that want to keep architecture decisions, coding standards, component docs, and backlogs in version-controlled markdown alongside their code.

[Full docs](https://github.com/markramm/pyrite/tree/main/extensions/software-kb)

---

### Zettelkasten

Personal knowledge management with atomic note-taking, CEQRC workflow, maturity tracking, and literature notes.

**Install:** `pip install -e extensions/zettelkasten`

**Adds:**

- **Entry types:** `zettel`, `literature_note`
- **MCP tools:** `zettel_inbox`, `zettel_graph`
- **CLI commands:** `pyrite zettel`
- **Preset:** `zettelkasten`
- **Relationships:** `elaborates`, `branches_from`, `synthesizes` (and inverses)

**Use case:** Researchers, writers, and lifelong learners who practice Zettelkasten-style note-taking and want AI agents to help process their inbox of fleeting notes into permanent knowledge.

[Full docs](https://github.com/markramm/pyrite/tree/main/extensions/zettelkasten)

---

### Encyclopedia

Wikipedia-inspired collaborative knowledge base with quality assessment, review workflows, protection levels, and talk pages.

**Install:** `pip install -e extensions/encyclopedia`

**Adds:**

- **Entry types:** `article`, `talk_page`
- **MCP tools:** `wiki_quality_stats`, `wiki_review_queue`, `wiki_stubs`, `wiki_submit_review`, `wiki_assess_quality`, `wiki_protect`
- **CLI commands:** `pyrite wiki`
- **Preset:** `encyclopedia`
- **Workflows:** Article review workflow
- **DB tables:** Encyclopedia review tables

**Use case:** Teams building shared reference documentation that needs editorial quality control -- quality ratings (stub through Featured Article), peer review queues, and page protection.

[Full docs](https://github.com/markramm/pyrite/tree/main/extensions/encyclopedia)

---

### Social

Everything2-inspired community knowledge base with user-authored writeups, voting, reputation tracking, and author-only editing enforcement.

**Install:** `pip install -e extensions/social`

**Adds:**

- **Entry types:** `writeup`, `user_profile`
- **MCP tools:** `social_top`, `social_newest`, `social_reputation`, `social_vote`, `social_post`
- **CLI commands:** `pyrite social`
- **Preset:** `social`
- **Hooks:** `before_save` (author check), `after_save` (count updates), `after_delete` (reputation adjustment)
- **DB tables:** Social vote and reputation tables

**Use case:** Communities that want a collaborative writing platform where members contribute essays, reviews, how-tos, and stories with upvote/downvote reputation mechanics.

[Full docs](https://github.com/markramm/pyrite/tree/main/extensions/social)

---

### Cascade

Investigative journalism knowledge management covering actors, organizations, events, themes, mechanisms, scenes, victims, statistics, and timelines.

**Install:** `pip install -e extensions/cascade`

**Adds:**

- **Entry types:** `actor`, `cascade_org`, `cascade_event`, `timeline_event`, `theme`, `victim`, `statistic`, `mechanism`, `scene`, `solidarity_event`
- **MCP tools:** `cascade_actors`, `cascade_timeline`, `cascade_network`, `solidarity_timeline`, `solidarity_infrastructure_types`, `cascade_capture_lanes`
- **KB types:** `cascade-research`, `cascade-timeline`, `cascade-solidarity`
- **Relationships:** `member_of`, `investigated`, `funded_by`, `capture_mechanism`, `built_on`, `responded_to` (and inverses)

**Use case:** Investigative journalists and researchers mapping networks of actors, organizations, events, and power structures across large-scale investigations.

[Full docs](https://github.com/markramm/pyrite/tree/main/extensions/cascade)

---

### Task

Agent-oriented task management with a workflow state machine, parent-child decomposition, dependency tracking, evidence linking, and checkpoints.

**Install:** `pip install -e extensions/task`

**Adds:**

- **Entry types:** `task`
- **MCP tools:** `task_list`, `task_status`, `task_create`, `task_update`, `task_claim`, `task_decompose`, `task_checkpoint`
- **CLI commands:** `pyrite task`
- **Preset:** `task`
- **Workflows:** Task workflow (open, claimed, in_progress, blocked, review, done, failed)
- **Hooks:** `before_save` (transition validation), `after_save` (parent rollup)
- **Relationships:** `subtask_of`, `produces` (and inverses)

**Use case:** AI agent orchestration -- agents claim tasks atomically, decompose work into subtasks, log checkpoints with confidence scores, and link evidence entries as they go.

[Full docs](https://github.com/markramm/pyrite/tree/main/extensions/task)

---

## Community Plugins

Community plugins will be listed here. See [Building Your Own](#building-your-own) to create and submit one.

## Building Your Own

Pyrite plugins are standard Python packages that expose entry types, MCP tools, CLI commands, validators, and presets through a simple class interface.

**Resources:**

- **Plugin writing tutorial:** [`docs/tutorials/plugin-writing.md`](tutorials/plugin-writing.md)
- **Claude Code skill:** Use the `extension-builder` skill in Claude Code to scaffold a new plugin interactively
- **Reference implementations:** Browse the [extensions/](https://github.com/markramm/pyrite/tree/main/extensions) directory for working examples

**Submitting a community plugin:**

1. Build and test your plugin against the latest Pyrite release
2. Open a PR to [markramm/pyrite](https://github.com/markramm/pyrite) adding your plugin to the Community Plugins section of this page
3. Include a link to your plugin's repository, a one-line description, and what it adds
