# End-to-End Demo Scenario: Runtime to Governance Evidence Flow

This is the reproducible demo scenario for `rag-security-platform-main` that exercises the full integration path:

1. request enters runtime context
2. retrieval touches sources
3. a tool decision is evaluated
4. MCP usage is represented if available
5. eval evidence is generated
6. artifacts are written
7. launch gate produces a result
8. dashboard can read the artifacts

## Status labels used here

- **Implemented**: adapter artifact writing, launch-gate generation, dashboard artifact-read verification.
- **Partially Implemented**: real exporter-backed data is used when present in this workspace/runtime.
- **Demo-only**: synthetic but schema-valid data is used where live hooks are unavailable.
- **Unconfirmed**: canonical production runtime hooks are not fully validated across all deployment modes in this workspace.

## Run the demo (exact commands)

From repo root:

```bash
make demo
```

Or directly:

```bash
cd integration-adapter
python -m integration_adapter.demo_scenario
```

Optional output override:

```bash
cd integration-adapter
python -m integration_adapter.demo_scenario --artifacts-root artifacts/logs
```

## What the demo does

- **Partially Implemented:** Attempts **real extraction first** for:
  - connector inventory
  - tool inventory
  - MCP inventory
  - eval results
  - runtime events
- **Demo-only:** Falls back to **synthetic schema-valid payloads** where data is unavailable.
- **Implemented:** Writes normalized artifacts under `artifacts/logs`.
- **Implemented:** Runs launch-gate evaluation and writes machine + markdown outputs.
- **Implemented:** Verifies Starter Kit dashboard artifact readers can parse generated evidence.
- **Implemented:** Writes `demo_scenario.report.json` with per-domain real/synthetic labels and remaining realism gaps.

## Report fields to inspect

Generated report:
- `integration-adapter/artifacts/logs/demo_scenario.report.json`

Key fields:
- `real_vs_synthetic.*` — per-domain source labels.
- `story_steps[]` — per-step source label for the target story.
- `outputs.*` — exact artifact output paths.
- `launch_gate_status` — go / conditional_go / no_go.
- `dashboard_read_verification` — parser compatibility status.
- `remaining_realism_gaps[]` — explicit UNCONFIRMED gaps for this run.

## Expected outputs

Under `integration-adapter/artifacts/logs/` (or configured root):
- `audit.jsonl`
- `connectors.inventory.json`
- `tools.inventory.json`
- `mcp_servers.inventory.json`
- `evals/demo-e2e.jsonl`
- `evals/demo-e2e.summary.json`
- `replay/demo-trace-1.replay.json`
- `launch_gate/security-readiness-<STAMP>.json`
- `launch_gate/security-readiness-<STAMP>.md`
- `demo_scenario.report.json`

## Dashboard verification path

```bash
cd myStarterKit-maindashb-main
DASHBOARD_ARTIFACTS_ROOT=../integration-adapter/artifacts/logs python -m observability.api
```

Open `http://127.0.0.1:8080/`.

**Implemented:** Dashboard remains read-only; this demo verifies artifact parsing only.

## Remaining realism gaps (typical)

- **Unconfirmed:** canonical runtime event feed hook parity across deployments.
- **Unconfirmed:** canonical eval runtime hook parity (often snapshot/file-backed in this workspace).
- **Unconfirmed:** MCP usage semantics may rely on fallback representation depending on environment.
- **Unconfirmed:** artifact evidence does not independently prove production runtime control enforcement.
