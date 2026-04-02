---
id: oauth-providers
title: OAuth Providers
type: component
tags:
- core
- auth
kind: service
path: pyrite/services/oauth_providers.py
owner: markr
dependencies: '["auth_service"]'
---

Protocol-based OAuth provider abstraction with a concrete GitHub implementation. Handles OAuth code exchange (token retrieval via httpx) and normalized user profile fetching. Provides OAuthToken and OAuthProfile dataclasses for provider-agnostic identity. Used by AuthService for 'Sign in with GitHub' flow.
