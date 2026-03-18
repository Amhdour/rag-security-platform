# System Coherence: AI Trust & Security Readiness

## Purpose

**Implemented:** This document fixes repository-level ambiguity by defining exact cross-repo roles, naming, and artifact contracts.

## Canonical repository roles

1. **Implementation plane** — `myStarterKit`
   - **Implemented:** primary application behavior and control implementation.
2. **Evaluation + evidence plane** — `rag-security-platform` (this repository)
   - **Implemented:** evidence extraction, normalization, compatibility checks, and Launch Gate-ready artifacts.
3. **Observability/dashboard plane** — `myStarterKit-maindashb`
   - **Implemented:** read-only evidence/telemetry visualization.
4. **Presentation plane** — `website`
   - **Planned:** public-facing communication and status presentation (outside this workspace).

## Naming alignment used in this workspace

- **Implemented:** external system name: `myStarterKit-maindashb`.
- **Implemented:** local directory name in this workspace: `myStarterKit-maindashb-main/`.
- **Implemented:** all references in root docs now call out both names to avoid confusion.

## Integration points (artifact-first)

**Implemented:** this workspace aligns planes through artifacts, not direct runtime coupling.

### Producer (this repo)
- `integration-adapter` emits artifacts under:
  - `integration-adapter/artifacts/logs/audit.jsonl`
  - `integration-adapter/artifacts/logs/replay/`
  - `integration-adapter/artifacts/logs/evals/`
  - `integration-adapter/artifacts/logs/launch_gate/`

### Consumer alignment
- **Implemented:** dashboard/governance compatibility remains read-only and evidence-driven.
- **Unconfirmed:** canonical production hook parity across all runtime deployment modes is not fully validated in this workspace.

## Minimal structure convention (current)

- **Implemented:** keep additive integration changes centered in:
  - `integration-adapter/`
  - root automation (`Makefile`, `scripts/`)
  - root/system docs (`README.md`, `docs/`)
- **Implemented:** do not flatten or merge upstream repos into one runtime codebase.

## Verification commands for claim updates

Run these before broadening claim-bearing documentation:

- `python scripts/validate_upstream_provenance_lock.py`
- `cd integration-adapter && python -m pytest -q`
