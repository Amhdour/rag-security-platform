# Identity / Authorization / Delegation Evidence Model

This document explains what adapter evidence proves vs what it infers.

## Normalized fields

The normalized runtime event schema includes:

- `actor_id`
- `tenant_id`
- `session_id`
- `persona_or_agent_id`
- `tool_invocation_id`
- `delegation_chain`
- `decision_basis`
- `resource_scope`
- `authz_result`
- `identity_authz_field_sources` (per-field provenance marker)

**Implemented:** Field provenance markers use one of:
- `sourced` (directly present in runtime/export input)
- `derived` (adapter inferred from nearby evidence)
- `unavailable` (no reliable value available)

## Proven vs inferred semantics

- **Proven in artifact:** a field value exists and `identity_authz_field_sources[field] == "sourced"`.
- **Inferred/derived:** a field value exists but provenance marker is `derived`.
- **Not proven:** a field value is `unavailable` and provenance marker is `unavailable`.

**Implemented:** The adapter does not invent positive identity claims; missing identity fields remain `unavailable` and are marked `unavailable`.

## Launch-gate minimum quality checks

**Implemented:** Launch-gate evaluates:
1. `identity_authz_evidence_presence`
2. `identity_authz_provenance_quality`

`identity_authz_provenance_quality` enforces minimum quality by evaluating:
- missing/invalid provenance markers,
- critical field provenance availability (`actor_id`, `tenant_id`, `session_id`, `decision_basis`, `resource_scope`, `authz_result`),
- amount of derived-only critical evidence.

Outcomes:
- **PASS:** critical provenance available and coverage is acceptable.
- **WARN:** some critical fields are derived/unavailable, but not fail-threshold.
- **FAIL:** critical provenance largely unavailable.

## Honesty boundary

- **Implemented:** Artifact evidence quality can support governance review.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.
- **Unconfirmed:** artifact evidence alone does not prove production runtime enforcement.
