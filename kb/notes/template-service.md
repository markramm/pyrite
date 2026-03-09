---
id: template-service
title: Template Service
type: component
tags:
- core
- templates
kind: service
path: pyrite/services/template_service.py
owner: markr
---

Manages user-defined markdown templates that scaffold new KB entries. Templates are stored as markdown files with YAML frontmatter in `_templates/` within each KB directory. Supports variable placeholders (`{{title}}`, `{{date}}`, etc.), preset-based template provisioning, and rendering with auto-populated built-in variables.
