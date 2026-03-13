# Compatibility Matrix

This matrix records tested/known compatibility points across the three planes.

## Matrix

| Runtime Plane | Governance Plane | Adapter Plane | Onyx Remote | Onyx Ref | Onyx Commit | Starter Kit Remote | Starter Kit Ref | Starter Kit Commit | Adapter Commit Basis | Provenance Lock Status | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `onyx-main/` | `myStarterKit-maindashb-main/` | `integration-adapter/` | `https://github.com/onyx-dot-app/onyx` | `main` (expected) | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | workspace commit `a90fc07c966a38ed9d59395e4414bc093ec0b123` | `docs/upstream-provenance.lock.json` (validated shape) | Partial | **Partially Implemented:** Artifact contract compatibility is tested. **Unconfirmed:** Runtime/governance upstream commit pinning remains incomplete due to missing nested git metadata. |

## Compatibility notes

1. **Boundary model**
   - **Implemented:** Compatibility is artifact-contract based, not direct runtime module coupling.
   - **Implemented:** Adapter emits audit/inventory/eval/launch-gate artifacts for governance ingestion.

2. **Current confirmed compatibility**
   - **Implemented:** Adapter schema/mapping tests validate normalized event vocabulary and artifact generation paths.
   - **Implemented:** Launch-gate summary artifact shape generation is implemented in adapter writer.

3. **Current unconfirmed compatibility**
   - **Unconfirmed:** Canonical Onyx runtime hook sources for connector/tool/MCP/eval/event exporters are not fully pinned to upstream commits in this workspace.
   - **Unconfirmed:** Starter Kit canonical upstream remote/ref/commit cannot be verified without nested git metadata.

4. **Provenance update dependency**
   - **Implemented:** This matrix must be synchronized with `docs/upstream-provenance.lock.json`.
   - **Planned:** Add CI automation to verify lock/matrix consistency.

## Upgrade and refresh procedure

When refreshing `onyx-main/` or `myStarterKit-maindashb-main` snapshots:

1. Verify upstream metadata from nested repositories:
   ```bash
   cd onyx-main && git remote -v && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD
   cd ../myStarterKit-maindashb-main && git remote -v && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD
   ```
2. Update `docs/upstream-provenance.lock.json` with confirmed remote/ref/commit values.
3. Run lock validation:
   ```bash
   python scripts/validate_upstream_provenance_lock.py
   ```
4. Run adapter validation tests:
   ```bash
   cd integration-adapter && python -m pytest -q
   ```
5. Update this matrix row to match lock values and include test run evidence in PR notes.
