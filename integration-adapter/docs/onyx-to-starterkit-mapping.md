# Onyx -> Secure Starter Kit Mapping

This document defines the additive mapping contract used by `integration-adapter/`.

## Goals

- Keep Onyx as runtime execution plane.
- Keep Secure Starter Kit as governance/evidence/Launch Gate plane.
- Use artifact generation as the only integration boundary.

## Domain mapping

| Onyx concept | Adapter translator | Secure Starter Kit artifact target |
|---|---|---|
| Connectors / indexed sources | `translate_connectors` | `artifacts/logs/connectors.inventory.json` |
| Retrieval decisions | `translate_retrieval_events` | `artifacts/logs/audit.jsonl` (`retrieval.decision`) |
| Tool inventory | `translate_tool_inventory` | `artifacts/logs/tools.inventory.json` |
| Tool decisions | `translate_tool_decisions` | `artifacts/logs/audit.jsonl` (`tool.decision`, `confirmation.required`) |
| MCP server inventory | `translate_mcp_inventory` | `artifacts/logs/mcp_servers.inventory.json` |
| MCP usage | `translate_mcp_usage` | `artifacts/logs/audit.jsonl` (`tool.execution_attempt`) |
| Eval outputs | `translate_eval_outputs` | `artifacts/logs/evals/*.jsonl` |
| Eval run metadata | `translate_eval_inventory` | `artifacts/logs/evals.inventory.json` |
| Request lifecycle/security events | `translate_request_lifecycle_events` | `artifacts/logs/audit.jsonl` |

## Normalized event vocabulary

The adapter emits event types aligned with Secure Starter Kit audit contracts:

- `request.start`
- `policy.decision`
- `retrieval.decision`
- `tool.decision`
- `tool.execution_attempt`
- `confirmation.required`
- `deny.event`
- `fallback.event`
- `request.end`

## Source model notes

The adapter uses internal source models in `schemas.py` as lightweight facades over Onyx payloads:

- `OnyxRetrievalRecord`
- `OnyxToolDecisionRecord`
- `OnyxMCPUsageRecord`
- `OnyxEvalResultRecord`

These models intentionally avoid direct imports from Onyx internals.

## TODOs requiring runtime-hook confirmation

The following fields require confirmation from concrete Onyx runtime paths before production wiring:

1. Connector index status field names per tenant.
2. Tool inventory source of truth for builtin/custom + enablement visibility.
3. MCP usage feed and decision status semantics.
4. Eval output shape compatibility across local and remote eval providers.
5. Canonical lifecycle event stream source for request/policy/deny/fallback events.


## Normalized identity/authz mapping layer

For `audit.jsonl` events, the adapter records normalized identity/authz evidence:

- `actor_id`, `tenant_id`, `session_id`
- `persona_or_agent_id`
- `tool_invocation_id`
- `delegation_chain`
- `decision_basis`
- `resource_scope`
- `authz_result`
- `identity_authz_field_sources`

`identity_authz_field_sources` marks each field as:
- `sourced`: directly read from runtime payload/hook
- `derived`: inferred deterministically by adapter
- `unavailable`: no trustworthy source found in this workspace

### Onyx field mapping (best-effort)

The adapter maps normalized identity/authz fields from runtime keys where available:

- `session_id` <= `session_id` or Onyx-style `chat_session_id` (else derived from `trace_id`)
- `persona_or_agent_id` <= `persona_or_agent_id` or `persona_id` or `agent_id`
- `tool_invocation_id` <= `tool_invocation_id` or Onyx-style `tool_call_id`
- `delegation_chain` <= `delegation_chain` list (or derived from `delegated_by`)
- `decision_basis` <= `decision_basis` or `reason`
- `resource_scope` <= `resource_scope` or runtime payload `source_id` / `tool_name` / `mcp_server`
- `authz_result` <= `authz_result` or `decision` (or derived from boolean `allowed`)

Unconfirmed: canonical runtime hook not validated in this workspace for all deployment modes.

### Proven vs inferred

- **Implemented/Proven in artifact output:** normalized fields and source markers are emitted in `audit.jsonl`.
- **Partially Implemented:** some fields are derived from adjacent runtime fields where direct hooks are unavailable.
- **Unconfirmed:** canonical production identity/delegation hook locations and semantics remain deployment-dependent.
