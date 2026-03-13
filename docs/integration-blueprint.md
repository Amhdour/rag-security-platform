# Onyx + AI Trust Starter Kit Integration Blueprint

## Scope and constraints

This blueprint defines a non-invasive integration where:
- **Implemented:** **Onyx** remains runtime execution plane.
- **Implemented:** **Starter Kit** remains governance/evidence/launch-gate plane.
- **Implemented:** **integration-adapter** remains additive translation plane.

Assumptions not fully verifiable from current workspace are explicitly labeled as **Unconfirmed**.

## Status labels used in this document

- **Implemented**: present in code and runnable in this workspace.
- **Partially Implemented**: present with environment/runtime caveats.
- **Demo-only**: synthetic or demo fixture path.
- **Unconfirmed**: hook/source not conclusively pinned from code in this workspace.
- **Planned**: target behavior not yet implemented.

## Repository architecture analysis

### Onyx (`onyx-main`)

**Implemented (observed structure):**
- `backend/onyx/server/`
- `backend/onyx/connectors/`
- `backend/onyx/background/celery/`
- `backend/onyx/db/`
- `web/`

**Partially Implemented (for this integration workspace):**
- adapter can optionally read some Onyx DB paths if runtime env is available.

### Starter Kit (`myStarterKit-maindashb-main`)

**Implemented (observed structure):**
- `app/`, `policies/`, `telemetry/audit/`, `launch_gate/`, `observability/`, `evals/`
- read-only dashboard endpoints with 405 for mutating methods.

### Integration adapter (`integration-adapter`)

**Implemented:**
- schema/mapping pipeline
- artifact generation commands
- launch-gate evaluator
- demo scenario
- tests for parser/generation/launch-gate/dashboard compatibility

**Demo-only:**
- synthetic fallback payloads in demo paths.

**Unconfirmed:**
- canonical production event/eval hook parity across all Onyx deployment modes.

## Overlap analysis

Overlapping concern domains:
1. audit telemetry
2. tool governance metadata
3. retrieval decision metadata
4. eval reporting
5. readiness reporting

**Implemented conflict-avoidance strategy:**
- no model replacement across repos
- artifact contract boundary between runtime and governance

## Integration boundary

**Implemented boundary:** artifact files
- adapter input: exporter payloads (live or file-backed)
- adapter output:
  - `audit.jsonl`
  - `replay/*.replay.json`
  - `evals/*.jsonl`
  - `evals/*.summary.json`
  - `launch_gate/*.json` and `launch_gate/*.md`

## Trust zones

1. **Implemented:** Zone A — Runtime (Onyx)
2. **Implemented:** Zone B — Adapter (read/transform/export)
3. **Implemented:** Zone C — Governance (Starter Kit read-only consumption)

**Implemented (design intent):** Expected flow is **A -> B -> C**.

## Integration TODOs / unconfirmed hooks

- **Unconfirmed** canonical Onyx production source for lifecycle/retrieval/tool/MCP runtime events.
- **Unconfirmed** canonical Onyx MCP usage counters/semantics.
- **Unconfirmed** canonical multi-provider eval output compatibility details.

## Planned next verification

- **Planned:** Pin and verify live hook sources against specific upstream commits.
- **Planned:** Add environment-backed integration tests for DB/event hook paths.
