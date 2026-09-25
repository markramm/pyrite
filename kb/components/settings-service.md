---
id: settings-service
title: Settings Service
type: component
tags:
- core
- settings
importance: 5
kind: service
path: pyrite/services/settings_service.py
owner: core
---

Instance-wide settings store (the setting table): get, all, set, delete. The REST settings endpoints read and write through it (#380); secret masking and the admin rule for operator settings stay in server/endpoints/settings_ep.py, the surface that shows values. Provided by get_settings_service in server/api.py. The AI-settings precedence (a DB setting over config, today in api.get_llm_service) is meant to move here with the composition root (#382).
