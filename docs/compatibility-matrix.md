# Compatibility Matrix

This matrix records tested/known compatibility points across the three planes.

## Matrix

| Runtime Plane | Governance Plane | Adapter Plane | Onyx Commit | Starter Kit Commit | Adapter Commit Basis | Status | Notes |
|---|---|---|---|---|---|---|---|
| `onyx-main/` | `myStarterKit-maindashb-main/` | `integration-adapter/` | UNCONFIRMED (no nested git metadata) | UNCONFIRMED (no nested git metadata) | workspace commit `a90fc07c966a38ed9d59395e4414bc093ec0b123` | Partial | Adapter contracts and artifact generation are implemented; live runtime hook pinning is still partially unconfirmed. |

## Compatibility notes

1. **Boundary model**
   - Compatibility is artifact-contract based, not direct runtime module coupling.
   - Adapter emits audit/inventory/eval/launch-gate artifacts that Starter Kit can consume.

2. **Current confirmed compatibility**
   - Adapter schema/mapping tests pass for normalized event vocabulary and artifact generation paths.
   - Launch-gate summary artifact shape generation is implemented in adapter writer.

3. **Current unconfirmed compatibility**
   - Canonical Onyx runtime hook sources for connector/tool/MCP/eval/event exporters are not fully pinned to upstream commits in this workspace.

4. **Upgrade guidance**
   - When updating Onyx or Starter Kit snapshots, refresh this matrix and `docs/upstream-provenance.md` with:
     - upstream remote URL,
     - exact upstream commit,
     - adapter validation test run results,
     - any contract deltas.

## Confirmation commands (to run when nested git metadata exists)

```bash
cd onyx-main && git remote -v && git rev-parse HEAD
cd ../myStarterKit-maindashb-main && git remote -v && git rev-parse HEAD
cd ../ && git rev-parse HEAD
```
