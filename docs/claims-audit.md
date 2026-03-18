# Claims Audit (README + docs)

This audit classifies major claims in this repository using conservative language.

## Proven (code + tests in this workspace)

- **Proven:** Evidence pipeline and artifact generation are implemented and test-covered in `integration-adapter`.
- **Proven:** Shared evidence artifact schema exists and is machine-readable (`artifacts_schema/schema.json`).
- **Proven:** Launch Gate-related artifacts are generated and validated by adapter workflows and tests.

## Partially proven (implemented with environment/runtime caveats)

- **Partially Proven:** Dashboard ingestion compatibility is schema-aligned in this workspace, but end-to-end production integration depends on deployment wiring.
- **Partially Proven:** Repository-level readiness summary (`launch_gate_summary.json`) exposes a conservative contract, but it is not a deployment-certified verdict.
- **Partially Proven:** Cross-repo contract documentation (`integration/integration.md`) is implemented, while transport/channel integration remains environment-specific.

## Conceptual / Unconfirmed

- **Conceptual:** Production security enforcement effectiveness cannot be proven from fixture/demo evidence alone.
- **Conceptual:** Canonical runtime hook parity across all deployment modes remains unvalidated in this workspace.
- **Conceptual:** Deployment-grade attestation/non-repudiation guarantees are outside currently demonstrated scope.

## Reviewer use

For claim-bearing reviews:
1. Confirm implementation file(s) exist.
2. Confirm test coverage exists.
3. Treat deployment/runtime assumptions as **Unconfirmed** unless verified in-environment.
