# Defensibility claim boundaries

This page separates what is demonstrated in this workspace from what remains conceptual.

## Demonstrated in code

- **Implemented:** Adversarial evaluation harness with scenario loading, scoring (`pass` / `fail` / `warn`), JSONL + summary outputs, and markdown report generation in `integration-adapter/integration_adapter/adversarial_harness.py`.
- **Implemented:** Reviewer control matrix generator in `integration-adapter/integration_adapter/control_matrix.py`.
- **Implemented:** Conservative evidence summary generator (Markdown/JSON/optional HTML) in `integration-adapter/integration_adapter/evidence_report.py`.
- **Implemented:** Launch-gate style verdict bridge based on generated artifacts in `integration-adapter/integration_adapter/launch_gate_bridge.py`.
- **Implemented:** Scenario fixture packs for retrieval poisoning and output leakage under `integration-adapter/tests/fixtures/adversarial/`.

## Demonstrated in tests

- **Implemented:** Harness output/scoring behavior coverage in `integration-adapter/tests/test_adversarial_harness.py`.
- **Implemented:** Retrieval-poisoning scenario expectations in `integration-adapter/tests/test_retrieval_poisoning_scenarios.py`.
- **Implemented:** Output-leakage scenario expectations in `integration-adapter/tests/test_output_leakage_scenarios.py`.
- **Implemented:** Control matrix generation coverage in `integration-adapter/tests/test_control_matrix.py`.
- **Implemented:** Evidence report output coverage in `integration-adapter/tests/test_evidence_report.py`.
- **Implemented:** Launch-gate bridge verdict/report coverage in `integration-adapter/tests/test_launch_gate_bridge.py`.

## Conceptual only

- **Unconfirmed:** Canonical runtime hook parity with all production deployment modes is not validated in this workspace.
- **Unconfirmed:** Production-grade security enforcement effectiveness cannot be inferred from demo/fixture runs alone.
- **Unconfirmed:** Safer-than-baseline verdicts are artifact-relative to available evidence, not deployment-certified assurance.

Use explicit wording when repeated elsewhere:

`Unconfirmed: canonical runtime hook not validated in this workspace.`

## Future work

- **Planned:** Validate runtime hook parity against live deployments and pin verified hook mappings by environment.
- **Planned:** Expand adversarial sets to include richer unsafe-tool interaction traces from real execution logs.
- **Planned:** Add stronger artifact attestation and signing-chain guarantees beyond current integrity checks.
- **Planned:** Add recurring CI publication of evidence snapshots for reviewer diffability across releases.

## Review rule

For claim-bearing updates, keep this ordering:

1. Link claim to implementation file(s).
2. Link claim to test coverage.
3. Mark any deployment/runtime gaps as **Unconfirmed**.
4. Avoid production-enforcement wording unless implemented **and** tested in this workspace.
