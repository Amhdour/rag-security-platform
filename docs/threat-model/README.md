# Threat model package (practical)

This package documents the threat model for the repository as an **artifact-centric integration workspace**.

Scope is grounded in implemented controls in:
- `integration-adapter/integration_adapter/`
- `integration-adapter/tests/`
- `docs/control-matrix.md`
- `docs/launch-gate-policy.md`

Status labels used in this package:
- **Implemented**
- **Partially Implemented**
- **Demo-only**
- **Unconfirmed**
- **Planned**

## Package contents

1. [System overview](./system-overview.md)
2. [Assets](./assets.md)
3. [Trust boundaries](./trust-boundaries.md)
4. [Threat actors](./threat-actors.md)
5. [Attack paths](./attack-paths.md)
6. [Control points](./control-points.md)
7. [Residual risks](./residual-risks.md)
8. [End-to-end secure RAG pipeline walkthrough](./pipeline-walkthrough.md)

## Defensibility notes

- **Implemented:** Controls are described only when corresponding code/tests exist in this repository.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.
- **Unconfirmed:** no production enforcement claim is made from demo artifacts alone.
