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
