# Testing Blind Spots and Untestable Runtime Assumptions

This repository includes strong artifact-level verification, but some runtime assumptions remain untestable in this workspace-only environment.

## What is tested deterministically

- Adapter schema validation and event vocabulary checks.
- Exporter behavior for file-backed data, missing files, malformed inputs.
- Artifact generation and output file completeness.
- Launch-gate pass/warn/fail logic and fail-closed behavior.
- Dashboard compatibility parsing for generated artifacts.
- End-to-end demo pipeline smoke flow.

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

