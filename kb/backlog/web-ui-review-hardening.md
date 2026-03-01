---
id: web-ui-review-hardening
title: "Web UI Review and Hardening"
type: backlog_item
tags:
- quality
- frontend
- web-ui
- hardening
- launch
kind: improvement
priority: high
effort: M
status: proposed
links:
- ux-accessibility-fixes
- playwright-integration-tests
- demo-site-deployment
---

## Problem

The web UI is the least exercised part of the project but will be the first thing new users see — on the demo site, in screenshots, and when they `docker compose up` locally. It needs a systematic review and hardening pass before going public.

Areas of concern:

- **Visual polish**: inconsistent spacing, typography, color usage across pages
- **Error handling**: API failures may show raw errors or blank screens instead of helpful messages
- **Empty states**: pages with no data (new install, empty KB) may look broken rather than guiding the user
- **Loading states**: slow API responses may leave users staring at blank content
- **Navigation**: is the information architecture clear to a first-time user?
- **Responsive design**: mobile/tablet experience untested
- **Browser compatibility**: only tested in Chrome during development
- **Dark mode**: if supported, is it consistent? If not, should it be?
- **Performance**: large KB rendering (500+ entries in search, big graphs) may be slow

## Proposed Solution

### 1. Visual audit (S)

Walk every route and screenshot it. Flag inconsistencies in:
- Spacing and padding
- Font sizes and weights
- Color palette usage
- Component styling (buttons, cards, inputs, tables)
- Light/dark mode consistency

### 2. Error and empty state audit (S)

For each page, test:
- What happens when the API is down?
- What happens when the KB is empty?
- What happens when a search returns no results?
- What happens when an entry doesn't exist (404)?

Add proper error boundaries, loading skeletons, and helpful empty states.

### 3. First-run experience (S)

A new user who just installed Pyrite and opens the web UI should see:
- A welcome/onboarding state (not a blank page)
- Clear guidance on how to create their first KB and entry
- The UI should look intentional, not broken

### 4. Responsive and cross-browser (S)

- Test on mobile and tablet viewports
- Test on Firefox and Safari
- Fix layout breaks, overflow issues, touch targets

### 5. Performance check (S)

- Profile search results page with 500+ entries
- Profile graph view with large entry sets
- Add pagination or virtual scrolling where needed

## Relationship to Other Items

- **UX & Accessibility Fixes** (`ux-accessibility-fixes`): specific known issues, subsumable into this broader review
- **Playwright tests** (`playwright-integration-tests`): tests validate the fixes stick
- **Demo site** (`demo-site-deployment`): this work makes the demo site presentable

## Success Criteria

- Every route has been manually reviewed and screenshotted
- No blank/broken states on empty data or API errors
- First-run experience guides the user
- Responsive on mobile viewports (360px+)
- Works in Chrome, Firefox, Safari
- No console errors in normal usage
