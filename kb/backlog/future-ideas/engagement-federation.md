---
type: backlog_item
title: "Federate Engagement Data Across Installs"
kind: feature
status: proposed
priority: medium
effort: XL
tags: [federation, engagement]
---

Design a federation protocol for engagement data (votes, reputation, reviews) across pyrite installs. Options include lightweight file format (_votes.json), CRDTs, or ActivityPub-style federation.

Currently engagement data is local-only SQLite — lost on clone. This is by design (ADR-0003) but limits multi-site collaboration.
