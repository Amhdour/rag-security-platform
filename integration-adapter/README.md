# Integration Adapter

Additive adapter translating Onyx runtime concepts into starter-kit-compatible governance artifacts.

## Scope

- No Onyx core rewrites.
- No direct starter-kit policy/dashboard mutation paths.
- Artifact files are the integration boundary.

## Implementation status (claims audit)

### Implemented
- Artifact pipeline commands:
  - `collect_from_onyx`
  - `generate_artifacts`
  - `run_launch_gate`
  - `demo_scenario`
- Schema validation for normalized events.
- Artifact writing for audit/replay/eval/launch-gate.
- Evidence-based launch-gate evaluator with fail-closed behavior on malformed/missing evidence.

### Partially Implemented
- Exporters support file-backed extraction and optional direct Onyx DB extraction where runtime imports/session are available.

### Demo-only
- Demo scenario can synthesize schema-valid runtime events/inventory/evals when live data is unavailable.

### Unconfirmed
- Canonical production runtime hook locations for all deployment modes (especially event feed semantics and multi-provider eval shape).

### Planned
- Environment-specific live-hook validation and commit-pinned runtime compatibility matrix updates.

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

```bash
cd integration-adapter
python -m integration_adapter.collect_from_onyx
python -m integration_adapter.generate_artifacts
python -m integration_adapter.run_launch_gate
```

Force demo mode:

```bash
cd integration-adapter
python -m integration_adapter.generate_artifacts --demo
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

See `../docs/demo-scenario.md` for steps, expected outputs, and real-vs-synthetic labeling.

## Testing notes

- Adapter tests include unit and integration-style coverage.
- Untestable runtime assumptions are documented in `../docs/testing-blind-spots.md`.
