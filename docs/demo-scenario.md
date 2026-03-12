# End-to-End Demo Scenario: Runtime to Governance Evidence Flow

Scenario goal (demo path):
1. request enters runtime context
2. retrieval touches sources
3. tool decision is evaluated
4. MCP usage is represented
5. eval evidence is generated
6. artifacts are written
7. launch gate produces a result
8. dashboard reads artifacts

## Status labels for this scenario

- **Demo-only**: scenario is intended for reproducible review/demo workflows.
- **Partially Implemented**: uses real exporter outputs when available.
- **Demo-only / Synthetic**: falls back to schema-valid synthetic payloads when live data is unavailable.
- **Unconfirmed**: does not prove production runtime enforcement or full live hook parity.

## Run command

```bash
cd integration-adapter
python -m integration_adapter.demo_scenario
```

Optional artifacts root override:

```bash
cd integration-adapter
python -m integration_adapter.demo_scenario --artifacts-root artifacts/logs
```

## Real vs synthetic behavior

The scenario attempts real exporter reads first. For any missing domain, it uses synthetic demo payloads.

Generated report:
- `artifacts/logs/demo_scenario.report.json`

Includes per-domain label:
- `real_vs_synthetic.connectors`
- `real_vs_synthetic.tools`
- `real_vs_synthetic.mcp_inventory`
- `real_vs_synthetic.runtime_events`
- `real_vs_synthetic.eval_results`

Values:
- `real`
- `synthetic`

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

## Dashboard-read verification

The demo performs read-only parse verification using Starter Kit artifact readers.

- Success indicates parser compatibility for generated artifacts.
- Failure returns non-zero exit code.

## Visualize in Starter Kit dashboard

```bash
cd myStarterKit-maindashb-main
DASHBOARD_ARTIFACTS_ROOT=../integration-adapter/artifacts/logs python -m observability.api
```

Open `http://127.0.0.1:8080/`.

## Limitations

- **Unconfirmed**: production enforcement guarantees are not established by this demo.
- **Unconfirmed**: all deployment-specific live hooks are not fully validated here.
- **Implemented**: artifact compatibility and read-only dashboard parsing in this workspace.
