# AGENTS.md — rag-security-platform-main

## Mission (workspace-level)
Keep this repository a **three-plane integration workspace**:
- `onyx-main/` = runtime execution
- `integration-adapter/` = read/normalize/export artifacts
- `myStarterKit-maindashb-main/` = governance + read-only observability

## Non-negotiable rules
1. **Additive integration only.** Prefer changes in `integration-adapter/`, root docs, and root automation files.
2. **No destructive merges.** Do not rewrite/flatten upstream repos into one combined codebase.
3. **Dashboard stays read-only.** No mutating endpoints/behaviors in dashboard/observability paths.
4. **Artifact boundary first.** Integrate planes through artifacts (`audit.jsonl`, replay, eval, launch_gate), not runtime coupling.

## Claims & status labels (required)
- Never claim production security/enforcement unless implemented **and tested**.
- Label claim-bearing docs/comments with one of:
  - **Implemented**
  - **Partially Implemented**
  - **Demo-only**
  - **Unconfirmed**
  - **Planned**

## When to mark `Unconfirmed`
Mark as **Unconfirmed** when any of these are true:
- Hook/path is inferred but not validated in this workspace.
- Behavior depends on environment/runtime services not exercised in tests.
- Claim needs deployment-specific verification.

Use explicit wording where relevant:
`Unconfirmed: canonical runtime hook not validated in this workspace.`

## Exporter workflow (adapter)
1. Inspect real Onyx models/configs/fixtures first.
2. Implement smallest read-only extractor.
3. Keep extraction, translation, and writing separate.
4. Add schema validation + malformed/missing input handling.
5. Add deterministic tests before broad doc claims.

## CI + review guardrails (Codex/GitHub)
- Before updating claim-bearing docs, run at minimum:
  - `python scripts/validate_upstream_provenance_lock.py`
  - `cd integration-adapter && python -m pytest -q`
- For release-quality verification (same path as CI), run:
  - `make adapter-ci`
  - `cd integration-adapter && python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs-ci-smoke`
- In code review, verify these are true in changed outputs/artifacts:
  1. source-mode + fallback metadata remains explicit,
  2. schema/version compatibility checks still fail-closed on blocked mismatches,
  3. launch-gate still fails on integrity failures and critical evidence failures,
  4. integrity verification failures are treated as blockers (not warnings).
- If CI fails, first reproduce locally with:
  - `make adapter-ci`
  - then the failing step command from `.github/workflows/ci.yml`.
- Do not merge with unresolved regressions in integrity, schema compatibility, or launch-gate critical checks.

## Test-before-claim rule
- Run relevant tests **before** updating docs/claims.
- Minimum for adapter changes:
  - `cd integration-adapter && python -m pytest -q`
- For dashboard/observability changes, run targeted Starter Kit tests and broaden as needed.

## Demo data labeling
- Demo/synthetic evidence must be explicitly labeled **Demo-only** in reports/docs.
- Do not present demo outputs as proof of production enforcement.

## Documentation sync after code changes
When behavior/contracts/status change, update:
- root `README.md`
- `integration-adapter/README.md`
- relevant docs under `docs/` (e.g., threat model, demo, blind spots, hardening review)
