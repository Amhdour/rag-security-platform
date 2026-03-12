# rag-security-platform-main

Integration workspace for a **three-plane architecture**:

- **`onyx-main/`** = runtime execution plane (chat, retrieval, connectors, tools, personas/agents, MCP).
- **`myStarterKit-maindashb-main/`** = governance/evidence/launch-gate/read-only dashboard plane.
- **`integration-adapter/`** = translation plane that normalizes runtime state/events into Starter Kit-compatible artifacts.

This repository intentionally keeps these planes separated rather than merging upstream codebases.

## Repository purpose

1. Preserve upstream boundaries and responsibilities.
2. Add interoperability in `integration-adapter/`.
3. Produce artifact evidence consumable by governance/launch-gate workflows.
4. Keep dashboard behavior read-only and artifact-driven.

See `docs/integration-blueprint.md` for architecture notes and constraints.

## Architecture at a glance

```text
[Onyx runtime] --(inventory/events exports)--> [integration-adapter] --(artifacts/logs/*)--> [Starter Kit governance/dashboard]
```

## Implementation status (claims audit)

### Implemented
- Adapter schema validation and normalization pipeline for inventory/events/evals.
- Artifact generation commands and output writing (`audit`, `replay`, `eval`, `launch_gate`).
- Evidence-based launch-gate evaluator (artifact quality/presence checks).
- Read-only Starter Kit dashboard artifact parsing compatibility for generated artifacts.

### Partially Implemented
- Exporters can read file-backed inputs and may attempt direct Onyx DB extraction when runtime environment supports it.

### Demo-only
- End-to-end demo scenario can use synthetic-but-schema-valid events/inventory/evals when live hooks are unavailable.

### Unconfirmed
- Canonical production Onyx sources for all runtime hooks (event feeds, MCP usage counters, multi-provider eval schema details).

### Planned
- Fully pinned and verified live runtime hook wiring for every domain across deployment modes.

## Top-level folder guide

- `onyx-main/`: upstream Onyx runtime code.
- `myStarterKit-maindashb-main/`: upstream governance/dashboard code.
- `integration-adapter/`: additive translation and evidence tooling.
- `docs/`: workspace architecture/provenance/compatibility/maturity/demo/testing docs.

## Upstream provenance and compatibility

- `docs/upstream-provenance.md`
- `docs/compatibility-matrix.md`
- `docs/maturity-model.md`

## Tests

### Integration adapter

```bash
cd integration-adapter
python -m pytest -q
```

### Starter Kit

```bash
cd myStarterKit-maindashb-main
pytest -q
```

### Onyx

Onyx has broader env/service requirements; see `onyx-main/AGENTS.md` and `onyx-main/README.md`.

## Evidence generation pipeline

```bash
cd integration-adapter
python -m integration_adapter.collect_from_onyx
python -m integration_adapter.generate_artifacts
python -m integration_adapter.run_launch_gate
```

Or:

```bash
make evidence
```

Demo mode:

```bash
cd integration-adapter
python -m integration_adapter.generate_artifacts --demo
```

Expected outputs under `artifacts/logs`:
- `audit.jsonl`
- `replay/*.replay.json`
- `evals/*.jsonl` and `evals/*.summary.json`
- `launch_gate/*.json` and `launch_gate/*.md`

> Launch-gate results here are **evidence-quality outputs**, not standalone proof of runtime control enforcement.

## End-to-end demo scenario

```bash
cd integration-adapter
python -m integration_adapter.demo_scenario
```

This generates demo artifacts, runs launch-gate, and verifies Starter Kit artifact readers can parse outputs.

See `docs/demo-scenario.md` for full steps and real-vs-synthetic labels.

## Testing blind spots

Known runtime assumptions that are not fully testable in this workspace are tracked in:
- `docs/testing-blind-spots.md`


## Final hardening review

- Current final hardening assessment, unresolved blockers, and prioritized next steps: `docs/final-hardening-review.md`.
