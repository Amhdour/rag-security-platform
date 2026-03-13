# Schema Versioning Policy

This document defines adapter contract versioning across source ingestion, normalization, artifact bundle output, and launch-gate output.

## Versioned contracts

**Implemented:** The adapter enforces explicit versions in `integration_adapter.versioning`:

- Raw source schema version: `source_schema_version`
- Normalized adapter schema version: `normalized_schema_version`
- Artifact bundle contract version: `artifact_bundle_schema_version`
- Launch-gate output schema version: `launch_gate_schema_version`

Current versions are `1.0` for all contracts.

## Compatibility policy

Policy outcomes are deterministic and test-backed:

- **allowed**
  - exact version match, or
  - same major version with actual minor <= expected minor.
- **warn_only**
  - same major version with actual minor > expected minor (forward minor drift).
- **blocked**
  - major version mismatch,
  - missing version,
  - malformed version format.

This policy distinguishes schema incompatibility from missing-data tolerance:

- schema incompatibility (`blocked`) fails generation or launch-gate contract checks,
- missing-data tolerance remains handled by existing artifact/evidence checks.

## Enforcement points

1. **Artifact generation preflight**
   - validates expected source schema version,
   - validates expected normalized schema version,
   - validates expected artifact bundle schema version,
   - blocks on `blocked` and continues with warnings for `warn_only`.

2. **Artifact stamping**
   - `artifact_bundle.contract.json` stores version contracts,
   - audit/eval/replay/inventory artifacts are stamped with version metadata.

3. **Launch-gate validation**
   - validates `artifact_bundle.contract.json` against expected versions,
   - blocks on incompatible major versions,
   - emits warn residual risk on forward minor drift.

## Configuration

Expected versions are configurable via env vars:

- `INTEGRATION_ADAPTER_EXPECTED_SOURCE_SCHEMA_VERSION`
- `INTEGRATION_ADAPTER_EXPECTED_NORMALIZED_SCHEMA_VERSION`
- `INTEGRATION_ADAPTER_EXPECTED_ARTIFACT_BUNDLE_SCHEMA_VERSION`
- `INTEGRATION_ADAPTER_EXPECTED_LAUNCH_GATE_SCHEMA_VERSION`

## Upgrade / downgrade guidance

- **Minor upgrade (same major, higher minor actual):** warn-only and review contract diffs.
- **Minor downgrade (same major, lower minor actual):** allowed for compatibility.
- **Major version change:** blocked until consumer/producer contracts are upgraded and tests updated.

## Required tests

Run before updating version claims:

```bash
cd integration-adapter
python -m pytest -q
```

Generate sample artifacts with version stamps:

```bash
cd integration-adapter
python -m integration_adapter.generate_artifacts --demo
```


## Operational checks

Validate version compatibility during generation:

```bash
cd integration-adapter
python -m integration_adapter.generate_artifacts --demo --profile demo --artifacts-root artifacts/logs
```

Expected behavior:
- **Implemented:** major-version mismatch in expected vs actual contract returns non-zero with `schema compatibility blocked`.
- **Implemented:** forward minor drift is `warn_only` and surfaced in CLI output and adapter health summary.

Failure conditions:
- **Implemented:** blocked compatibility decisions stop artifact generation before normal completion.
- **Implemented:** launch-gate `artifact_contract_versions` fails on incompatible contract artifacts.
