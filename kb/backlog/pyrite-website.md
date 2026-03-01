---
id: pyrite-website
title: "Pyrite Website (pyrite.dev)"
type: backlog_item
tags:
- feature
- website
- launch
- marketing
kind: feature
priority: high
effort: M
status: planned
links:
- demo-site-deployment
- awesome-plugins-page
- launch-plan
- roadmap
---

## Problem

Pyrite needs a web presence beyond the GitHub repo. Visitors from HN, Reddit, or blog posts need three things: understand what Pyrite is (marketing), learn how to use it (docs), and try it live (demo). Currently these are all conflated into the README and a planned demo site. A standalone website separates these concerns and gives each the space it needs.

## Solution

A separate repository (`pyrite-dev/pyrite-website` or similar) hosting the Pyrite marketing site, documentation, and linking to the demo site.

### Three-Layer Web Presence

**Layer 1 — Marketing site (pyrite.dev)**

Static site (Astro, Hugo, or plain HTML/CSS) that tells the story:

- Landing page: "Pyrite turns your AI into a domain expert" — the elevator pitch, key visuals, call-to-action
- How it works: three portals (CLI, MCP, Web UI), schema-as-config, plugin system
- Use cases: software teams, investigators, PKM, community hubs
- Plugins page: links to awesome-plugins-page and eventually the extension registry
- Getting started: quick install commands, link to full tutorial
- Links to demo site, GitHub, Discord, PyPI

Lightweight, fast, SEO-friendly. No backend required — can be hosted on GitHub Pages, Netlify, or Cloudflare Pages for free.

**Layer 2 — Docs section (pyrite.dev/docs or docs.pyrite.dev)**

Documentation rendered from the Pyrite KB itself:

- Read-only access to the Pyrite project KB (ADRs, components, standards, designs)
- Getting Started tutorial
- Plugin writing tutorial
- API reference
- Architecture overview

This is the "dogfooding as documentation" play — visitors see Pyrite's own knowledge infrastructure rendered as documentation. Could be:
- A Pyrite web UI instance in read-only mode pointed at the project KB
- Static site generation from KB markdown files
- Both (static for speed, link to live instance for interactive exploration)

**Layer 3 — Demo site (demo.pyrite.dev)**

Live Pyrite instance (separate from marketing site) running the full web UI:

- Loaded with curated awesome-list KBs (journalism KBs, public research KBs)
- Read-only for anonymous visitors
- Write access for registered users (BYOK AI, create entries in demo KB)
- Community guidelines enforced via KB-level intent layer
- Runs on Postgres backend with auth and rate limiting

### Domain Structure

| URL | Purpose | Hosting |
|-----|---------|---------|
| pyrite.dev | Marketing + landing page | Static (GitHub Pages / Netlify) |
| pyrite.dev/docs | Documentation | Static or Pyrite read-only instance |
| demo.pyrite.dev | Live demo with curated KBs | Fly.io / Railway with Postgres |

### Separate Repository

The website lives in its own repo (`pyrite-website`) because:

- Marketing site iterates independently of core releases
- Different toolchain (static site generator vs Python/SvelteKit)
- Different contributors (marketing, design, content vs engineering)
- Demo site deployment is already tracked separately (#85)

## Prerequisites

- Demo site deployment (#85) — the live demo layer
- Awesome plugins page (#109) — content for the plugins section
- Getting Started tutorial — content for the docs section
- Plugin writing tutorial (#108) — content for the docs section

## Success Criteria

- pyrite.dev (or equivalent domain) live with landing page, docs section, and link to demo
- Landing page loads in under 2 seconds, mobile-responsive
- Docs section surfaces the Pyrite KB as navigable documentation
- Demo site linked prominently from landing page and docs
- Blog post hosting (for launch content pieces) integrated into the site
- SEO basics: meta tags, OpenGraph, sitemap

## Launch Context

Ships as part of 0.12 launch prep. The website is the first thing linked in every blog post, HN submission, and README. Without it, visitors land on a GitHub README — which is fine for developers but misses the broader audience. The website is the "front door" that routes visitors to the right experience: docs for learners, demo for evaluators, GitHub for contributors.
