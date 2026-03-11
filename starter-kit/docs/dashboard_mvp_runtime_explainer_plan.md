# Smallest High-Value Runtime Explainer Dashboard (MVP Plan)

## Verified Repository Grounding

### Module boundaries (already implemented)
The repository already enforces the target module split:
- `app/`
- `policies/`
- `retrieval/`
- `tools/`
- `telemetry/audit/`
- `evals/`
- `launch_gate/`

This is documented as implemented architecture and reflected in the system map exposed by the observability layer.

### Runtime flow (already implemented)
The runtime flow is already represented in code and docs as:
1. request normalization + trace context
2. policy checks across retrieval/model/tool routing
3. retrieval boundary enforcement (tenant/source/metadata)
4. tool mediation (allow/deny/confirmation/rate-limit)
5. telemetry audit + replay artifacts
6. eval + launch-gate readiness outputs

### Baseline artifacts to consume
The dashboard should consume existing artifacts and not add enforcement-path dependencies:
- `artifacts/logs/audit.jsonl`
- `artifacts/logs/replay/*.replay.json`
- `artifacts/logs/evals/*.jsonl`
- `artifacts/logs/evals/*.summary.json`
- `artifacts/logs/verification/*.summary.json|md`
- `artifacts/logs/launch_gate/*.json`

## Best Place to Add Dashboard as a Separate Layer

Use and extend the existing top-level **`observability/`** package as the dashboard layer.

Why this is best:
- It is already physically separate from enforcement modules.
- It already provides a read-only API (`GET` endpoints, write methods blocked).
- It already resolves artifact paths and builds trace/replay/eval/launch-gate read models.

This keeps `app/`, `policies/`, `retrieval/`, `tools/`, `telemetry/audit/`, and `launch_gate/` enforcement logic unchanged.

## Architecture Plan (Smallest MVP)

### 1) Data plane (read-only)
- Source of truth: filesystem artifacts under `artifacts/logs` (or demo root override).
- No calls into policy engine, retriever, tool router, or orchestrator runtime execution.
- Parse and normalize into dashboard DTOs only.

### 2) API plane (read-only)
Keep API limited to `GET` endpoints and explicit `405` for mutation methods.

MVP endpoints:
- `GET /api/traces`
- `GET /api/traces/{trace_id}`
- `GET /api/replay`
- `GET /api/replay/{replay_id}`
- `GET /api/evals`
- `GET /api/evals/{run_id}`
- `GET /api/launch-gate/latest`
- `GET /api/system-map`

### 3) UI plane (single-page, minimal JS)
Focus on one high-value dashboard page with tabs/sections:
- Request timeline
- Policy decisions
- Retrieval decisions
- Tool decisions
- Deny/fallback/error events
- Replay artifacts
- Eval summaries
- Launch-gate readiness status

## Folder Structure (MVP)

Keep existing structure and add only thin view-model helpers where needed:

```text
observability/
├── api.py
├── artifact_paths.py
├── contracts.py
├── service.py
├── trace_normalization.py
├── eval_normalization.py
├── launch_gate_normalization.py
└── web/
    ├── index.html
    └── static/
        ├── app.js
        └── styles.css
```

Optional additions (only if needed by UI complexity):
- `observability/view_models.py`
- `tests/unit/test_observability_view_models.py`

## API/Backend Plan

1. **Keep strict read-only behavior**
   - Continue denying POST/PUT/PATCH/DELETE.
2. **Artifact-first aggregation**
   - Audit log reader builds trace timeline and stage summaries.
   - Replay reader adds replay coverage and event-count metadata.
   - Eval readers expose run list + per-run outcomes.
   - Launch-gate reader exposes latest readiness and blockers/residual risks.
3. **Correlation strategy**
   - Primary key: `trace_id`; fallback key: `request_id`.
   - If mapping is ambiguous, show source-path metadata instead of guessing.
4. **Performance/safety bounds**
   - Add default limits/pagination to trace/eval listing.
   - Return parse warnings; fail-soft on malformed lines.

## Frontend Page Plan (Single Dashboard)

### Header
- Environment/artifact root indicator (real vs demo)
- Read-only badge + “not enforcement path” disclaimer

### Section A: Runtime Trace Explorer
- Trace table with filters (`trace_id`, `request_id`, `actor_id`, `tenant_id`, `event_type`)
- Detail pane timeline in event order

### Section B: Decision Explainer
- Policy decision list (action, allow, reason, risk tier)
- Retrieval decision card (doc count, top_k, allowed sources)
- Tool decision card (allow/deny/confirmation outcomes)
- Deny/fallback/error feed

### Section C: Evidence Correlation
- Replay artifact metadata + coverage flags
- Eval run summary tiles (pass/fail/blocked/etc.)
- Latest launch-gate status (`go`/`conditional_go`/`no_go`) with blockers/residual risks

## Implementation Phases

### Phase 1 (1–2 days): MVP Explainability
- Confirm artifact parsing contracts.
- Ensure all required sections render from existing APIs.
- Add clear empty-state messaging when artifacts are missing.

### Phase 2 (1 day): Correlation & UX polish
- Link selected trace to replay + nearest eval run (when identifiers match).
- Add copyable evidence paths.

### Phase 3 (1 day): Robustness
- Pagination/limits.
- Schema-drift tolerant parsing with warnings.
- Unit tests for malformed artifact handling.

## Risks
- Schema drift in artifact formats may break strict parsers.
- Sparse artifacts can create “empty dashboard” confusion.
- Correlation between trace/eval/launch-gate is not always one-to-one.
- Large JSONL files can impact response times without pagination.

## Non-Goals
- No policy editing, no policy override, no runtime mutation.
- No direct tool execution/retrieval/model invocation.
- No write-back of telemetry/eval/launch-gate artifacts.
- No replacement of launch-gate or eval harness; dashboard remains observability-only.
