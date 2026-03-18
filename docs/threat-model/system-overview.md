# System overview

## Architecture view

This repository is a three-plane integration workspace:

1. **Runtime plane (`onyx-main/`)**
   - Executes RAG workflows and produces runtime events.
2. **Translation plane (`integration-adapter/`)**
   - Read-only extraction, normalization, and artifact generation.
3. **Governance plane (`myStarterKit-maindashb-main/`)**
   - Read-only observability and reviewer consumption of artifacts.

## Security-relevant data flow

1. Adapter collects runtime-adjacent inputs (live/db/file/fixture/synthetic modes).
2. Adapter normalizes events and inventories into contract-bound artifacts.
3. Launch gate evaluates artifact quality and control evidence with fail-closed checks.
4. Adversarial harness emits eval results and markdown/json evidence for reviewers.

## Source-of-truth controls

- **Implemented:** Artifact generation pipeline (`collect_from_onyx`, `generate_artifacts`, `run_launch_gate`).
- **Implemented:** Adversarial harness for prompt injection, retrieval poisoning, output leakage, policy bypass, and unsafe-tool attempts where detectable.
- **Implemented:** Control-matrix/evidence-report/launch-gate-bridge documentation outputs.
- **Unconfirmed:** Runtime hook parity for all deployment modes.
