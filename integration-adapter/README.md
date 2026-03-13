# Integration Adapter

**Implemented:** Additive adapter translating Onyx runtime concepts into starter-kit-compatible governance artifacts.

## Scope

- **Implemented:** No Onyx core rewrites.
- **Implemented:** No direct starter-kit policy/dashboard mutation paths.
- **Implemented:** Artifact files are the integration boundary.

## Implementation status (claims audit)

### Implemented
- Artifact pipeline commands:
  - `collect_from_onyx`
  - `generate_artifacts`
  - `run_launch_gate`
  - `demo_scenario`
- **Implemented:** Schema validation for normalized events.
- **Implemented:** Artifact writing for audit/replay/eval/launch-gate.
- **Implemented:** Evidence-based launch-gate evaluator with fail-closed behavior on malformed/missing evidence.

### Partially Implemented
- **Partially Implemented:** Exporters support file-backed extraction and optional direct Onyx DB extraction where runtime imports/session are available.

### Demo-only
- **Demo-only:** Demo scenario can synthesize schema-valid runtime events/inventory/evals when live data is unavailable.

### Unconfirmed
- **Unconfirmed:** Canonical production runtime hook locations for all deployment modes (especially event feed semantics and multi-provider eval shape).

### Planned
- **Planned:** Environment-specific live-hook validation and commit-pinned runtime compatibility matrix updates.


## Exporter runtime-hook status

- **Connector inventory exporter**: **Partially Implemented** (real Onyx DB read via `onyx.db.connector.fetch_connectors` when runtime is available; file-backed fallback).
- **Tool inventory exporter**: **Partially Implemented** (real Onyx DB read via `onyx.db.tools.get_tools` when runtime is available; file-backed fallback).
- **MCP inventory exporter**: **Partially Implemented** (real Onyx DB read via `onyx.db.mcp.get_all_mcp_servers` with ToolCall-derived usage counts when runtime is available; file-backed fallback).
- **Eval results exporter**: **Unconfirmed** runtime hook in this workspace (currently file-backed snapshot extraction only).
- **Runtime events exporter**: **Partially Implemented** (prefers audit JSONL, with ToolCall-derived `tool.execution_attempt` fallback from Onyx DB when runtime is available).

> Unconfirmed: canonical runtime hook not validated in this workspace for deployment-wide parity.


## Normalized identity and authorization evidence

Normalized audit events now include identity/authorization evidence fields:
- `actor_id`
- `tenant_id`
- `session_id`
- `persona_or_agent_id`
- `tool_invocation_id`
- `delegation_chain`
- `decision_basis`
- `resource_scope`
- `authz_result`
- `identity_authz_field_sources` (per-field: `sourced`, `derived`, or `unavailable`)

Proven vs inferred guidance:
- **Proven in artifacts:** a field value exists in the normalized artifact and indicates whether it was sourced/derived/unavailable.
- **Inferred/Derived:** adapter inferred value from adjacent payload semantics (e.g., `resource_scope` from `source_id` or `tool_name`).
- **Unconfirmed:** canonical runtime hook parity across deployment modes is not established by this workspace alone.

## Included modules

- `integration_adapter/config.py` — adapter configuration / artifact root handling.
- `integration_adapter/schemas.py` — normalized event and launch-gate schema models.
- `integration_adapter/artifact_output.py` — writes audit, replay, eval, and launch-gate artifacts.
- `integration_adapter/mappers.py` — runtime payload -> normalized schema mapping.
- `integration_adapter/translators.py` — domain translators.
- `integration_adapter/exporters.py` — read-only exporters from Onyx-facing sources.
- `integration_adapter/raw_sources.py` — JSON/JSONL source readers and path discovery.
- `integration_adapter/pipeline.py` — collection + artifact generation + launch-gate orchestration.
- `integration_adapter/collect_from_onyx.py` — CLI entrypoint.
- `integration_adapter/generate_artifacts.py` — CLI entrypoint.
- `integration_adapter/run_launch_gate.py` — CLI entrypoint.
- `integration_adapter/demo_scenario.py` — end-to-end demo runner.

## Mapping contract

- `docs/onyx-to-starterkit-mapping.md`

## Output layout

Generated artifacts are written under:
- `artifacts/logs/audit.jsonl`
- `artifacts/logs/replay/*.replay.json`
- `artifacts/logs/evals/*.jsonl`
- `artifacts/logs/evals/*.summary.json`
- `artifacts/logs/launch_gate/*.json`
- `artifacts/logs/launch_gate/*.md`

## Quick start

```bash
cd integration-adapter
python -m pytest -q
```

## Runnable evidence pipeline

Preferred step-by-step commands:

```bash
cd integration-adapter
python -m integration_adapter.collect_from_onyx
python -m integration_adapter.generate_artifacts
python -m integration_adapter.run_launch_gate
```

One-command pipeline from repo root:

```bash
make evidence
```

Alternative one-command pipeline from adapter directory:

```bash
cd integration-adapter
python -m integration_adapter.evidence_pipeline
```

Force demo mode:

```bash
make evidence-demo
```

Or:

```bash
cd integration-adapter
python -m integration_adapter.evidence_pipeline --demo
```

Environment overrides:
- `INTEGRATION_ADAPTER_ARTIFACTS_ROOT`
- `INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON`
- `INTEGRATION_ADAPTER_ONYX_TOOLS_JSON`
- `INTEGRATION_ADAPTER_ONYX_MCP_JSON`
- `INTEGRATION_ADAPTER_ONYX_EVALS_JSON`
- `INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL`

## Launch-gate criteria (evidence-based)

`python -m integration_adapter.run_launch_gate` checks:
1. connector inventory presence
2. tool inventory classification quality
3. MCP inventory classification quality
4. required audit lifecycle events
5. eval evidence presence
6. artifact completeness
7. critical/high eval failures
8. artifact schema validity (fail-closed on malformed evidence)

Status semantics:
- `go`: all checks pass
- `conditional_go`: no fails and one or more warnings
- `no_go`: one or more failures

Limitations:
- Evaluates evidence presence/quality only.
- Does **not** independently prove production runtime enforcement.

## End-to-end demo scenario

```bash
cd integration-adapter
python -m integration_adapter.demo_scenario
```

Or from repo root:

```bash
make demo
```

The demo report at `artifacts/logs/demo_scenario.report.json` explicitly labels per-domain and per-story-step `real` vs `synthetic` sources and includes `remaining_realism_gaps` with UNCONFIRMED runtime-hook caveats.

See `../docs/demo-scenario.md` for full steps, expected outputs, and realism gaps.

## Testing notes

- Adapter tests include unit and integration-style coverage.
- Untestable runtime assumptions are documented in `../docs/testing-blind-spots.md`.
