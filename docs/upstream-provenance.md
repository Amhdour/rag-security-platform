# Upstream Provenance and Pinning

**Implemented:** This workspace keeps upstream provenance in a machine-readable lock file at `docs/upstream-provenance.lock.json`.

## Why this exists

**Implemented:** The lock file makes integration targets explicit across three planes without flattening upstream repositories.

**Partially Implemented:** Full upstream commit pinning is currently available only for the workspace-tracked adapter plane; runtime and dashboard plane pins remain unavailable in this checkout.

## Lock file contract

`docs/upstream-provenance.lock.json` includes:

- `lock_version`
- `workspace` metadata (`repository`, `tracked_at_workspace_commit`)
- `components[]`, each with:
  - `component_id`
  - `local_path`
  - `role`
  - `upstream` (`repo_name`, `expected_remote_url`, `expected_ref`, `pinned_commit`, `pin_status`)
  - `local_snapshot` (`git_metadata_available`, `snapshot_status`, `unavailable_reason`, `verification_commands`, `maintainer_todo`)

## Current confirmation status

### 1) Onyx runtime plane (`onyx-main/`)

- **Partially Implemented:** Upstream repo name and expected remote URL are recorded.
- **Unconfirmed:** Pinned upstream commit hash is unavailable in this workspace.
- **Unconfirmed:** Branch/tag is recorded as expected `main` and must be verified from nested git metadata.

Unconfirmed: canonical runtime hook not validated in this workspace.

### 2) Starter Kit governance plane (`myStarterKit-maindashb-main/`)

- **Partially Implemented:** Local snapshot identity is recorded and linked to this plane.
- **Unconfirmed:** Canonical upstream remote URL, branch/tag, and pinned commit are unavailable in this workspace.

### 3) Integration adapter plane (`integration-adapter/`)

- **Implemented:** Pinned commit is tracked via workspace root git commit in lock metadata.
- **Implemented:** Verification command is documented.

## Why some fields are unavailable

**Unconfirmed:** `onyx-main/` and `myStarterKit-maindashb-main/` are present as local snapshots without nested `.git` metadata in this checkout.

Because nested metadata is missing, this workspace cannot truthfully resolve:

- upstream remote URL (for Starter Kit),
- active branch/tag,
- exact upstream commit hash.

## Regeneration and verification workflow

Run these commands when nested git metadata is present:

```bash
cd onyx-main && git remote -v && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD
cd ../myStarterKit-maindashb-main && git remote -v && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD
cd ../ && git rev-parse HEAD
```

Then update `docs/upstream-provenance.lock.json`:

1. Replace `upstream.expected_remote_url` with confirmed remote URL.
2. Replace `upstream.expected_ref` with confirmed branch or tag.
3. Replace `upstream.pinned_commit` with verified commit hash.
4. Change `upstream.pin_status` from `UNCONFIRMED` to `IMPLEMENTED` only after verification.
5. Update `workspace.tracked_at_workspace_commit` to current workspace commit.

## Validation command

**Implemented:** Validate the lock shape and required fields with:

```bash
python scripts/validate_upstream_provenance_lock.py
```

Or via make target:

```bash
make provenance-check
```

## Maintainer TODOs

- **Planned:** Enable nested git metadata capture during upstream snapshot refreshes.
- **Planned:** Require provenance lock validation in CI for every integration release.
- **Planned:** Add automated diff checks between lock contents and compatibility matrix references.


## Update procedure (operational)

1. Refresh upstream snapshots.
2. Capture nested git metadata (when available):

```bash
cd onyx-main && git remote -v && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD
cd ../myStarterKit-maindashb-main && git remote -v && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD
cd ../
```

3. Update `docs/upstream-provenance.lock.json` fields (`expected_remote_url`, `expected_ref`, `pinned_commit`, `pin_status`).
4. Validate lock shape:

```bash
make provenance-check
```

Failure condition:
- **Implemented:** validator exits non-zero when required fields/shape are missing or invalid.
