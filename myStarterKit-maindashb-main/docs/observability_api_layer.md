# Observability API Layer (Read-Only)

This repository exposes a minimal dashboard backend via `observability/api.py` and `observability/service.py`.

## Endpoints

- `GET /api/overview`
- `GET /api/traces`
- `GET /api/traces/{id}`
- `GET /api/replay`
- `GET /api/replay/{id}`
- `GET /api/evals`
- `GET /api/evals/{id}`
- `GET /api/verification/latest`
- `GET /api/launch-gate/latest`
- `GET /api/system-map`

Mutating methods (`POST`, `PUT`, `PATCH`, `DELETE`) return `405`.

## Behavior notes

- `/api/overview` returns summary artifact counts and latest launch-gate/verification status.
- `/api/traces` returns normalized trace summaries and supports filters (`trace_id`, `request_id`, `actor_id`, `tenant_id`, `event_type`).
- `/api/traces/{id}` returns a full normalized timeline.
- All data is read from artifacts; no runtime tool/policy/retrieval execution occurs.
- Redaction from trace normalization is preserved in API outputs.

## Safety

- Read-only API surface.
- No policy mutation endpoints.
- No direct tool execution paths.
- Malformed artifacts are handled defensively and skipped where applicable.
