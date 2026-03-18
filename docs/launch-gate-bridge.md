# Launch Gate Bridge (Evaluation -> Verdict)

## Purpose

**Implemented:** This bridge converts adapter evaluation outputs into a launch-gate style verdict that is reviewer-friendly and artifact-backed.

It summarizes:
- whether core controls exist,
- whether adversarial tests passed,
- what remains risky,
- and whether the system appears safer than an unprotected baseline.

**Unconfirmed:** canonical runtime hook not validated in this workspace.

## Inputs

- `integration-adapter/artifacts/logs/evals/*.jsonl`
- `integration-adapter/artifacts/logs/launch_gate/*.json` (if present)
- control mapping metadata from `integration_adapter.control_matrix`

## Outputs

- Example JSON verdict: `docs/launch-gate-bridge.example.json`
- Example Markdown verdict: `docs/launch-gate-bridge.example.md`

## Decision semantics

- `no_go` when core controls are absent or eval failures exist.
- `conditional_go` when failures are absent but warnings/residual uncertainty remain.
- `go` when failures/warnings are absent and evidence indicates strong control posture.

**Partially Implemented:** Baseline comparison is relative to available artifact evidence (e.g., blocked/denied/gated scenarios) and does not prove production-grade runtime enforcement alone.

## Regenerate

```bash
make launch-gate-bridge
```

Direct command:

```bash
cd integration-adapter
python -m integration_adapter.launch_gate_bridge \
  --artifacts-root artifacts/logs \
  --output-json ../docs/launch-gate-bridge.example.json \
  --output-md ../docs/launch-gate-bridge.example.md
```
