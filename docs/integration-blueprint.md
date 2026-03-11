# Onyx + AI Trust Starter Kit Integration Blueprint

## Scope and Constraints

This blueprint defines a **non-invasive integration** where:

- **Onyx** remains the runtime execution plane (chat, retrieval, connectors, tools, agents, MCP).
- **Starter kit** remains the governance plane (policy framing, telemetry/evidence views, launch-gate readiness).
- Integration is additive via `integration-adapter/` without full repository merge.

Assumptions that could not be fully validated from code are explicitly marked as **UNCONFIRMED**.

## Repository Architecture Analysis

### Onyx (`onyx-main`) high-level architecture

Observed primary areas:

- `backend/onyx/server/` for API features and runtime endpoints.
- `backend/onyx/connectors/` for source integrations and indexing adapters.
- `backend/onyx/background/celery/` for async ingestion and processing workers.
- `backend/onyx/evals/` for evaluation flows.
- `backend/onyx/db/` for persistence models and query paths.
- `web/` for runtime UI.

Operationally, Onyx appears to provide:

- request handling and chat orchestration,
- retrieval/indexing over connectors,
- tool exposure and execution mediation,
- MCP-related integrations,
- eval and operational telemetry outputs.

### Starter kit (`myStarterKit-maindashb-main`) high-level architecture

Observed primary areas:

- `app/` orchestration and contracts.
- `policies/` policy loading and enforcement interfaces.
- `telemetry/audit/` event contracts, sinks, replay generation.
- `launch_gate/` machine-checkable release-readiness evaluation.
- `observability/` read-only dashboard API/UI over artifact files.
- `evals/` scenario-based safety/quality checks.

The starter kit cleanly separates governance concerns from runtime execution.

## Overlap Analysis

Overlapping concern domains:

1. **Audit telemetry**: both systems define audit-like event records.
2. **Tool governance**: both represent tool decisions and guarded execution.
3. **Retrieval governance**: both include retrieval decision/event concepts.
4. **Eval reporting**: both can produce evaluation outputs.
5. **Release readiness**: starter kit has explicit launch gate; Onyx has operational signals that can feed it.

Potential conflict avoided by integration boundary:

- No direct replacement of Onyx runtime models.
- No direct replacement of starter-kit policy/launch-gate logic.
- Use normalized artifacts as interoperability layer.

## Clean Integration Boundary

Recommended boundary: **artifact contract boundary**

- Input side (from Onyx runtime plane): normalized dictionaries / exported snapshots / runtime events.
- Adapter side: translates into starter-kit-compatible artifacts.
- Output side (to starter-kit governance plane):
  - `audit.jsonl`
  - replay files
  - eval summary/result files
  - launch gate summary files

No runtime callbacks from starter-kit dashboard into Onyx are required.

## Trust Zones

1. **Zone A – Runtime (Onyx)**
   - Executes user requests, retrieval, tools, and MCP.
   - Produces raw runtime metadata/events.
2. **Zone B – Adapter (integration-adapter)**
   - Read/transform/export only.
   - No policy enforcement authority.
3. **Zone C – Governance (starter kit)**
   - Consumes artifacts read-only for dashboarding.
   - Performs launch-gate evaluation and evidence synthesis.

Data is expected to flow A -> B -> C.

## Data Flows

1. Onyx event/inventory snapshots are exported or provided to adapter APIs.
2. Adapter maps Onyx concepts to normalized vocabulary.
3. Adapter writes starter-kit artifact files under an artifact root.
4. Starter-kit observability API reads from configured artifact root.
5. Launch-gate workflows consume generated summaries and event counts.

## Recommended Integration Pattern

### Pattern: Sidecar-style artifact adapter

- New top-level package: `integration-adapter/`.
- Pure-Python translator and writer with minimal dependencies.
- Pluggable input model (raw dicts first; runtime hooks later).
- Deterministic artifact output layout compatible with starter-kit readers.

### Why this pattern

- Low coupling and reversible.
- Preserves each repository’s ownership boundaries.
- Supports incremental runtime hook integration.
- Keeps dashboard read-only and governance-centric.

## Integration TODOs / Unconfirmed Runtime Hooks

The following are intentionally marked TODO pending runtime verification:

- **UNCONFIRMED** exact Onyx event bus/log source for retrieval/tool/MCP runtime events.
- **UNCONFIRMED** canonical Onyx location for MCP server usage counters.
- **UNCONFIRMED** canonical Onyx eval output schema when multiple providers are configured.

Adapter code will include explicit TODO markers where these hooks should be finalized.
