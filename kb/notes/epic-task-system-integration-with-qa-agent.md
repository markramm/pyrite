---
id: epic-task-system-integration-with-qa-agent
title: 'Epic: Task system integration with QA agent'
type: backlog_item
tags:
- task-system
- qa
- epic
kind: epic
effort: M
links:
- target: auto-create-qa-validation-tasks-on-entry-save
  relation: has_subtask
  kb: pyrite
- target: link-qa-assessment-entries-as-task-evidence
  relation: has_subtask
  kb: pyrite
- target: entries-needing-qa-as-a-task-query
  relation: has_subtask
  kb: pyrite
- target: qa-agent-workflow-on-task-primitives
  relation: has_subtask
  kb: pyrite
---

Phase 4 of the Coordination/Task System. Integrates the task primitives with the QA workflow so QA validation becomes task-driven. Research and QA agents use the same coordination layer.

## Acceptance Criteria

- QA validation tasks auto-created on entry save
- QA assessment entries linked as task evidence
- Entries needing QA queryable as a task list
- QA agent workflow uses task primitives (claim, validate, checkpoint, complete)

