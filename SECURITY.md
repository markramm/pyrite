# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in Pyrite, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email the maintainers directly or use GitHub's private vulnerability reporting feature:

1. Go to the [Security tab](https://github.com/markramm/pyrite/security) of this repository
2. Click "Report a vulnerability"
3. Provide a detailed description of the vulnerability

We will acknowledge receipt within 48 hours and aim to provide a fix within 7 days for critical issues.

## Scope

This policy applies to the `pyrite` Python package and its server components (REST API, MCP server).

## Best Practices for Users

- Never commit your `.env` file or API keys to version control
- Use read-only KB configurations for untrusted data sources
- Run the REST API behind a reverse proxy in production
- Keep dependencies up to date
