# Trace Normalization Layer

`observability/trace_normalization.py` reconstructs end-to-end request traces from audit and replay artifacts for dashboard consumption.

## Inputs

- Audit events from `artifacts/logs/audit.jsonl` (or equivalent artifact root).
- Replay links from `artifacts/logs/replay/*.replay.json`.

## Normalized trace output

Each trace explanation includes:

- `trace_id` and `request_id`
- `actor_id` and `tenant_id`
- ordered `timeline`
- `event_category` and `stage`
- `decision_outcome`
- `reason`
- `final_disposition` / `final_outcome`
- linked replay artifact metadata when available

## Stage classification

Events are classified into:

- `lifecycle`
- `policy`
- `retrieval`
- `model`
- `tools`
- `deny`
- `fallback`
- `error`

Classification uses runtime event names defined in telemetry contracts (`request.start`, `policy.decision`, `retrieval.decision`, `tool.decision`, `deny.event`, `fallback.event`, `error.event`, etc.).

## Safety and failure behavior

- Missing audit file returns empty results.
- Malformed audit lines are skipped and counted.
- Incomplete traces are marked with `partial_trace=true` and `final_disposition=in_progress` when no terminal signal exists.
- Payload redaction is preserved via `redact_mapping` before normalized timeline emission.

## Non-goals

- No runtime enforcement changes.
- No mutation of policy, retrieval, tools, eval, telemetry, or launch-gate behavior.
- No frontend-coupled rendering logic.
