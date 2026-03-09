---
id: llm-rubric-evaluator
title: LLM Rubric Evaluator
type: component
tags:
- core
- ai
- qa
kind: service
path: pyrite/services/llm_rubric_evaluator.py
owner: markr
dependencies: '["llm_service"]'
---

LLM-assisted rubric evaluation for judgment-only rubric items. Handles rubric items that require semantic judgment (e.g., 'Entry body explains the why, not just the what') by batching them into a single LLM call per entry. Gracefully degrades when no LLM is configured — returns empty results. Used by QAService for quality assessment.
