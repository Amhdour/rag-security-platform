# Onyx -> Starter-Kit Mapping

This document defines the additive mapping contract used by `integration-adapter/`.

## Goals

- Keep Onyx as runtime execution plane.
- Keep starter kit as governance/evidence/launch-gate plane.
- Use artifact generation as the only integration boundary.

## Domain mapping

| Onyx concept | Adapter translator | Starter-kit artifact target |
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

The adapter emits event types aligned with starter-kit audit contracts:

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
