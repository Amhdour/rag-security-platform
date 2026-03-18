# Negative-Path Security Validation Coverage

This document summarizes deterministic failure/adversarial-path checks currently exercised in this workspace.

## Covered scenarios (Implemented)

- malformed source documents (`validate_config --strict-sources`, exporter malformed-line handling)
- incompatible schema versions (pipeline compatibility blocking + Launch Gate contract checks)
- stale critical artifacts (Launch Gate freshness fail-closed)
- missing identity/authz evidence (Launch Gate `identity_authz_evidence_presence` FAIL)
- missing/unknown MCP classification (Launch Gate `mcp_inventory_classified` WARN)
- partial exporter failure (Launch Gate `exporter_degradation` FAIL on high parse failures)
- artifact write failure (pipeline writes failed-run adapter health and raises)
- synthetic fallback in `prod_like` (profile safeguards block)
- Launch Gate fail-closed behavior for critical evidence/malformed artifacts
- evidence tampering signal detection (contract vs audit normalized-schema mismatch fails)

## Test references

- `integration-adapter/tests/test_launch_gate_evaluator.py`
- `integration-adapter/tests/test_pipeline.py`
- `integration-adapter/tests/test_env_profiles.py`
- `integration-adapter/tests/test_config_validation.py`

## Remaining blind spots

- **Unconfirmed:** canonical runtime hook not validated in this workspace.
- **Unconfirmed:** tampering detection is consistency-based only (no cryptographic signatures/attestations).
- **Planned:** signed artifact manifests / attestations for stronger anti-tamper guarantees.
