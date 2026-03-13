# rag-security-platform-main

Integration workspace for a **three-plane architecture**:

- **`onyx-main/`** = runtime execution plane (chat, retrieval, connectors, tools, personas/agents, MCP).
- **`myStarterKit-maindashb-main/`** = governance/evidence/launch-gate/read-only dashboard plane.
- **`integration-adapter/`** = translation plane that normalizes runtime state/events into Starter Kit-compatible artifacts.

**Implemented:** This repository intentionally keeps these planes separated rather than merging upstream codebases.

## Repository purpose

1. **Implemented:** Preserve upstream boundaries and responsibilities.
2. **Implemented:** Add interoperability in `integration-adapter/`.
3. **Implemented:** Produce artifact evidence consumable by governance/launch-gate workflows.
4. **Implemented:** Keep dashboard behavior read-only and artifact-driven.

**Implemented:** See `docs/integration-blueprint.md` for architecture notes and constraints.

## Architecture at a glance

```text
[Onyx runtime] --(inventory/events exports)--> [integration-adapter] --(artifacts/logs/*)--> [Starter Kit governance/dashboard]
```

## Implementation status (claims audit)

### Implemented
- Adapter schema validation and normalization pipeline for inventory/events/evals, including normalized identity/authorization evidence fields with sourced/derived/unavailable markers.
- Artifact generation commands and output writing (`audit`, `replay`, `eval`, `launch_gate`).
- Evidence-based launch-gate evaluator (artifact quality/presence checks).
- Read-only Starter Kit dashboard artifact parsing compatibility for generated artifacts.

### Partially Implemented
- Exporters can read file-backed inputs and may attempt optional live/service-api/db-backed extraction when runtime environment supports it.
- Exporter source precedence target is `live` > `service_api` > `db_backed` > `file_backed` > `fixture_backed` > `synthetic`.

### Demo-only
- End-to-end demo scenario can use synthetic-but-schema-valid events/inventory/evals when live hooks are unavailable.

### Unconfirmed
- Canonical production Onyx sources for all runtime hooks (event feeds, MCP usage counters, multi-provider eval schema details).

### Planned
- Fully pinned and verified live runtime hook wiring for every domain across deployment modes.

## Top-level folder guide

- **Implemented:** `onyx-main/` remains upstream Onyx runtime code.
- **Implemented:** `myStarterKit-maindashb-main/` remains upstream governance/dashboard code.
- **Implemented:** `integration-adapter/` remains additive translation and evidence tooling.
- **Implemented:** `docs/` contains workspace architecture/provenance/compatibility/maturity/demo/testing docs.

## Upstream provenance and compatibility

- `docs/upstream-provenance.md`
- `docs/upstream-provenance.lock.json`
- `docs/compatibility-matrix.md`
- `docs/maturity-model.md`
- `docs/threat-model.md`
- `docs/schema-versioning.md`
- `docs/exporter-parity.md`
- `docs/adapter-health.md`
- `docs/launch-gate-policy.md`
- `docs/fixture-catalog.md`
- `docs/environment-profiles.md`
- `docs/identity-authz-evidence.md`
- `docs/negative-path-validation.md`
- `docs/artifact-integrity.md`
- `docs/artifact-retention-policy.md`

**Implemented:** Validate machine-readable provenance lock shape with `make provenance-check` (or `python scripts/validate_upstream_provenance_lock.py`).

**Implemented:** Adapter contract version enforcement is documented in `docs/schema-versioning.md` and enforced during artifact generation and launch-gate evaluation.

**Implemented:** Exporter source-mode metadata and parity coverage are documented in `docs/exporter-parity.md`.

**Implemented:** Adapter operational telemetry and health reporting are documented in `docs/adapter-health.md`.

**Implemented:** Launch-gate evidence-quality policy and fail/warn/pass semantics are documented in `docs/launch-gate-policy.md`.

**Implemented:** Adapter extraction/normalization/gate contracts are validated against real-derived sanitized fixtures documented in `docs/fixture-catalog.md`.

**Implemented:** Environment profiles (`demo`, `dev`, `ci`, `prod_like`) and safeguards are documented in `docs/environment-profiles.md` and enforced by adapter profile validation.

**Implemented:** Identity/authz/delegation evidence model and proven-vs-inferred semantics are documented in `docs/identity-authz-evidence.md`.

**Implemented:** Negative-path security validation coverage and current blind spots are documented in `docs/negative-path-validation.md`.

**Implemented:** Artifact integrity manifest/hash safeguards and verification command are documented in `docs/artifact-integrity.md`.

## Reproducible adapter packaging and execution

**Implemented:** Install adapter tooling with development extras:

```bash
cd integration-adapter
python -m pip install -e .[dev]
```

**Implemented:** Console entrypoints are published via `pyproject.toml`:
- `integration-adapter-collect`
- `integration-adapter-generate`
- `integration-adapter-gate`
- `integration-adapter-evidence`
- `integration-adapter-validate`
- `integration-adapter-ci-smoke`
- `integration-adapter-health`

**Implemented:** Configuration validation command (copy/paste):

```bash
cd integration-adapter
python -m integration_adapter.validate_config
```

**Implemented:** Strict source validation (requires all source env vars to be set and parseable):

```bash
cd integration-adapter
python -m integration_adapter.validate_config --strict-sources
```

**Implemented:** CI-friendly end-to-end command without external services:

```bash
make adapter-ci
```

## Operations quickstart (copy/paste)

Validate configuration and profile policy:

```bash
cd integration-adapter
python -m integration_adapter.validate_config --profile dev
```

Generate demo artifacts with deterministic profile:

```bash
cd integration-adapter
python -m integration_adapter.generate_artifacts --demo --profile demo --artifacts-root artifacts/logs
```

Run launch-gate on generated artifacts:

```bash
cd integration-adapter
python -m integration_adapter.run_launch_gate --profile demo --artifacts-root artifacts/logs
```

Verify artifact integrity manifest + hashes (default `hash_only` mode):

```bash
cd integration-adapter
python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs
```

Optional signed-manifest verification:

```bash
cd integration-adapter
python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs --integrity-mode signed_manifest --signing-key-path /secure/path/signing.key
```


Apply artifact retention policy (dry-run by default):

```bash
cd integration-adapter
python -m integration_adapter.artifact_retention --dry-run --profile ci --artifacts-root artifacts/logs
```

Apply destructive cleanup after validation/integrity checks:

```bash
cd integration-adapter
python -m integration_adapter.artifact_retention --apply --profile ci --artifacts-root artifacts/logs
```


Operator health summary (text):

```bash
cd integration-adapter
python -m integration_adapter.health_report --artifacts-root artifacts/logs --format text
```

Metrics-style summary:

```bash
cd integration-adapter
python -m integration_adapter.health_report --artifacts-root artifacts/logs --format metrics
```

Expected outputs:
- **Implemented:** `artifact_bundle.contract.json`
- **Implemented:** `artifact_integrity.manifest.json`
- **Implemented:** `adapter_health/adapter_run_summary.json`
- **Implemented:** `audit.jsonl`
- **Implemented:** `replay/*.replay.json`
- **Implemented:** `evals/*.jsonl` and `evals/*.summary.json`
- **Implemented:** `launch_gate/security-readiness-*.json`

Failure conditions (non-zero exit):
- **Implemented:** invalid configuration in strict validation mode.
- **Implemented:** schema compatibility blocked.
- **Implemented:** profile safeguards blocked (for example `prod_like` + synthetic/demo fallback).
- **Implemented:** launch-gate critical FAIL checks (missing/stale critical evidence, integrity failures).
- **Implemented:** integrity verifier detects missing files/manifest entries/hash mismatches.
- **Implemented:** integrity verifier fails when signed-manifest verification is requested and signature validation fails.
- **Implemented:** retention cleanup must run in explicit apply mode and preserves required artifacts plus latest successful launch-gate runs.

## Tests

### Integration adapter

```bash
cd integration-adapter
python -m pytest -q
```

### Starter Kit

```bash
cd myStarterKit-maindashb-main
pytest -q
```

### Onyx

**Implemented:** Onyx has broader env/service requirements; see `onyx-main/AGENTS.md` and `onyx-main/README.md`.

## Workspace CI automation

**Implemented:** GitHub Actions workflow `.github/workflows/ci.yml` runs on both `push` and `pull_request` events for this workspace.

**Implemented:** CI executes the following checks in order:
1. Python 3.11 setup and adapter dependency installation (`pip install -e ./integration-adapter[dev]`).
2. Upstream provenance lock validation (`python scripts/validate_upstream_provenance_lock.py`).
3. Integration adapter test suite (`cd integration-adapter && python -m pytest -q`).
4. CI smoke pipeline (`cd integration-adapter && python -m integration_adapter.ci_smoke --profile ci --artifacts-root artifacts/logs-ci-smoke`).
5. Artifact regeneration for a fresh manifest snapshot (`cd integration-adapter && python -m integration_adapter.generate_artifacts --demo --profile ci --artifacts-root artifacts/logs-ci-smoke`).
6. Artifact integrity verification against smoke outputs (`cd integration-adapter && python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs-ci-smoke`).

**Implemented:** CI blockers (hard-fail conditions) include:
- failing adapter tests,
- invalid upstream provenance lock shape,
- smoke pipeline execution failures or missing required outputs,
- integrity manifest failures (missing entries or hash mismatch).

**Demo-only:** Smoke outputs are generated from deterministic demo-safe pathways and local fixtures by design; they validate pipeline contracts, not production runtime enforcement.

## Evidence generation pipeline

Preferred command path (step-by-step):

```bash
cd integration-adapter
python -m integration_adapter.collect_from_onyx
python -m integration_adapter.generate_artifacts
python -m integration_adapter.run_launch_gate
```

One-command pipeline (repo root):

```bash
make evidence
```

Step-by-step pipeline (repo root):

```bash
make evidence-step
```

**Implemented:** This executes collection, artifact generation, launch-gate evaluation, verifies required output files, and returns non-zero on fatal pipeline failures.

Demo mode:

```bash
make evidence-demo
```

Or directly:

```bash
cd integration-adapter
python -m integration_adapter.evidence_pipeline --demo --profile demo
```

CI smoke (demo, no external services):

```bash
make adapter-smoke
```

Optional artifacts-root override for step commands:

```bash
cd integration-adapter
python -m integration_adapter.generate_artifacts --demo --profile demo --artifacts-root artifacts/logs
python -m integration_adapter.run_launch_gate --profile demo --artifacts-root artifacts/logs
```

Expected outputs under `artifacts/logs`:
- **Implemented:** `audit.jsonl`
- **Implemented:** `replay/*.replay.json`
- **Implemented:** `evals/*.jsonl` and `evals/*.summary.json`
- **Implemented:** `launch_gate/*.json` and `launch_gate/*.md`

> Launch-gate results here are **evidence-quality outputs**, not standalone proof of runtime control enforcement.
>
> The launch-gate machine output explicitly separates:
> - `evidence_status.present`
> - `evidence_status.incomplete`
> - `control_assessment.enforced`
> - `control_assessment.proven`
>
> `control_assessment.proven` remains `false` in this workspace unless runtime enforcement is independently validated.
>
> Blockers (fail) and residual risks (warn) are emitted separately in both machine-readable and markdown launch-gate outputs.

## End-to-end demo scenario

Run the reproducible demo from repo root:

```bash
make demo
```

Or directly:

```bash
cd integration-adapter
python -m integration_adapter.demo_scenario
```

**Partially Implemented:** This demo executes the full story (runtime request -> retrieval -> tool decision -> MCP usage representation -> eval evidence -> artifacts -> launch-gate -> dashboard read verification), preferring real extraction and using synthetic schema-valid fallbacks only where required.

**Implemented:** The demo report includes per-domain real/synthetic labels, step-level provenance, and `event_type_coverage` for key runtime event types.

After running, inspect:
- **Implemented:** `integration-adapter/artifacts/logs/demo_scenario.report.json`
- **Implemented:** `integration-adapter/artifacts/logs/launch_gate/security-readiness-<STAMP>.json`

**Implemented:** See `docs/demo-scenario.md` for exact steps, output expectations, and remaining realism gaps.

## Testing blind spots

**Unconfirmed:** Known runtime assumptions that are not fully testable in this workspace are tracked in:
- `docs/testing-blind-spots.md`


## Final hardening review

- Current final hardening assessment, unresolved blockers, and prioritized next steps: `docs/final-hardening-review.md`.
