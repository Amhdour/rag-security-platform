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
