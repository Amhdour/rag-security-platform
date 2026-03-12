# AGENTS.md — rag-security-platform-main

## Repository purpose
This repo is an **integration workspace** for three coordinated planes:
- `onyx-main/` (runtime execution)
- `integration-adapter/` (translation/artifact generation)
- `myStarterKit-maindashb-main/` (governance/evidence/read-only dashboard)

## Separation of concerns (must preserve)
- **Onyx**: request handling, retrieval, connectors, tools, MCP runtime behavior.
- **Integration adapter**: read/normalize/export artifacts only.
- **Starter Kit**: governance checks, evidence views, launch-gate, read-only observability.

## Non-invasive integration policy
- Prefer additive changes in `integration-adapter/`.
- Avoid invasive runtime rewrites when an adapter-side approach is feasible.
- Use artifact contracts (`audit.jsonl`, replay, eval, launch_gate) as integration boundary.

## No destructive merge rule
- Do **not** destructively merge upstream repos into one rewritten codebase.
- Keep upstream directories distinct and attributable.

## Dashboard read-only rule
- Dashboard/API must remain read-only.
- No mutating endpoints for policy/runtime/tool execution from dashboard paths.
- Preserve localhost-safe defaults unless explicitly requested otherwise.

## Honest-claims policy
- Never claim production security/enforcement guarantees not implemented and tested.
- Label status explicitly in docs/comments when relevant:
  - **Implemented**
  - **Partially Implemented**
  - **Demo-only**
  - **Unconfirmed**
  - **Planned**

## Testing expectations
- Run relevant fast tests after each major change.
- For adapter work, default to:
  - `cd integration-adapter && python -m pytest -q`
- For dashboard/observability changes, run targeted Starter Kit tests and broaden if needed.
- Prefer deterministic fixtures and fail-closed behavior tests for malformed/missing evidence.

## Documentation update expectations
- Update docs when behavior/contracts/status labels change.
- Keep README + adapter README + relevant docs in sync.
- Track known blind spots/unconfirmed assumptions in docs.

## Preferred execution order
1. Inspect existing code/docs/tests and identify real vs placeholder vs unconfirmed.
2. Implement smallest safe additive change.
3. Add/update tests.
4. Run validation commands.
5. Update docs/comments to match actual behavior.
6. Commit with focused scope.

## Marking unconfirmed runtime hooks
- Use explicit markers in code comments/docs, e.g.:
  - `Unconfirmed: canonical runtime hook not validated in this workspace.`
- Provide next-step verification command/path whenever possible.

## Coding style (adapter modules)
- Keep extraction, normalization, and writing concerns separate.
- Prefer small typed helpers and explicit defaults for missing fields.
- Handle malformed input defensively; fail closed for launch-gate/evidence integrity checks.
- Avoid hidden coupling to Onyx internals; if optional runtime imports are used, guard them and document fallback behavior.
