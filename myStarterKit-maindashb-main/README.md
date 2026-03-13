# Secure Support Agent Starter Kit

A production-oriented repository scaffold for building a **secure support agent** with retrieval-augmented generation (RAG), policy enforcement, telemetry/audit trails, evaluations, and launch gating.

> Phase 10 adds a hardening and cleanup pass focused on safer defaults, tighter fail-safe behavior, and clearer deployment/demo readiness guidance.


## Review this repo in 5 minutes

Use this path to validate credibility quickly (no marketing steps):

1. **Core claims + traceability map**
   - `docs/security_guarantees.md`
   - `verification/security_guarantees_manifest.json`
2. **Regenerate machine evidence from clean state**
   ```bash
   ./scripts/regenerate_core_evidence.sh
   ```
3. **Inspect guarantees verification output**
   - `artifacts/logs/verification/security_guarantees.summary.json`
4. **Inspect launch-readiness decision and blockers/residual risks**
   - `artifacts/logs/launch_gate/security-readiness-<STAMP>.json`
5. **Review honest residual risk list**
   - `docs/evidence_pack/residual_risks.md`

If release-relevant guarantees are missing/failing, launch-gate should not report `go`.


## Security Guarantees

- See `docs/security_guarantees.md` for implementation-aligned security invariants, enforcement points, evidence mappings, and residual risks.
- See `docs/trust_boundaries.md` for boundary-by-boundary crossings, risks, controls, and required audit events.

## Purpose

This starter kit provides a clean foundation to:
- Build support-focused agent workflows incrementally.
- Separate concerns across app, retrieval, tools, policies, telemetry, evals, and launch controls.
- Enable safe iteration with clear extension points and test scaffolding.

## Current Scope

Included:
- Modular repository layout.
- Structured request/response/context models.
- Policy-aware orchestration flow with explicit stage boundaries.
- Secure retrieval service with source registration and tenant/source enforcement.
- IAM integration mapping examples for OIDC/JWT, services, operators, and delegated workloads (`docs/iam_integration.md`).
- Trust/provenance metadata requirements for citation-friendly retrieval results.
- Secure tool router with explicit allow/deny/require_confirmation decisions and mediated execution path.
- Policy-as-code runtime engine with validation, risk tiers, environment overrides, kill switch, and fallback-to-RAG handling.
- Structured telemetry and audit pipeline with JSONL output and replay artifact generation.
- Reusable security eval runner with scenario-based red-team cases and regression outputs.
- Launch-gate readiness evaluator with machine-checkable checks, blockers, and residual-risk summaries.
- Evidence-pack and reviewer/operator/portfolio documentation for practical review workflows.
- Hardening pass across policy/retrieval/tool/launch-gate fail-safe behavior and stricter tests.
- Environment/config templates.
- Engineering and safety guidance in `AGENTS.md`.
- Baseline and orchestration-focused tests.

Not included:
- Business/domain logic.
- Live integrations (LLM providers, vector stores, ticketing systems, etc.).
- Security claims beyond what is actually implemented.

## Repository Layout

```text
.
├── app/                  # Agent models, context, orchestration, model contracts
├── retrieval/            # Retrieval abstractions, indexing/query contracts
├── tools/                # Tool registry and mediated routing contracts
├── policies/             # Policy specs and enforcement integration points
├── telemetry/
│   └── audit/            # Audit event schemas and telemetry pipeline hooks
├── evals/                # Evaluation harness and datasets placeholders
├── launch_gate/          # Pre-launch readiness checks and release gate scaffolding
├── docs/                 # Architecture, roadmap, and operating docs
├── tests/                # Unit/integration/e2e structure and fixtures
├── artifacts/
│   └── logs/             # Runtime and CI artifact output location
├── config/               # Config templates and environment-specific overlays
└── scripts/              # Utility scripts for setup/validation (safe, non-prod)
```

## Core Flow (Phase 10)

1. Request enters with `SupportAgentRequest` and `SessionContext`.
2. Orchestrator builds `RequestContext`.
3. Policy gate checks retrieval stage.
4. Retrieval returns supporting documents.
5. Policy gate checks model generation stage.
6. Model receives user input plus retrieved context (RAG-first prompt envelope).
7. Policy gate checks tool-routing stage.
8. Tool router returns **decisions only** (never direct execution).
9. Response returns structured output + trace for auditability.

## Quick Start (Reviewer, ~10 minutes)

1. **Setup**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```
2. **Minimal config**
   ```bash
   cp config/settings.template.yaml config/settings.local.yaml
   cp config/logging.template.yaml config/logging.local.yaml
   mkdir -p artifacts/logs/evals artifacts/logs/replay
   ```
3. **Startup/validation commands**
   ```bash
   pytest -q
   python -m evals.runner
   python -m launch_gate.engine
   ```
4. **Inspect generated evidence**
   - Eval scenario logs: `artifacts/logs/evals/*.jsonl`
   - Eval summaries: `artifacts/logs/evals/*.summary.json`
   - Replay artifacts: `artifacts/logs/replay/*.replay.json`
   - Audit logs (if JSONL sink is wired in your runtime entrypoint): `artifacts/logs/audit.jsonl`

### Demo walkthrough

> Uses repository runtime fixture wiring (`evals/runtime.py`) so reviewers can exercise real orchestrator/policy/retrieval/tool paths quickly.

#### A) Normal request (orchestrator path)
```bash
python -c "from evals.runtime import build_runtime_fixture, make_request; f=build_runtime_fixture(); r=f.orchestrator.run(make_request(request_id='demo-ok', tenant_id='tenant-a', user_text='How do I reset my password?')); print('status:', r.status); print('retrieved_docs:', list(r.trace.retrieved_document_ids)); print('events:', [e.event_type for e in f.audit_sink.events])"
```

#### B) Guarded action (denied tool invocation)
```bash
python -c "from evals.runtime import build_runtime_fixture, make_invocation; f=build_runtime_fixture(); d=f.tool_router.route(make_invocation(request_id='demo-deny', tenant_id='tenant-a', tool_name='admin_shell', action='exec', arguments={'command':'whoami'})); print('tool_decision:', d.status); print('reason:', d.reason)"
```

#### C) Launch-gate output example
```bash
python -c "from pathlib import Path; from launch_gate.engine import SecurityLaunchGate; report=SecurityLaunchGate(repo_root=Path('.')).evaluate(); print('status:', report.status); print('summary:', report.summary); [print(f'- {c.check_name}:', 'PASS' if c.passed else 'FAIL') for c in report.checks]"
```

## Development Principles

- Keep all execution paths policy-aware and auditable.
- Prefer explicit contracts between modules.
- Add implementation only with tests and documented threat considerations.
- Never claim security properties that are not verifiably implemented.

## Dashboard at a glance

Use the dashboard as a **read-only evidence viewer** for reviewer workflows.

1. Start API locally:
   ```bash
   python -m observability.api
   ```
2. Open `http://127.0.0.1:8080/`.
3. Follow this reviewer path:
   - **Overview**: check readiness + connected evidence + artifact integrity status.
   - **Trace Explorer**: filter to a trace of interest (tenant/actor/outcome/security flags).
   - **Trace Detail**: inspect timeline, policy/retrieval/tool decisions, and linked artifacts.
   - **Evidence Sources**: confirm each panel’s artifact path and timestamp.
   - **Evals**: inspect scenario outcomes and high/critical failures.
   - **Launch Gate**: inspect status, blockers, residual risks, and passed checks.

Screenshot placeholders (replace with real captures when available):
- `docs/images/dashboard-overview.png` (Overview)
- `docs/images/dashboard-trace-detail.png` (Trace Detail)
- `docs/images/dashboard-launch-gate.png` (Launch Gate)

## Read-only Dashboard API (Observability)

A minimal dashboard backend is available under `observability/` and is intentionally **read-only**.
It reads existing artifacts (`artifacts/logs/audit.jsonl`, `artifacts/logs/replay/*.replay.json`,
`artifacts/logs/evals/*.summary.json`, `artifacts/logs/evals/*.jsonl`, and
`artifacts/logs/launch_gate/*.json`) and does not participate in enforcement decisions.

Run locally:

```bash
python -m observability.api
```

Then open `http://127.0.0.1:8080/` for the web dashboard UI (served as static files by the same process).

Endpoints:
- `GET /api/traces` (filters: `request_id`, `trace_id`, `tenant_id`, `actor_id`, `event_type`)
- `GET /api/traces/{trace_id}`
- `GET /api/replay`
- `GET /api/replay/{id}`
- `GET /api/evals`
- `GET /api/evals/{id}`
- `GET /api/launch-gate/latest`
- `GET /api/system-map`

All mutating methods return `405 method_not_allowed`.

Artifact root is configurable via `DASHBOARD_ARTIFACTS_ROOT`; if unset, the API accepts `INTEGRATION_ADAPTER_ARTIFACTS_ROOT`, then `INTEGRATION_ARTIFACTS_ROOT` as fallbacks for integration deployments.
When none of those are set, the dashboard defaults to `artifacts/logs`; in the integration workspace it also auto-detects sibling `../integration-adapter/artifacts/logs` when local artifacts are absent.

Recommended integration workflow (from repository root):

```bash
make evidence-demo
cd myStarterKit-maindashb-main
DASHBOARD_ARTIFACTS_ROOT=../integration-adapter/artifacts/logs python -m observability.api
```

This keeps dashboard behavior read-only while validating compatibility with generated adapter artifacts.


#### Dashboard security defaults and deployment posture

- **Localhost-only by default**: dashboard binds to `127.0.0.1` unless remote binding is explicitly enabled.
- **Remote binding requires explicit opt-in**: set `DASHBOARD_ALLOW_REMOTE=true` and `DASHBOARD_HOST=<bind-address>`.
- **Read-only guarantee**: only GET endpoints are implemented; POST/PUT/PATCH/DELETE return `405 method_not_allowed`.
- **No tool execution / no policy mutation guarantee**: dashboard code path only reads artifacts and static files; it does not invoke orchestrator tools or mutate policy bundles.
- **Secret and argument safety**: payloads shown in trace/replay views are redacted via `app/secrets.py` helpers; raw sensitive values are not intended to be emitted by dashboard readers.
- **Reverse-proxy expectation for shared environments**: if exposed beyond localhost, place behind authenticated TLS-terminating reverse proxy and restrict origin/IP access.
- **Authentication expectation**: built-in API has no authn/authz layer; do not expose publicly without external authentication controls.
- **Demo separation**: demo mode must use `DASHBOARD_ARTIFACTS_ROOT=artifacts/demo/dashboard_logs`; runtime and demo artifacts should not be mixed.

Example remote review (explicit, not default):

```bash
DASHBOARD_ALLOW_REMOTE=true DASHBOARD_HOST=0.0.0.0 python -m observability.api
```


### Local demo mode (learning only)

When runtime artifacts are sparse, you can generate clearly-labeled demo artifacts that follow the repository schemas:

```bash
python scripts/generate_dashboard_demo_artifacts.py
DASHBOARD_ARTIFACTS_ROOT=artifacts/demo/dashboard_logs python -m observability.api
```

In demo mode, the dashboard is explicitly labeled and reads from `artifacts/demo/dashboard_logs` instead of production-like logs.

For integration-adapter generated demo artifacts:

```bash
cd ../integration-adapter
python -m integration_adapter.demo_scenario
cd ../myStarterKit-maindashb-main
DASHBOARD_ARTIFACTS_ROOT=../integration-adapter/artifacts/logs python -m observability.api
```

## Phase 10 Hardening Notes

- Retrieval and tool-routing now fail closed when policy evaluation errors occur.
- Tool decision outputs keep argument shape while redacting argument values to reduce leakage risk.
- Launch-gate evaluation now treats unreadable required evidence files as explicit blockers.


## Documentation & Evidence Pack

- Architecture deep-dive: `docs/architecture.md`
- Architecture diagrams: `docs/architecture_diagrams.md`
- Deployment architecture: `docs/deployment_architecture.md`
- Trust boundaries (boundary-by-boundary crossings, controls, and required logging): `docs/trust_boundaries.md`
- Threat model: `docs/threat_model.md`
- Operator/developer setup: `docs/operator/setup.md`
- Security reviewer guide: `docs/reviewer/security_review_guide.md`
- Reviewer trust pack (quick credibility walkthrough): `docs/reviewer_guide.md`
- Portfolio summary: `docs/portfolio/project_summary.md`
- Evidence pack index: `docs/evidence_pack/README.md`

- Secrets handling guide: `docs/security_secrets.md`

- External integration boundary hardening: `docs/integration_boundary_security.md`.

- Incident response playbooks: `docs/incident_response_playbooks.md`.
- Incident readiness evidence summary: `docs/evidence_pack/incident_readiness_summary.md`.
- Security drift detection guide: `docs/drift_detection.md`.
- Retrofit review mode guide: `docs/retrofit_mode.md`.
- Retrofit assessment templates: `docs/templates/retrofit_system_profile.template.json`, `docs/templates/retrofit_control_mapping.template.json`.
