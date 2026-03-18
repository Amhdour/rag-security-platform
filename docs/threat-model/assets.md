# Assets

## Primary assets in scope

| Asset | Why it matters | Evidence location | Status |
|---|---|---|---|
| Normalized audit trail (`audit.jsonl`) | Core attribution for retrieval/tool/policy decisions | `integration-adapter/artifacts/logs/audit.jsonl` | **Implemented** |
| Eval artifacts (`evals/*.jsonl`, summaries) | Security outcome evidence for scenarios and severities | `integration-adapter/artifacts/logs/evals/` | **Implemented** |
| Launch Gate verdict artifacts | Block/allow governance decision basis | `integration-adapter/artifacts/logs/launch_gate/` | **Implemented** |
| Artifact integrity manifest | Detect tampering/mismatch in generated outputs | `integration-adapter/artifacts/logs/artifact_integrity.manifest.json` | **Implemented** |
| Connector/tool/MCP inventories | Enumerate reachable external surfaces | `integration-adapter/artifacts/logs/*.inventory.json` | **Implemented** |
| Identity/authz provenance fields | Distinguish sourced vs derived vs unavailable identity evidence | `audit.jsonl` fields + `identity_authz_field_sources` | **Implemented** |

## Asset constraints

- **Unconfirmed:** artifact correctness does not by itself prove complete runtime event emission.
- **Unconfirmed:** deployment-specific runtime adapters may emit shapes not fully validated in this workspace.
