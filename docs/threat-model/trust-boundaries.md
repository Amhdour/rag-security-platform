# Trust boundaries

## Boundary B1: Runtime -> Adapter ingestion

- Runtime evidence crosses into adapter extraction/translation logic.
- Risks: malformed events, missing critical events, source-mode fallback ambiguity.
- **Implemented controls:**
  - schema validation and malformed input handling,
  - explicit source-mode and fallback metadata,
  - Launch Gate fail-closed checks for required/critical evidence.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.

## Boundary B2: Adapter processing -> Artifact store

- Normalized data is materialized as audit/eval/Launch Gate artifacts.
- Risks: tampering, partial writes, stale evidence.
- **Implemented controls:**
  - deterministic artifact writers,
  - artifact integrity manifest (hashes/sizes; optional signed mode),
  - freshness and completeness checks in Launch Gate.

## Boundary B3: Artifact store -> Governance consumption

- Governance/review uses generated artifacts without mutating runtime state.
- Risks: over-claiming from demo-only evidence, incomplete reviewer context.
- **Implemented controls:**
  - evidence summary and control matrix generation,
  - explicit status-label discipline (`Implemented`, `Unconfirmed`, etc.),
  - read-only dashboard principle at workspace policy level.
