# Upstream Provenance and Pinning

This workspace assembles multiple upstream codebases without merging them into a single rewritten codebase.

## Integration-workspace repository

- Workspace repo: `rag-security-platform-main` (current local checkout)
- Current workspace commit (discoverable locally):
  - `a90fc07c966a38ed9d59395e4414bc093ec0b123`

Command used:

```bash
git rev-parse HEAD
```

## Upstream components

### 1) Onyx runtime plane

- Local path: `onyx-main/`
- Upstream project name (inferred from README): `onyx` (Onyx by onyx-dot-app)
- Expected upstream URL (discoverable from README links):
  - `https://github.com/onyx-dot-app/onyx`
- Pinned upstream commit hash: **UNCONFIRMED in this workspace**
  - Reason: `onyx-main/` is not a nested git repository in this checkout.

To obtain and pin from a clone with git metadata:

```bash
cd onyx-main
git remote -v
git rev-parse HEAD
```

### 2) Starter Kit governance plane

- Local path: `myStarterKit-maindashb-main/`
- Upstream project name: **UNCONFIRMED from current files**
  - Current folder naming suggests an internal/custom Starter Kit variant.
- Expected upstream URL: **UNCONFIRMED in this workspace**
- Pinned upstream commit hash: **UNCONFIRMED in this workspace**
  - Reason: `myStarterKit-maindashb-main/` is not a nested git repository in this checkout.

To obtain and pin from source with git metadata:

```bash
cd myStarterKit-maindashb-main
git remote -v
git rev-parse HEAD
```

### 3) Integration adapter translation plane

- Local path: `integration-adapter/`
- Upstream project name: workspace-local adapter module
- Expected upstream URL: not required (currently maintained within this integration workspace)
- Pinned commit hash: tracked via workspace root git commit.

## Pinning policy (recommended)

For each integration release, maintain a provenance table with:

- `component_name`
- `local_path`
- `upstream_url`
- `upstream_commit`
- `import_or_sync_date`
- `notes`

Suggested machine-readable companion file (future): `docs/upstream-provenance.lock.json`.

## Current provenance limitations

- Nested upstream `.git/` metadata is absent in this workspace, so direct upstream commit verification is not currently possible for `onyx-main/` and `myStarterKit-maindashb-main`.
- This document therefore includes explicit TODO-style confirmation commands instead of unverifiable claims.
