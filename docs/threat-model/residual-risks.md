# Residual risks

This section captures what remains risky after applying implemented controls.

| Risk ID | Residual risk | Why it remains | Current mitigation in repo | Status |
|---|---|---|---|---|
| RR-01 | Runtime-hook parity uncertainty | Live deployment hook paths/semantics not fully validated in this workspace | explicit `Unconfirmed` labeling and parity documentation | **Unconfirmed** |
| RR-02 | Demo/fixture overgeneralization risk | Demo evidence can diverge from production behavior | demo-only labeling and conservative evidence wording | **Partially Implemented** |
| RR-03 | Artifact tamper resistance limits | Hash/signature verification helps, but no full external attestation chain here | integrity manifest + Launch Gate blocker logic | **Partially Implemented** |
| RR-04 | Tool-surface behavioral variance | Tool enforcement semantics depend on runtime/deployment controls outside adapter scope | tool decision evidence normalization + adversarial scenarios | **Partially Implemented** |
| RR-05 | Retrieval source trust drift | Indexed source quality/authority can degrade over time | retrieval-poisoning scenario packs and fail/warn scoring | **Partially Implemented** |

## Planned risk-reduction work

- **Planned:** deployment-validated runtime hook certification matrix.
- **Planned:** stronger artifact attestation chain suitable for external audits.
- **Planned:** recurring adversarial baseline-vs-protected differential runs in CI evidence publication.
