# AGENTS.md — Starter Kit (workspace integration)

Scope: `myStarterKit-maindashb-main/`

## Mission
Maintain governance/evidence behavior with a **read-only dashboard** in this integration workspace.

## Must-follow rules
1. Keep observability and dashboard APIs read-only (no mutating endpoints).
2. Preserve localhost-safe defaults unless explicitly requested otherwise.
3. Do not claim runtime enforcement guarantees not implemented and test-backed.
4. Use explicit claim labels where relevant: **Implemented / Partially Implemented / Demo-only / Unconfirmed / Planned**.

## Integration expectations
- Treat adapter artifacts as evidence inputs; do not add runtime-control side effects.
- If artifact shape/path assumptions are uncertain, mark them **Unconfirmed** and document next verification step.
- Handle missing/malformed artifacts defensively (safe empty state, no crashes).

## Test-before-claim
- Run targeted Starter Kit tests for touched observability/dashboard behavior.
- Broaden test scope when changing artifact compatibility paths.

## Docs sync
When behavior changes, update:
- `myStarterKit-maindashb-main/README.md`
- `myStarterKit-maindashb-main/docs/observability_artifact_readers.md`
- Any workspace-level docs that describe dashboard compatibility/status.
