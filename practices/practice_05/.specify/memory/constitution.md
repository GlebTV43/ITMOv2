# Subscription Registry Constitution

## Core Principles

### I. Preserve the existing library
Production MUST reuse practice_04 Registry through its public API. Previous lab files and tests MUST remain unchanged.

### II. Small local interface
Runtime and tests MUST use Python stdlib only. Bind to 127.0.0.1, one in-memory Registry per server, ordinary HTML forms. No database, auth or deployment.

### III. Specification before implementation
UI and logic MUST share a user-approved contract before production code. Behavioral changes require user agreement. Contract tests MUST fail before implementation.

### IV. Verify public behavior
Tests MUST use real HTTP and public Registry behavior. Original regression tests MUST pass. No skips or weakened tests. Verify forms and an error in a browser.

### V. Honest evidence
Reports MUST distinguish executed checks from plans. User text MUST be HTML-escaped. Rejected inputs MUST NOT mutate Registry.

## Additional Constraints
New source, tests and evidence belong to practice_05. Existing labs are read-only dependencies. Secrets and environment directories MUST NOT be committed.

## Development Workflow
Specify -> two-team reconciliation -> user approval -> plan -> tasks -> test-first implementation -> HTTP and browser verification -> convergence -> human acceptance. Commit and push are separate user-directed steps.

## Governance
Initial constitution derived from the user-approved contract. Explain amendments and seek user agreement for scope or behavior changes. Semantic versioning: breaking principles major, additions minor, clarifications patch. Review compliance before delivery.

**Version**: 1.0.0 | **Ratified**: 2026-10-30 | **Last Amended**: 2026-10-30
