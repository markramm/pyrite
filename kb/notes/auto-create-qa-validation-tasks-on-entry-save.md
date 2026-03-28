---
id: auto-create-qa-validation-tasks-on-entry-save
title: Auto-create QA validation tasks on entry save
type: backlog_item
tags:
- task-system
- qa
links:
- target: epic-task-system-integration-with-qa-agent
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
effort: M
---

When a new entry is saved to a KB with QA enabled, automatically create a QA validation task linked to that entry. The task should be in open status, ready for a QA agent to claim.

## Impacted Files
- pyrite/services/kb_service.py (after_save hook)
- pyrite/services/task_service.py

## Acceptance Criteria
- New entry save triggers QA task creation (configurable per KB)
- Task links to the entry via produces/produced_by relation
- Task includes relevant validation rules in its body
- Can be disabled per KB via kb.yaml config
