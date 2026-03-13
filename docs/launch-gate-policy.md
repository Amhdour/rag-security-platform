# Launch-Gate Evidence Quality Policy

This policy defines adapter launch-gate decisions based on evidence quality, freshness, compatibility, and degradation signals.

## Scope and limitations

- **Implemented:** Launch-gate evaluates artifacts and telemetry quality for integration readiness.
- **Implemented:** Launch-gate emits machine-readable and human-readable results.
- **Unconfirmed:** Launch-gate does not prove production runtime control enforcement.

## PASS / WARN / FAIL model

### PASS
All quality checks pass and no blocker evidence exists.

### WARN (residual risk)
Evidence is present but degraded, such as:

- source-mode quality indicates fixture/synthetic evidence,
- exporter degradation signals are non-zero,
- non-critical artifact freshness staleness,
- partial threat-control mapping gaps.

### FAIL (blocker)
Fail-closed conditions include:

- missing or stale **critical** evidence families,
- incompatible contract versions (blocked),
- malformed critical artifacts,
- severe identity/authz evidence absence,
- critical/high eval failures,
- adapter health status `failed_run`.

## Freshness policy

Critical evidence (fail when stale/missing):

- `artifact_bundle.contract.json`
- `audit.jsonl`
- `evals/*.summary.json`

Warning-level freshness (warn when stale):

- inventory snapshots
- adapter health summary

Thresholds:

- `INTEGRATION_ADAPTER_MAX_CRITICAL_EVIDENCE_AGE_SECONDS` (default: `86400`)
- `INTEGRATION_ADAPTER_MAX_WARNING_EVIDENCE_AGE_SECONDS` (default: `172800`)

## Quality checks covered

- artifact freshness / staleness
- version compatibility
- source-mode quality
- exporter degradation
- identity/authz evidence presence
- threat-control-evidence mapping completeness
- critical artifact absence vs warning-level degradation

## Demo-only evidence handling

- **Implemented:** Synthetic/fixture-heavy source modes are surfaced as quality degradation signals.
- **Demo-only:** Demo runs can still be useful for integration checks but are not proof of production enforcement.

## Outputs

- Machine-readable: `launch_gate/security-readiness-<STAMP>.json`
- Human-readable: `launch_gate/security-readiness-<STAMP>.md`

Both include blockers and residual risks with explicit reasons.


## Identity/authz provenance quality

- **Implemented:** Launch-gate includes `identity_authz_provenance_quality` to evaluate per-field provenance quality (`sourced`, `derived`, `unavailable`).
- **Implemented:** Critical provenance fields (`actor_id`, `tenant_id`, `session_id`, `decision_basis`, `resource_scope`, `authz_result`) failing availability thresholds produce FAIL.
- **Implemented:** Derived-only critical evidence is warning-level unless critical-unavailable thresholds are exceeded.


## Evidence tampering signal checks

- **Implemented:** Launch-gate includes `evidence_tampering_signals` consistency checks between `artifact_bundle.contract.json` and `audit.jsonl` schema-version stamps.
- **Implemented:** Contract/audit mismatch is fail-closed.
- **Unconfirmed:** no cryptographic signing/attestation is implemented in this workspace.


## Artifact integrity manifest checks

- **Implemented:** Launch-gate includes `artifact_integrity_manifest` and fail-closes on missing required files, missing manifest entries, or hash mismatches.
- **Implemented:** Hash verification is SHA-256 consistency checking against `artifact_integrity.manifest.json`.
- **Unconfirmed:** this is not cryptographic non-repudiation or signed attestation.


## Operations commands

Run gate with profile defaults:

```bash
cd integration-adapter
python -m integration_adapter.run_launch_gate --profile demo --artifacts-root artifacts/logs
```

Freshness policy inputs:
- **Implemented:** `INTEGRATION_ADAPTER_MAX_CRITICAL_EVIDENCE_AGE_SECONDS`
- **Implemented:** `INTEGRATION_ADAPTER_MAX_WARNING_EVIDENCE_AGE_SECONDS`
- **Implemented:** profile defaults are auto-applied when env vars are not explicitly set.

Critical fail-closed examples:
- **Implemented:** missing or stale `artifact_bundle.contract.json` / `audit.jsonl` / eval summary.
- **Implemented:** integrity manifest verification failure.
- **Implemented:** artifact contract incompatibility.

Warning-level degradation examples:
- **Implemented:** fixture/synthetic source mode quality signals.
- **Implemented:** partial identity/authz provenance quality.
- **Implemented:** partial threat-control mapping completeness.
