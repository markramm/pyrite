---
id: link-qa-assessment-entries-as-task-evidence
title: Link QA assessment entries as task evidence
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
effort: S
---

When a QA agent completes validation and creates a QA assessment entry, automatically link it as evidence on the corresponding QA task. This creates a traceable chain: entry -> QA task -> QA assessment.

## Impacted Files
- pyrite/services/qa_service.py
- pyrite/services/task_service.py

## Acceptance Criteria
- QA assessment entries automatically linked as evidence on QA tasks
- Evidence links visible in task_status output
- Provenance chain traceable from entry to assessment
