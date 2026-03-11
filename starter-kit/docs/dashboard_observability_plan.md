# Runtime Observability & Explainer Dashboard Plan

## Purpose
Design a **read-only, non-enforcement** dashboard layer that explains runtime behavior by consuming existing evidence artifacts (audit logs, replay artifacts, eval outputs, and launch-gate outputs) without changing policy, retrieval, tool mediation, or launch-gate enforcement paths.

## Repository Observations (Current State)
- Runtime orchestration already emits stage-aligned events for request lifecycle, policy decisions, retrieval decisions, tool decisions, fallback, deny, and errors.
- Audit telemetry is already persisted as JSONL and replay artifacts can already be built from audit events.
- Eval runner already writes scenario-level JSONL, summary JSON, and per-scenario replay artifacts.
- Launch gate already emits structured readiness status/checks (`go`, `conditional_go`, `no_go`) with blockers/residual risks.
- Existing structure cleanly separates enforcement modules from telemetry/evidence modules, which is ideal for an observability layer.

## Recommended Placement (Separate Explainer Layer)

### New Top-Level Module
Add a **new top-level package**:

```text
observability/
```

Rationale:
- Keeps enforcement code paths unchanged in `app/`, `policies/`, `retrieval/`, `tools/`, and `launch_gate/`.
- Aligns with current architecture where telemetry/audit is the source of truth for runtime outcomes.
- Enables strict read-only data flow from artifacts into dashboard views.

## Proposed Folder Structure

```text
observability/
├── __init__.py
├── contracts.py                 # Typed read models for dashboard payloads
├── service.py                   # Read-only aggregation service over artifacts
├── sources/
│   ├── __init__.py
│   ├── audit_log_source.py      # Reads artifacts/logs/audit.jsonl
│   ├── replay_source.py         # Reads artifacts/logs/replay/*.replay.json
│   ├── eval_source.py           # Reads artifacts/logs/evals/*.jsonl + *.summary.json
│   └── launch_gate_source.py    # Reads artifacts/logs/launch_gate/*.json
├── api/
│   ├── __init__.py
│   └── server.py                # Minimal stdlib HTTP JSON API (read-only GET)
└── web/
    ├── index.html               # Static shell
    ├── app.js                   # Vanilla JS rendering (minimal deps)
    └── styles.css
```

Optional docs/tests:

```text
docs/observability_dashboard.md
tests/unit/test_observability_service.py
tests/integration/test_observability_endpoints.py
```

## Backend API Plan (Read-Only)
All endpoints are `GET` only and return materialized views from existing artifacts.

### Health & Metadata
- `GET /api/health`
  - Returns process health and artifact accessibility status.
- `GET /api/meta/sources`
  - Returns discovered artifact locations, newest timestamps, and parse warnings.

### Trace & Runtime Timeline
- `GET /api/traces`
  - Query params: `tenant_id`, `actor_id`, `event_type`, `status`, `limit`, `cursor`.
  - Returns trace list summary (trace_id, request_id, started_at, ended_at, key outcomes).
- `GET /api/traces/{trace_id}`
  - Returns normalized trace object with timeline + stage summaries.
- `GET /api/traces/{trace_id}/timeline`
  - Returns ordered events suitable for timeline chart/table.

### Decision Views
- `GET /api/traces/{trace_id}/policy-decisions`
- `GET /api/traces/{trace_id}/retrieval-decisions`
- `GET /api/traces/{trace_id}/tool-decisions`
- `GET /api/traces/{trace_id}/denies-fallbacks-errors`

### Replay Artifacts
- `GET /api/replay`
  - Lists replay artifacts with coverage flags.
- `GET /api/replay/{trace_id}`
  - Returns parsed replay artifact and linkages to trace summary.

### Eval Outputs
- `GET /api/evals/runs`
  - Lists eval run summaries by timestamp/suite.
- `GET /api/evals/runs/{run_id}`
  - Returns summary + scenario outcome counts.
- `GET /api/evals/runs/{run_id}/scenarios`
  - Returns scenario rows (severity, outcome, runtime realism evidence).

### Launch Gate
- `GET /api/launch-gate/latest`
  - Returns latest readiness report.
- `GET /api/launch-gate/history`
  - Returns recent reports and status trend.

### Safety Constraints for API
- No POST/PUT/PATCH/DELETE.
- No endpoint that invokes policy/retrieval/tool runtime logic.
- No direct pass-through endpoint to tool registry/router.
- Redaction-preserving output only (respect existing redacted artifact fields).

## Frontend Plan (Minimal Dependencies)
Use static HTML + vanilla JS first to minimize dependency footprint.

### Pages
1. `/` Overview
   - Latest launch-gate status card.
   - Recent trace activity.
   - Eval run summary snapshot.
2. `/traces`
   - Filterable trace table.
3. `/traces/:trace_id`
   - Full runtime explainer view:
     - request timeline
     - policy decisions
     - retrieval decisions
     - tool routing decisions
     - deny/fallback/error panel
     - replay coverage panel
4. `/evals`
   - Eval run list + scenario breakdown.
5. `/launch-gate`
   - Readiness status, blockers, residual risks, scorecard categories.

### Core Components
- `TraceTimeline`
- `PolicyDecisionList`
- `RetrievalDecisionCard`
- `ToolRoutingDecisionList`
- `DenyFallbackErrorPanel`
- `ReplayCoverageCard`
- `EvalSummaryTable`
- `LaunchGateStatusPanel`

## Trace Visualization Data Model (Read Model)

```json
{
  "trace_id": "trace-...",
  "request_id": "...",
  "actor": {
    "actor_id": "...",
    "actor_type": "...",
    "tenant_id": "...",
    "session_id": "...",
    "trust_level": "..."
  },
  "lifecycle": {
    "started_at": "...",
    "ended_at": "...",
    "request_lifecycle_complete": true,
    "terminal_status": "ok|blocked|error"
  },
  "timeline": [
    {
      "timestamp": "...",
      "event_type": "policy.decision",
      "stage": "retrieval.search|model.generate|tools.route|...",
      "summary": "human-readable explanation",
      "payload": {}
    }
  ],
  "policy_decisions": [
    {"action": "retrieval.search", "allow": true, "reason": "...", "risk_tier": "...", "constraints": {}}
  ],
  "retrieval_decisions": [
    {"document_count": 3, "top_k": 3, "allowed_source_ids": ["kb-primary"]}
  ],
  "tool_decisions": [
    {"decisions": ["allow", "deny", "require_confirmation"]}
  ],
  "deny_events": [
    {"stage": "tool.route", "tool_name": "...", "reason": "..."}
  ],
  "fallback_events": [
    {"mode": "rag_only", "reason": "..."}
  ],
  "error_events": [
    {"stage": "...", "reason": "..."}
  ],
  "replay": {
    "available": true,
    "coverage": {
      "decision_replay_core_complete": true
    },
    "artifact_path": "artifacts/logs/replay/..."
  },
  "linked_eval_runs": ["security-redteam-..."],
  "linked_launch_gate_reports": ["security-readiness-..."]
}
```

Notes:
- This is a **derived read model** generated from artifacts.
- It should never be used as an input to runtime enforcement decisions.

## Minimal Implementation Phases

### Phase 0 — Artifact Inventory + Contracts
- Implement `observability/contracts.py` with typed DTOs.
- Implement artifact discovery and schema-tolerant parsers.
- Add unit tests for parsing known artifact formats.

### Phase 1 — Read-Only API
- Implement `/api/health`, `/api/traces`, `/api/traces/{trace_id}`, `/api/launch-gate/latest`, `/api/evals/runs`.
- Add integration tests that run only over fixture artifacts.

### Phase 2 — Explainer UI (Static)
- Build overview page and trace-detail explainer view.
- Render required runtime visualizations (timeline, policy/retrieval/tool/deny/fallback/error, replay).

### Phase 3 — Cross-Artifact Correlation
- Link traces to replay artifacts and nearest eval/launch-gate runs by timestamp/request IDs when available.
- Add explicit “evidence source” labels to every UI section.

### Phase 4 — Hardening
- Add pagination and bounded file reads.
- Add optional authn/authz front-door (viewer role) without changing runtime enforcement internals.
- Add clear stale-data and partial-data warnings.

## Risks
- **Schema drift risk**: artifact formats may evolve; parsers must be version-tolerant.
- **Data volume risk**: large JSONL logs can degrade UI/API performance without indexing/pagination.
- **Correlation ambiguity**: not every eval or launch-gate record maps one-to-one with a runtime trace.
- **Sensitive metadata exposure**: dashboard must preserve existing redaction and avoid raw payload dumps.
- **False authority risk**: operators may treat dashboard as source of enforcement; UI must label it as observability-only.

## Non-Goals
- No policy enforcement, policy override, or policy mutation from dashboard.
- No direct tool execution or retrieval invocation from dashboard.
- No write-back into audit/eval/launch-gate artifacts by default.
- No replacement of launch-gate/eval pipelines; dashboard only visualizes their outputs.

## Acceptance Criteria (for first deliverable)
- Dashboard runs without modifying `app/orchestrator.py`, `policies/`, `retrieval/`, `tools/`, or `launch_gate/` enforcement behavior.
- All visualizations are powered by existing artifacts and are read-only.
- Required runtime elements are visible:
  - request timeline
  - policy decisions
  - retrieval decisions
  - tool routing decisions
  - deny/fallback/error events
  - replay artifacts
  - eval summaries
  - launch-gate readiness output
- Tests cover parser success/failure and endpoint read-only behavior.


## Reviewer usability checklist (current implementation)

The current dashboard should allow a reviewer to:
- open Overview and read readiness/evidence/integrity summaries,
- find a trace via filters (tenant/actor/outcome/event/security flags),
- inspect trace timeline and major decisions,
- verify artifact source labels and timestamps,
- inspect eval outcomes and launch-gate blockers/residual risks.

Documentation screenshot placeholders (until generated):
- `docs/images/dashboard-overview.png`
- `docs/images/dashboard-trace-detail.png`
- `docs/images/dashboard-evals.png`
- `docs/images/dashboard-launch-gate.png`

Note: placeholders are documentation-only and do not imply screenshots currently exist.
