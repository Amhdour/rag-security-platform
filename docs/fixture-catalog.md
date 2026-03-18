# Adapter Contract Fixture Catalog

This catalog documents pinned fixture sets used for adapter contract tests.

## Fixture location

- `integration-adapter/tests/fixtures/onyx_contracts/`

## Fixture classes

- **Implemented (Real-derived):** `pass/` and `fail/` fixture sets are derived from representative Onyx data shapes.
- **Implemented (Sanitized):** all identifiers, tenant references, and endpoints are sanitized placeholders.
- **Implemented (Synthetic):** synthetic fallback payloads used by adapter demo mode remain in pipeline/demo flows, not in these fixture sets.
- **Implemented (Demo-only):** demo scenario data remains Demo-only and should not be treated as production proof.

## Included fixture families

- connector inventory
- tool inventory
- MCP inventory
- eval results
- runtime event samples (JSONL)
- adversarial retrieval poisoning scenarios (document fixtures + scenario definitions)
- adversarial output leakage scenarios (document fixtures + scenario definitions)

## Provenance metadata

See:
- `integration-adapter/tests/fixtures/onyx_contracts/fixture_manifest.json`

## Regeneration guidance

1. Export representative shapes from non-production Onyx environments.
2. Remove/replace sensitive values (tenants, users, secrets, hostnames).
3. Keep deterministic ordering and formatting.
4. Update fixture manifest timestamp and rerun contract tests.
5. **Planned:** add a scripted sanitizer/regenerator for automated fixture refresh.

## Contract tests

Contract tests validating extraction compatibility, normalization, schema validity, and launch-gate behavior:

- `integration-adapter/tests/test_contract_fixtures.py`

## Adversarial retrieval poisoning fixture pack

- **Implemented (Sanitized):** fixture documents are sanitized markdown inputs designed to resemble realistic enterprise content while avoiding sensitive data.
- **Implemented:** scenario definitions live at `integration-adapter/tests/fixtures/adversarial/retrieval_poisoning/scenarios.json`.
- **Implemented:** each scenario includes `threat`, fixture payload, and `expected_control_behavior` for deterministic scoring tests.
- **Demo-only:** these fixtures are local test/demo evidence and are not production enforcement proof.

Related tests:
- `integration-adapter/tests/test_retrieval_poisoning_scenarios.py`

## Adversarial output leakage fixture pack

- **Implemented (Sanitized):** fixture documents model realistic leakage risks without real sensitive data.
- **Implemented:** scenario definitions live at `integration-adapter/tests/fixtures/adversarial/output_leakage/scenarios.json`.
- **Implemented:** each scenario includes `threat`, fixture payload, and `expected_control_behavior` for deterministic control checks.
- **Demo-only:** fixtures are intended for local test/demo evaluation and not production enforcement proof.

Related tests:
- `integration-adapter/tests/test_output_leakage_scenarios.py`
