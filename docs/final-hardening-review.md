# Final Hardening Review (Implementation Maturity)

**Implemented:** This review is scoped to repository code, workflows, tests, and docs currently present in this workspace.

## Overall maturity estimate (strict)

- **Partially Implemented:** **8.3 / 10** production-readiness for the integration workspace.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.
- **Unconfirmed:** no asymmetric signature/attestation non-repudiation chain is implemented in this workspace.

## Category review (strict, evidence-based)

### 1) CI/CD completeness
- **Implemented:** Root CI workflow executes provenance validation, adapter tests, CI smoke, artifact regeneration, and integrity verification on push/PR.
- **Partially Implemented:** CI is deterministic for adapter scope, but no deployment-runtime parity job exists yet.

### 2) Artifact retention and cleanup safety
- **Implemented:** Profile-aware retention windows, dry-run default, explicit `--apply` mode, and preservation safeguards for required files + latest successful Launch Gate runs.
- **Implemented:** Retention outcomes are persisted into adapter health artifacts for operator traceability.

### 3) Runtime extraction strength and parity
- **Implemented:** Exporters include explicit source precedence (`live` > `service_api` > `db_backed` > `file_backed` > `fixture_backed` > `synthetic`) and explicit fallback metadata.
- **Partially Implemented:** Optional live/service/db adapters exist for all major domains.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.

### 4) Artifact integrity strength
- **Implemented:** Hash-based manifest verification is fail-closed in both verifier and Launch Gate.
- **Partially Implemented:** Optional signed-manifest mode (HMAC-SHA256) is implemented and tested.
- **Unconfirmed:** no asymmetric key signatures, transparency log, or external attestation chain.

### 5) Operator observability
- **Implemented:** Adapter health artifacts expose source modes, fallback counts, parse/validation failures, Launch Gate outcomes, freshness, integrity, and retention outcomes.
- **Implemented:** Operator health CLI supports `json`, `text`, and metrics-style outputs for low-noise triage.

### 6) Documentation honesty
- **Implemented:** Status labels are applied and major claims remain scoped to tested workspace behavior.
- **Partially Implemented:** Some docs still depend on deployment-specific verification for stronger claims.

### 7) Maintainability
- **Implemented:** Tooling is CLI-first, test-covered, and wired into CI and Make targets.
- **Partially Implemented:** Increasing feature surface (integrity/retention/health/exporter modes) raises complexity and benefits from stronger module-level contracts.

### 8) Remaining blockers (strict)
1. **Unconfirmed:** deployment-validated runtime parity matrix across Onyx deployment topologies.
2. **Unconfirmed:** non-repudiation-grade asymmetric signing + provenance attestation flow.
3. **Partially Implemented:** CI does not yet include multi-profile policy assertions beyond current smoke path.

## What is now production-oriented

1. **Implemented:** deterministic adapter CI pipeline with provenance + tests + smoke + integrity verification.
2. **Implemented:** fail-closed integrity + Launch Gate behavior for missing/tampered critical artifacts.
3. **Implemented:** safe retention lifecycle management with destructive action explicit and reviewable.
4. **Implemented:** operator-focused health reporting suitable for troubleshooting degraded runs.
5. **Implemented:** explicit fallback/source metadata across exporters to avoid hidden degradation.

## What still prevents 9/10

1. **Unconfirmed:** canonical runtime hook not validated in this workspace.
2. **Unconfirmed:** no asymmetric signature/attestation chain for stronger trust transfer.
3. **Partially Implemented:** CI/runtime verification remains workspace-centric rather than deployment-matrix validated.

## Next 5 implementation steps (strict priority)

1. **Planned:** Add deployment-parity integration harness against controlled Onyx runtime services (per-domain pass/fail matrix).
2. **Planned:** Add asymmetric signature verification mode (e.g., detached signature/certificate path) while retaining optionality.
3. **Planned:** Add CI profile matrix assertions (`demo`, `dev`, `ci`, `prod_like`) with expected pass/fail outcomes.
4. **Planned:** Add health report regression snapshots to catch telemetry schema drift in CI.
5. **Planned:** Add run-id-linked bundle manifest family to strengthen cross-artifact correlation and retention semantics.
