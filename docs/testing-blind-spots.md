# Testing Blind Spots and Untestable Runtime Assumptions

This repository includes strong artifact-level verification, but some runtime assumptions remain untestable in this workspace-only environment.

## What is tested deterministically

- Adapter schema validation and event vocabulary checks.
- Exporter behavior for file-backed data, missing files, malformed inputs.
- Artifact generation and output file completeness.
- Launch-gate pass/warn/fail logic and fail-closed behavior.
- Dashboard compatibility parsing for generated artifacts.
- End-to-end demo pipeline smoke flow.

### Verification matrix (claims -> tests)

1. **Schema validation**
   - `integration-adapter/tests/test_schemas.py`
   - `integration-adapter/tests/test_identity_mapping.py`

2. **Exporter outputs**
   - `integration-adapter/tests/test_exporters.py`

3. **Malformed and missing input handling**
   - `integration-adapter/tests/test_malformed_input.py`
   - `integration-adapter/tests/test_missing_fields.py`
   - `integration-adapter/tests/test_evidence_pipeline_failures.py`

4. **Artifact generation**
   - `integration-adapter/tests/test_artifact_generation.py`
   - `integration-adapter/tests/test_pipeline.py`

5. **Launch-gate PASS / WARN / FAIL**
   - `integration-adapter/tests/test_launch_gate_evaluator.py`

6. **Dashboard artifact compatibility (where testable)**
   - `integration-adapter/tests/integration/test_dashboard_artifact_compatibility.py`
   - `integration-adapter/tests/integration/test_dashboard_artifact_compatibility_malformed.py`
   - `integration-adapter/tests/integration/test_dashboard_service_compatibility.py`
   - `myStarterKit-maindashb-main/tests/unit/test_observability_dashboard_api.py`
   - `myStarterKit-maindashb-main/tests/unit/test_observability_artifact_readers.py`

7. **End-to-end demo smoke test**
   - `integration-adapter/tests/integration/test_demo_pipeline_smoke.py`
   - `integration-adapter/tests/test_demo_scenario.py`

## Runtime assumptions not fully testable here

1. **Live Onyx DB/session extraction paths**
   - Exporters include optional Onyx DB-backed reads.
   - In this workspace, these paths are environment-dependent and not guaranteed runnable in CI without runtime services.

2. **Canonical production runtime event feed mapping**
   - Artifact tests validate schema-level compatibility and parser behavior.
   - They do not prove that every deployed Onyx runtime emits identical event semantics.

3. **Production enforcement guarantees**
   - Launch-gate validates evidence presence/quality.
   - It does not by itself prove runtime policy/tool enforcement in production.

## Mitigation guidance

- Treat adapter launch-gate results as evidence-quality checks.
- For production confidence, run environment-specific integration tests against live Onyx services with pinned commits and known data fixtures.
- Keep `demo_scenario.report.json` real-vs-synthetic markers in review workflows.

## Current automated suite scope

- **Adapter unit + integration-style tests** run under `integration-adapter/tests/` and cover schema validation, exporter normalization, malformed/missing input handling, artifact generation, launch-gate pass/warn/fail, dashboard reader compatibility, and demo smoke.
- **Starter Kit dashboard targeted tests** cover read-only API behavior, malformed artifact handling, and local/sibling artifact root resolution.
