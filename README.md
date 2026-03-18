# rag-security-platform

## Repository Role in AI Trust & Security System

**Primary role (exact): Evaluation.**

**Implemented:** This repository is the security testing + evidence plane for the overall system. It is responsible for producing normalized artifacts and launch-readiness evidence from runtime-aligned inputs.

System-wide role map:
- `myStarterKit` → Implementation (secure runtime)
- `rag-security-platform` (**this repository**) → **Evaluation** (security testing & evidence)
- `myStarterKit-maindashb` (`myStarterKit-maindashb-main/` in this workspace) → Observability (dashboard)
- `website` → Presentation


## Terminology baseline

- **AI Trust & Security Readiness**: system-wide program name used in this repository.
- **Layer Retrofit**: additive integration approach (no destructive merge of upstream repos).
- **Secure Starter Kit**: governance/consumption counterpart referenced by this evaluation repo.
- **Launch Gate**: readiness verdict stage generated from evidence artifacts.

Supporting control terms used consistently in docs:
- prompt injection defense
- retrieval validation
- tool authorization
- runtime monitoring
- auditability

## Why this role assignment is enforced

Role determination is based on code present in this repo:
- **Implemented:** evidence orchestration (`integration_adapter/evidence_pipeline.py`, `pipeline.py`)
- **Implemented:** artifact generation (`integration_adapter/generate_artifacts.py`, `artifact_output.py`)
- **Implemented:** Launch Gate evidence evaluation (`integration_adapter/run_launch_gate.py`, `launch_gate_evaluator.py`)
- **Implemented:** adversarial and control-matrix evaluation paths (`integration_adapter/adversarial_harness.py`, `control_matrix.py`)

## What this repo does NOT do

- **Implemented:** runtime feature implementation inside `onyx-main/`.
- **Implemented:** mutating dashboard behavior inside `myStarterKit-maindashb-main/`.
- **Implemented:** website presentation logic.

Unclear or deployment-specific runtime-hook claims must remain **Unconfirmed** unless implemented and tested in this workspace.

Misplaced components (kept read-only in this workspace):
- **Implemented:** `onyx-main/` is not implementation ownership here; it is a runtime compatibility mirror.
- **Implemented:** `myStarterKit-maindashb-main/` is not dashboard ownership here; it is an observability compatibility mirror.

## Role-aligned folder structure

### Primary owned evaluation paths
- `integration-adapter/` — evaluation pipeline, normalization, artifact generation, Launch Gate checks
- `docs/` — evaluation evidence, threat-model, compatibility, and claim-boundary documentation
- `scripts/` — workspace validation utilities used by evaluation workflows

### Reference mirrors (read-only integration context)
- `onyx-main/` — runtime reference mirror for extraction compatibility
- `myStarterKit-maindashb-main/` — observability reference mirror for read-only compatibility

## Integration boundary (artifact-first)

**Implemented:** integration across planes is through artifacts, not runtime coupling.

Canonical outputs (generated under `integration-adapter/artifacts/logs/`):
- `audit.jsonl`
- `replay/*.replay.json`
- `evals/*.jsonl`
- `launch_gate/*.json`
- `launch_gate/*.md`


## Artifacts & Evidence

**Implemented:** Shared security evidence schema is published for cross-plane consumers:
- Schema: `artifacts_schema/schema.json`
- Example: `artifacts_schema/example_artifact.json`
- Integration contract: `integration/integration.md`

Intended consumers:
- evaluation workflows in this repository,
- read-only observability/dashboard integrations,
- website/presentation reporting pipelines.

Required schema fields:
- `event_type`
- `control_name`
- `threat_type`
- `stage` (`input|retrieval|context|model|tool|output|logging`)
- `decision` (`allow|deny|warn`)
- `reason`
- `timestamp`
- `request_id`
- `severity`


## Evidence Produced by This Repository

**Implemented:** Primary evidence outputs are produced by `integration-adapter` runs under:
- `integration-adapter/artifacts/logs/`

Repository-level placeholder examples (non-synthetic, documentation-only):
- Sample logs placeholder: `artifacts/sample_logs.placeholder.log`
- Sample test output placeholder: `artifacts/sample_test_output.placeholder.txt`
- Sample evaluation result placeholder: `artifacts/sample_evaluation_result.placeholder.json`

These placeholders are intentionally non-authoritative and exist only to define artifact locations.
Use pipeline-generated artifacts for real evidence consumption.


## Reviewer Quick Path

### 5-minute path
1. Run:
   - `python scripts/validate_upstream_provenance_lock.py`
   - `cd integration-adapter && python -m pytest -q`
2. Inspect:
   - `artifacts_schema/schema.json`
   - `integration/integration.md`
   - `docs/system-coherence.md`
3. Expected outputs:
   - provenance lock `PASS`
   - pytest summary with passing tests (for example `129 passed`)

### 15-minute path
1. Generate demo evidence:
   - `make evidence-demo`
2. Verify integrity + gate:
   - `cd integration-adapter && python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs`
   - `cd integration-adapter && python -m integration_adapter.run_launch_gate --artifacts-root artifacts/logs`
3. Inspect generated evidence:
   - `integration-adapter/artifacts/logs/audit.jsonl`
   - `integration-adapter/artifacts/logs/evals/`
   - `integration-adapter/artifacts/logs/launch_gate/`

Evidence artifact locations:
- Primary: `integration-adapter/artifacts/logs/`
- Contract schema: `artifacts_schema/schema.json`
- Integration contract: `integration/integration.md`


## Dashboard Integration

**Implemented:** Dashboard-facing ingestion should consume JSON evidence records aligned to `artifacts_schema/schema.json`.

Required dashboard-ingestion fields:
- `event_type`
- `decision`
- `stage`
- `timestamp`
- `request_id`

Sample JSON output for ingestion contract checks:
- `artifacts/dashboard_ingestion_sample.json`

Primary generated evidence location:
- `integration-adapter/artifacts/logs/`


## Launch Gate Readiness Summary

**Implemented:** Repository-level readiness signal is exposed in `launch_gate_summary.json` with:
- `controls_present`
- `tests_passed`
- `high_risk_findings`
- `readiness_status` (`pass|conditional|fail`)

Current file is a conservative repository summary artifact; use generated evidence under `integration-adapter/artifacts/logs/launch_gate/` for run-specific verdicts.


## Claims vs Evidence

Claim audit status used in this repository:
- **Proven (code/test):** implemented behavior with local test coverage in this workspace.
- **Partially Proven:** implemented artifacts/contracts with deployment/runtime caveats.
- **Conceptual:** architecture or assurance statements not fully validated here.

Audit references:
- `docs/claims-audit.md`
- `docs/defensibility-claims.md`

Conservative boundary:
- Unconfirmed: canonical runtime hook not validated in this workspace.

## Practical commands

- `make provenance-check`
- `make adapter-ci`
- `make evidence`
- `make launch-gate-bridge`

## Related Repositories in AI Trust & Security System

- **myStarterKit**  
  - **Role:** implementation plane  
  - **Link:** https://github.com/Amhdour/myStarterKit  
  - **Contribution:** runtime application behavior and security control implementation.

- **rag-security-platform** (this repository)  
  - **Role:** evaluation plane  
  - **Link:** https://github.com/Amhdour/rag-security-platform  
  - **Contribution:** evidence normalization, adversarial evaluation, artifact generation, and Launch Gate-ready readiness outputs.

- **myStarterKit-maindashb**  
  - **Role:** dashboard/observability plane  
  - **Link:** https://github.com/Amhdour/myStarterKit-maindashb  
  - **Contribution:** read-only observability and reviewer-facing evidence visualization.

## Website

https://www.amhdour.cv
