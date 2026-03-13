# Final Hardening Review (Implementation Maturity)

**Implemented:** This review is scoped to the current repository state and test-backed behavior in this workspace.

## Overall maturity estimate (strict)

- **Partially Implemented:** **7.8 / 10** production-readiness for the integration workspace as currently implemented.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.
- **Unconfirmed:** no cryptographic non-repudiation/signing chain for artifacts.

## 12-category status summary

### 1) Provenance completeness
- **Implemented:** Machine-readable upstream provenance lock exists (`docs/upstream-provenance.lock.json`) and shape validation is automated.
- **Partially Implemented:** Workspace-level tracking is clear; nested upstream pins remain conditional on nested git metadata availability.
- **Unconfirmed:** full upstream pin fidelity for all nested repos cannot be guaranteed in every checkout context.

### 2) Schema/version governance
- **Implemented:** Explicit source/normalized/artifact/launch-gate schema versions and compatibility policy (`allowed`, `warn_only`, `blocked`) are implemented.
- **Implemented:** Blocked version mismatches fail artifact generation.
- **Partially Implemented:** governance is enforced in adapter scope, but external consumers still require disciplined contract refresh cadence.

### 3) Exporter robustness
- **Implemented:** Source mode metadata, fallback diagnostics, malformed input handling, and partial-degradation surfacing are present.
- **Partially Implemented:** DB/runtime-backed extraction remains environment-dependent.
- **Unconfirmed:** deployment-wide exporter parity across all Onyx shapes is not validated here.

### 4) Runtime parity
- **Partially Implemented:** File/fixture/demo flows are highly test-covered.
- **Unconfirmed:** canonical runtime event/eval hook parity across deployment topologies is not proven in this workspace.

### 5) Operational telemetry
- **Implemented:** Adapter health summary includes source-mode counts, fallback usage, parse failures, schema failures, stale evidence detections, and launch-gate reasons.
- **Implemented:** run status classification (`success`, `degraded_success`, `failed_run`) is explicit.

### 6) Freshness-aware launch gating
- **Implemented:** Critical evidence freshness is fail-closed; warning-tier freshness degradation is explicitly separated.
- **Implemented:** Profile defaults apply freshness thresholds automatically.

### 7) Identity/authz evidence quality
- **Implemented:** Identity/authz/delegation fields and per-field provenance markers (`sourced`, `derived`, `unavailable`) are mapped and validated.
- **Implemented:** Launch-gate has presence + provenance-quality checks with PASS/WARN/FAIL semantics.

### 8) Contract fixture realism
- **Implemented:** Contract fixtures cover connector/tool/MCP/eval/runtime-event families with lineage/sanitization metadata.
- **Partially Implemented:** fixtures are real-derived and sanitized, but still snapshots and not continuous live parity proof.

### 9) Packaging and execution reproducibility
- **Implemented:** CLI entrypoints, Make targets, config validation, profile controls, and CI-friendly smoke command exist and are tested.
- **Implemented:** commands are copy-paste operational in docs.

### 10) Negative-path behavior
- **Implemented:** Deterministic tests cover malformed sources, incompatible versions, stale critical evidence, missing identity/authz evidence, missing MCP classification, partial exporter failure signals, artifact write failure, prod_like synthetic blocking, and fail-closed gate behavior.

### 11) Artifact integrity
- **Implemented:** Integrity manifest with SHA-256 and required-file verification exists and is integrated into launch-gate (`artifact_integrity_manifest` fail-closed check).
- **Partially Implemented:** tampering detection is consistency/hash-based and practical.
- **Unconfirmed:** no signature-based non-repudiation/attestation chain.

### 12) Documentation honesty
- **Implemented:** status labels are widely used and docs now include explicit commands/outputs/failure semantics.
- **Partially Implemented:** doc precision is strong for adapter scope; runtime parity claims remain appropriately constrained.

## What reached production-oriented quality

1. **Implemented:** deterministic adapter execution + verification flow (`validate_config` -> `generate_artifacts` -> `run_launch_gate` -> `verify_artifact_integrity`).
2. **Implemented:** fail-closed behavior for critical schema/freshness/integrity checks.
3. **Implemented:** operational telemetry sufficient for degraded-run diagnosis.
4. **Implemented:** profile-driven safeguards including strict `prod_like` blocking logic.
5. **Implemented:** negative-path test depth that exceeds happy-path-only confidence.

## What still prevents true 9/10

1. **Unconfirmed:** canonical runtime hook not validated in this workspace.
2. **Unconfirmed:** no cryptographic signing/attestation for artifact non-repudiation.
3. **Partially Implemented:** exporter live/db parity is best-effort and environment dependent.
4. **Partially Implemented:** upstream pinning for nested repos depends on checkout metadata availability.

## Top remaining blockers

1. **Unconfirmed:** deployment-validated runtime parity matrix across Onyx runtime modes.
2. **Unconfirmed:** signature/attestation-based artifact integrity beyond hash consistency.
3. **Partially Implemented:** routine upstream refresh automation that enforces provenance+compatibility update discipline.

## Next 10 implementation steps (strict priority)

1. **Planned:** Add signed artifact attestations (manifest signature + verifier).
2. **Planned:** Add CI job for profile matrix (`demo`, `dev`, `ci`, `prod_like`) with expected pass/fail assertions.
3. **Planned:** Add runtime-parity integration harness against a controlled Onyx runtime fixture service.
4. **Planned:** Add automated freshness regression tests with explicit artifact age simulation across families.
5. **Planned:** Add stricter launch-gate check for MCP classification completeness thresholds by profile.
6. **Planned:** Add upstream-lock refresh helper script to reduce manual provenance drift.
7. **Planned:** Add contract fixture regeneration tooling with sanitizer pipeline and deterministic snapshot diff checks.
8. **Planned:** Add structured exporter error taxonomy codes (not only strings) for better ops analytics.
9. **Planned:** Add release checklist automation enforcing `provenance-check`, `adapter-ci`, and integrity verification.
10. **Planned:** Add blind-spot report generation from test metadata to keep `Unconfirmed` claims synchronized.
