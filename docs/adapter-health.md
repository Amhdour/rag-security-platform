# Adapter Operational Telemetry and Health Reporting

## Health artifacts

**Implemented:** The adapter writes machine-readable operational telemetry at:

- `artifacts/logs/adapter_health/adapter_run_summary.json`
- `artifacts/logs/adapter_health/retention_last_run.json` (when retention CLI is executed)

The health summary distinguishes:

- `success`
- `degraded_success`
- `failed_run`

## Operator health CLI

**Implemented:** Emit a concise operator health report:

```bash
cd integration-adapter
python -m integration_adapter.health_report --artifacts-root artifacts/logs --format text
```

JSON output for automation:

```bash
cd integration-adapter
python -m integration_adapter.health_report --artifacts-root artifacts/logs --format json
```

Metrics-style output (flat counters):

```bash
cd integration-adapter
python -m integration_adapter.health_report --artifacts-root artifacts/logs --format metrics
```

## Reported health dimensions

**Implemented:** The health report includes:

- selected source mode by exporter
- fallback usage count
- parse failure count
- validation failure count
- integrity verification result (`ok`, mode, signature status/errors)
- Launch Gate status and failure reasons
- artifact freshness outcomes (`stale_critical`, `missing_critical` counts)
- retention/cleanup outcomes when available (`deleted_count`, dry-run/apply context)
- failure category for operator triage (`none`, `degraded`, `launch_gate_no_go`, `integrity_failure`, `artifact_write_failure`, `pipeline_failure`)

## Health interpretation guidance

- **Implemented:** `success` means no significant degradation signals and no fail-closed gate blockers in the latest run.
- **Implemented:** `degraded_success` means artifacts were produced but one or more quality signals (fallback-heavy extraction, warnings, freshness, or non-go gate status) require operator review.
- **Implemented:** `failed_run` means artifact generation failed before completing a normal successful pipeline path.

Recommended triage order:
1. check `failure_category`,
2. check `integrity` result,
3. check Launch Gate blockers and freshness evidence,
4. inspect exporter source modes + fallback counts,
5. inspect retention outcome if cleanup recently ran.

## Launch Gate integration

**Implemented:** Launch Gate consumes adapter-health and integrity evidence and emits:

- `WARN` when health reports degraded execution,
- `FAIL` when health reports failed execution,
- `FAIL` when integrity verification fails (including signed-manifest verification failures in signed mode).

## Troubleshooting guidance

- **Implemented:** Inspect `exporters` diagnostics in the health summary for source selection, warnings, and extraction errors.
- **Implemented:** Use Launch Gate blockers/residual risks together with health counters to identify degraded runs.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.
