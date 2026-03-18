# Control points

## CP-01 — Event normalization and schema validation

- Implementation modules:
  - `integration-adapter/integration_adapter/mappers.py`
  - `integration-adapter/integration_adapter/schemas.py`
- What is enforced:
  - normalized field mapping,
  - required schema conformance,
  - identity/authz provenance tagging.
- Validation evidence:
  - adapter test suite,
  - launch-gate schema validity checks.
- Status: **Implemented**.

## CP-02 — Artifact generation boundary

- Implementation modules:
  - `integration-adapter/integration_adapter/pipeline.py`
  - `integration-adapter/integration_adapter/artifact_output.py`
- What is enforced:
  - deterministic output structure for audit/eval/launch-gate artifacts.
- Validation evidence:
  - generated artifact tree and CI smoke flows.
- Status: **Implemented**.

## CP-03 — Adversarial scenario evaluation

- Implementation modules:
  - `integration-adapter/integration_adapter/adversarial_harness.py`
- What is enforced:
  - scenario execution and machine-readable scoring for key abuse classes.
- Validation evidence:
  - scenario fixtures and targeted tests for retrieval poisoning and output leakage.
- Status: **Implemented**.

## CP-04 — Evidence-to-review traceability

- Implementation modules:
  - `integration-adapter/integration_adapter/control_matrix.py`
  - `integration-adapter/integration_adapter/evidence_report.py`
  - `integration-adapter/integration_adapter/launch_gate_bridge.py`
- What is enforced:
  - threat/control/test/artifact mapping and conservative verdict synthesis from artifacts.
- Validation evidence:
  - module-specific tests and generated docs outputs.
- Status: **Implemented**.

## CP-05 — Artifact integrity verification

- Implementation modules:
  - `integration-adapter/integration_adapter/verify_artifact_integrity.py`
  - launch-gate evaluator checks for integrity blockers
- What is enforced:
  - hash/signature mode verification and blocker-on-failure behavior.
- Validation evidence:
  - integrity verification command + launch-gate blocking policy docs.
- Status: **Implemented**.

## CP-06 — Deployment parity certainty

- Implementation/documentation points:
  - exporter parity docs and status labeling discipline.
- What is enforced:
  - gap disclosure when runtime hook parity is not validated.
- Validation evidence:
  - explicit `Unconfirmed` labeling.
- Status: **Unconfirmed**.
