# Artifact Retention and Cleanup Policy

**Implemented:** This policy defines profile-aware retention windows and cleanup behavior for adapter artifacts.

## Scope

The policy applies to artifacts under the adapter artifacts root (default `integration-adapter/artifacts/logs`).

**Implemented:** Cleanup is executed by:

```bash
cd integration-adapter
python -m integration_adapter.artifact_retention --dry-run
```

or destructive apply mode:

```bash
cd integration-adapter
python -m integration_adapter.artifact_retention --apply
```

## Safety guarantees

- **Implemented:** Default mode is dry-run; no files are deleted unless `--apply` is passed.
- **Implemented:** Required baseline artifacts are preserved:
  - `artifact_bundle.contract.json`
  - `artifact_integrity.manifest.json`
  - `audit.jsonl`
  - `connectors.inventory.json`
  - `tools.inventory.json`
  - `mcp_servers.inventory.json`
  - `evals.inventory.json`
  - `adapter_health/adapter_run_summary.json`
- **Implemented:** Files referenced by the current integrity manifest are preserved.
- **Implemented:** The latest successful launch-gate run(s) are preserved (`status in {go, conditional_go}`), configurable via `--keep-latest-successful-runs`.
- **Implemented:** Cleanup does not run automatically during artifact generation; operators run cleanup after validation and verification steps.

## Profile-aware retention windows

Retention windows are profile defaults and can be overridden by environment variables.

| Artifact family | demo | dev | ci | prod_like |
|---|---:|---:|---:|---:|
| audit logs | 2 days | 7 days | 1 day | 30 days |
| eval outputs (`evals/*.jsonl`, `evals/*.summary.json`) | 3 days | 14 days | 2 days | 30 days |
| launch-gate outputs (`launch_gate/security-readiness-*`) | 3 days | 14 days | 2 days | 90 days |
| adapter health summaries (`adapter_health/*.json`) | 3 days | 14 days | 2 days | 30 days |
| integrity manifests (`artifact_integrity*.json`) | 3 days | 14 days | 2 days | 30 days |

**Implemented:** Per-profile/per-family overrides use:

`INTEGRATION_ADAPTER_RETENTION_<PROFILE>_<FAMILY>_SECONDS`

Example:

```bash
export INTEGRATION_ADAPTER_RETENTION_CI_LAUNCH_GATE_OUTPUTS_SECONDS=3600
```

## Destructive behavior

**Implemented:** In `--apply` mode, files older than the profile TTL and not protected by preservation rules are deleted.

**Implemented:** Deletions are file-level only (no directory removal), and each deletion candidate is listed in structured JSON output.

## Example outputs

Dry-run example:

```json
{
  "profile": "ci",
  "dry_run": true,
  "candidate_count": 2,
  "deleted_count": 0,
  "candidates": [
    {
      "family": "launch_gate_outputs",
      "path": "artifacts/logs/launch_gate/security-readiness-20240101T000000Z.json",
      "reason": "expired ttl (172800s) for family=launch_gate_outputs"
    }
  ]
}
```

Apply example:

```json
{
  "profile": "ci",
  "dry_run": false,
  "candidate_count": 2,
  "deleted_count": 2
}
```

## Limitations

- **Partially Implemented:** Retention currently operates on file age and launch-gate status, not immutable run IDs across all artifact families.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.
