---
id: hosting-security-requirements
type: design_doc
title: "Hosting Security Requirements for Investigative Journalists"
status: draft
author: markr
date: "2026-03-23"
reviewers: []
tags: [security, privacy, deployment, journalism, threat-model]
---

## Purpose

This document defines security and privacy requirements for Pyrite deployments, with particular attention to the threat model facing investigative journalists. Requirements are informed by documented patterns of legal compulsion against centralized service providers (see: Proton Mail transparency report analysis, MLAT laundering of law enforcement requests against activists, Swiss flat-rate surveillance billing changes).

The core principle: **minimize what exists, distribute what remains, make centralized collection architecturally impossible rather than contractually promised.**

## Deployment Tiers

Pyrite supports three deployment models with different trust assumptions. Requirements vary by tier.

### Tier 1: Self-Hosted (Maximum Security)
Journalist runs the docker container on their own hardware. No third-party provider in the chain. Legal compulsion requires a physical warrant under the journalist's home jurisdiction.

### Tier 2: Journalist-Managed VPS (Moderate Security)
Journalist spins up the container on a VPS of their choosing. They control the relationship with the hosting provider and evaluate their own threat model. Pyrite's security properties should hold regardless of hosting provider.

### Tier 3: TCP Managed Hosting (Convenience)
TCP operates shared infrastructure for journalists who don't want to manage their own deployment. TCP becomes the service provider and assumes the legal compulsion exposure that comes with it.

---

## REQ-1: No IP Address Logging

### REQ-1.1: Application-Level IP Logging
- Pyrite MUST NOT log client IP addresses in application logs by default.
- Pyrite MUST NOT store IP addresses in any database, cache, or persistent storage.
- Pyrite MUST NOT include IP addresses in error logs, audit trails, or analytics.
- There MUST be no configuration option to enable IP logging. This is a design constraint, not a policy choice. If the capability doesn't exist, it cannot be compelled.

### REQ-1.2: Web Server / Reverse Proxy Configuration
- The default docker container configuration MUST configure the web server (nginx, caddy, etc.) to NOT log access IPs.
- If access logs are enabled for debugging, they MUST use a placeholder or hash instead of real IP addresses.
- Documentation MUST warn operators about web server default logging behavior and provide hardened configurations.

### REQ-1.3: Audit Checklist
- [ ] Grep entire codebase for `request.remote_addr`, `X-Forwarded-For`, `X-Real-IP`, `REMOTE_ADDR` and equivalent patterns.
- [ ] Verify no ORM models or database columns store IP-like data.
- [ ] Verify docker container entrypoint scripts configure web server log format without IPs.
- [ ] Verify error handling / exception reporting does not capture request metadata containing IPs.

---

## REQ-2: Minimal Account Metadata

### REQ-2.1: Account Creation
- For self-hosted (Tier 1) and journalist-managed (Tier 2) deployments, Pyrite SHOULD operate without user accounts entirely -- single-user or shared-secret access is sufficient.
- For managed hosting (Tier 3), account creation MUST NOT require:
  - Real name
  - Phone number
  - Recovery email address
  - Any identity-linking information
- Accounts SHOULD be identified by a username/handle only.
- Account creation MUST be possible over Tor without CAPTCHAs or additional verification that would degrade anonymity.

### REQ-2.2: Account Metadata Storage
- Pyrite MUST NOT store account creation timestamps with greater precision than the calendar date.
- Pyrite MUST NOT store the IP address or user agent used at account creation.
- Pyrite MUST NOT store login history, session history, or access timestamps per-account.

### REQ-2.3: Audit Checklist
- [ ] Review account/user model for all stored fields. Document each field and justify its necessity.
- [ ] Verify no "created_at" or "last_login" timestamps with sub-day precision.
- [ ] Verify no session table retains historical login records.
- [ ] Verify registration flow does not require identity-linking data.

---

## REQ-3: Private Repository Encryption

### REQ-3.1: Encryption at Rest (Tier 3 Managed Hosting)
- Private KB content MUST be encrypted at rest on the server.
- For managed hosting, the strongest posture is zero-knowledge architecture: content is encrypted client-side and the server holds only opaque blobs.
- If zero-knowledge is not feasible for features requiring server-side processing (search indexing, MCP integration), this MUST be clearly documented in the threat model so journalists can make informed decisions.

### REQ-3.2: Encryption Key Management
- Encryption keys for private KBs MUST NOT be stored alongside the encrypted data.
- For zero-knowledge deployments, keys MUST reside exclusively on the client.
- For server-side processing deployments, keys SHOULD be held in memory only and derived from user credentials, never written to disk in plaintext.

### REQ-3.3: What a Court Order Could Reach
- Document explicitly what data a court order served on a Tier 3 managed hosting operator would be able to obtain. This document MUST be published and accessible to all users.
- The goal is: encrypted content blobs (useless without keys), minimal account metadata (per REQ-2), and no IP logs (per REQ-1).

### REQ-3.4: Audit Checklist
- [ ] Map all data flows for private KB content: creation, storage, retrieval, search, MCP access.
- [ ] Identify every point where plaintext private content exists on the server (in memory or on disk).
- [ ] Verify encryption at rest implementation -- algorithm, key derivation, key storage.
- [ ] Document the "court order disclosure surface" -- everything that could be handed over under legal compulsion.

---

## REQ-4: Git-Native Security Properties

### REQ-4.1: Leverage Git's Existing Security Model
- Pyrite's git-native storage SHOULD leverage git's built-in integrity verification (SHA hashes on every object).
- For private repos, git-crypt or similar transparent encryption SHOULD be evaluated for encrypting repository content while maintaining git's structural properties.

### REQ-4.2: No Metadata Leakage Through Git
- Git commit metadata (author name, email, timestamps) MUST be reviewed for information leakage in private KBs.
- For managed hosting of private repos, commit metadata SHOULD be as minimal as possible -- pseudonymous author identities, reduced timestamp precision.
- `.git/config` and other git configuration files MUST NOT contain identity-linking information in hosted deployments.

### REQ-4.3: Audit Checklist
- [ ] Review what metadata git stores by default in commits, refs, and config.
- [ ] Verify private repo commits don't leak real names or email addresses unless the journalist explicitly configures them.
- [ ] Evaluate git-crypt or git-remote-gcrypt for transparent encryption of private repos.

---

## REQ-5: Docker Container Security

### REQ-5.1: Container Hardening
- The docker container MUST run as a non-root user.
- The container MUST use a minimal base image (alpine or distroless preferred).
- The container MUST NOT include unnecessary tools (curl, wget, ssh, etc.) that could be used in a compromise.
- The container SHOULD use read-only filesystem where possible, with explicit writable volumes only for data directories.

### REQ-5.2: Network Minimization
- The container MUST expose only the ports necessary for operation (typically HTTP/HTTPS only).
- The container MUST NOT phone home, send telemetry, or make any outbound network requests that aren't explicitly initiated by the user.
- DNS queries SHOULD be minimized and documented.

### REQ-5.3: Volume Mounts and Data Isolation
- Persistent data MUST be stored in explicitly defined docker volumes, not baked into the container image.
- Documentation MUST clearly explain what's in each volume and what would be lost if the volume is destroyed.
- Backup and restore procedures MUST be documented.

### REQ-5.4: Audit Checklist
- [ ] Review Dockerfile for base image, user configuration, installed packages.
- [ ] Verify no outbound network calls on startup or during normal operation.
- [ ] Verify all persistent data paths are documented and mapped to volumes.
- [ ] Run container security scanner (trivy, grype) against built image.
- [ ] Verify container runs successfully with `--read-only` flag plus explicit tmpfs/volume mounts.

---

## REQ-6: MCP Server Security

### REQ-6.1: MCP Access to Private Content
- MCP server integration MUST respect KB-level access controls. An MCP connection MUST NOT be able to read private KBs without explicit authorization.
- MCP tool calls MUST NOT log query content, KB content, or results in a way that persists to disk.
- MCP connections MUST be authenticated. Unauthenticated MCP access MUST NOT be possible in default configuration.

### REQ-6.2: MCP and Zero-Knowledge Tension
- Document the tension between MCP integration (which requires the server to process content) and zero-knowledge architecture (which requires the server to NOT process content).
- If MCP integration requires server-side access to plaintext, this MUST be clearly communicated in the threat model.
- Consider an architecture where MCP processing happens client-side, with the MCP server running locally alongside the Pyrite client rather than on the hosted server.

### REQ-6.3: Audit Checklist
- [ ] Map all MCP tool calls and verify they respect KB access controls.
- [ ] Verify MCP server does not log queries or results to persistent storage.
- [ ] Verify MCP authentication is enforced by default.
- [ ] Document which MCP features require server-side plaintext access.

---

## REQ-7: Managed Hosting Operator Requirements (Tier 3)

### REQ-7.1: Transparency
- TCP MUST publish a transparency report documenting all legal orders received, contested, and complied with -- modeled on but improving upon Proton's report.
- TCP MUST document its legal compulsion posture: what it will contest, on what grounds, and what legal resources it has.
- TCP MUST publish a warrant canary.

### REQ-7.2: Data Minimization
- TCP managed hosting MUST implement all of REQ-1 through REQ-6.
- TCP MUST NOT collect or retain any data beyond what is technically necessary to operate the service.
- Payment processing MUST support anonymous methods (cryptocurrency at minimum). If credit card payment is offered, documentation MUST warn that payment identifiers can be compelled (see: Stop Cop City case).

### REQ-7.3: User Notification
- TCP MUST notify users when legal orders are received for their data, unless prohibited by law.
- TCP MUST document which jurisdictions allow gag orders and the typical duration of such orders.
- TCP SHOULD structure its operations to minimize exposure to gag orders.

### REQ-7.4: Incident Response
- TCP MUST have a documented procedure for responding to legal orders.
- TCP SHOULD retain legal counsel familiar with press freedom law and digital privacy before offering managed hosting.
- TCP SHOULD evaluate membership in organizations like the Reporters Committee for Freedom of the Press or EFF's legal network.

### REQ-7.5: Audit Checklist
- [ ] Verify all REQ-1 through REQ-6 audit checklists pass on managed hosting infrastructure.
- [ ] Verify transparency report publication process.
- [ ] Verify warrant canary is current and has a defined update schedule.
- [ ] Verify user notification procedure is documented and tested.
- [ ] Verify payment processing supports anonymous methods.
- [ ] Verify hosting infrastructure logging (load balancers, CDN, DNS) does not reintroduce IP logging removed at the application level.

---

## REQ-8: Threat Model Documentation

### REQ-8.1: Published Threat Model
- Pyrite MUST publish a threat model document accessible to all users.
- The threat model MUST clearly state, for each deployment tier:
  - What data exists on the server
  - What a court order served on the operator could obtain
  - What encryption protects and what it does not
  - What metadata is and is not available
  - What the operator can and cannot see

### REQ-8.2: Honest Limitations
- The threat model MUST NOT overstate protections. Where Proton's marketing promised "we don't log IPs" while their legal obligations said otherwise, Pyrite's documentation must state plainly what is and isn't protected.
- The threat model MUST distinguish between:
  - Content protection (encryption)
  - Metadata protection (what the server can observe)
  - Traffic analysis protection (what the network can observe)
  - Legal compulsion protection (what a court order can reach)

### REQ-8.3: Audit Checklist
- [ ] Verify published threat model exists and is accurate.
- [ ] Verify threat model matches actual system behavior (not aspirational behavior).
- [ ] Verify threat model is written for journalists, not security engineers -- clear, concrete, actionable.

---

## Audit Procedure

### Phase 1: Static Analysis
1. Run all REQ audit checklists against current codebase.
2. Grep for IP address handling, logging patterns, metadata storage.
3. Review all database schemas / data models for stored fields.
4. Review Dockerfile and container configuration.

### Phase 2: Runtime Analysis
1. Deploy container in test environment.
2. Perform typical operations (create KB, add entries, search, access via MCP).
3. Examine all log files, database contents, and filesystem artifacts.
4. Verify no IP addresses, timestamps, or identity-linking data persists.

### Phase 3: Adversarial Analysis
1. Simulate a "court order" -- what could an operator hand over from a running Tier 3 instance?
2. Document the complete disclosure surface.
3. Compare disclosure surface against published threat model.
4. Identify gaps and remediation priorities.

### Phase 4: Documentation Review
1. Verify threat model document is published and current.
2. Verify deployment documentation includes security guidance for each tier.
3. Verify managed hosting transparency commitments are documented.
