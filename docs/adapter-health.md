# Adapter Operational Telemetry and Health Reporting

## Health artifact

**Implemented:** The adapter writes machine-readable operational telemetry at:

- `artifacts/logs/adapter_health/adapter_run_summary.json`

The health summary distinguishes:

- `success`
- `degraded_success`
- `failed_run`

## Telemetry counters

**Implemented:** The health summary includes counters for:

- selected source mode (per exporter)
- fallback usage count
- parse failures
- schema validation failures
- artifact write failures
- launch-gate failure reasons
- stale evidence detections
- partial extraction warnings

## Launch-gate integration

**Implemented:** Launch-gate consumes adapter-health evidence and emits:

- `WARN` when health reports degraded execution,
- `FAIL` when health reports failed execution.

## Troubleshooting guidance

- **Implemented:** Inspect `exporters` diagnostics in the health summary for source selection, warnings, and extraction errors.
- **Implemented:** Use launch-gate blockers/residual risks together with health counters to identify degraded runs.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.
