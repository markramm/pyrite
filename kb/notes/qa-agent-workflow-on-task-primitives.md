---
id: qa-agent-workflow-on-task-primitives
title: QA agent workflow on task primitives
type: backlog_item
tags:
- task-system
- qa
kind: feature
effort: M
links:
- target: epic-task-system-integration-with-qa-agent
  relation: subtask_of
  kb: pyrite
---

Build the QA agent workflow on top of task primitives: claim QA task, run validation, checkpoint progress, create assessment entry as evidence, complete task. This replaces ad-hoc QA scripts with a structured, trackable workflow.

## Impacted Files
- pyrite/services/qa_service.py
- Documentation / skill updates

## Acceptance Criteria
- QA agent can claim -> validate -> checkpoint -> complete using task primitives
- Progress visible via task_status with confidence tracking
- Failed validations create tasks for human review
- Workflow documented in software-kb skill or QA docs

