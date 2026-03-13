# Final Hardening Review (Surgical)

**Implemented:** This review is scoped to repository integrity and explainability for AI Trust & Security readiness work in this workspace.

## 1) Architecture integrity
- **Implemented:** Three-plane separation is preserved (`onyx-main`, `integration-adapter`, `myStarterKit-maindashb-main`).
- **Partially Implemented:** Runtime-linked adapter behavior still depends on optional environment-backed hooks.
- **Unconfirmed:** Deployment-wide parity of all runtime hooks is not validated in this workspace.

## 2) Coupling risk
- **Implemented:** Artifact contracts remain the integration boundary and dashboard ingestion remains read-only.
- **Partially Implemented:** Adapter includes optional imports of Onyx runtime modules for best-effort extraction.
- **Unconfirmed:** Optional runtime imports can still vary by deployment shape and package layout.

## 3) Provenance clarity
- **Implemented:** Provenance and compatibility docs exist and are linked from root docs.
- **Partially Implemented:** Claim/status labeling is now explicit across major docs and adapter comments.
- **Unconfirmed:** Full upstream commit pinning cannot be completed from this workspace checkout alone.

## 4) Exporter robustness
- **Implemented:** File-backed reads, malformed-input tolerance, and defensive fallbacks are in place.
- **Partially Implemented:** DB-backed reads are best-effort and guarded by fallback behavior.
- **Unconfirmed:** Canonical runtime hook fidelity for all exporter domains is not fully verified in CI.

## 5) Schema drift risk
- **Implemented:** Schema validation and malformed/missing input tests are present.
- **Partially Implemented:** Drift detection is reactive (tests/contracts) rather than explicit version negotiation.
- **Planned:** Add schema/version contracts and compatibility checks for upstream payload evolution.

## 6) Launch-gate honesty
- **Implemented:** Launch-gate checks evidence quality/completeness and fails closed on malformed evidence.
- **Implemented:** Machine output separates blockers vs warnings and evidence present vs incomplete.
- **Unconfirmed:** Launch-gate output is not standalone proof of production runtime control enforcement.

## 7) Dashboard read-only integrity
- **Implemented:** Dashboard APIs remain read-only (mutating methods rejected).
- **Implemented:** Localhost-safe defaults are preserved with explicit remote opt-in.
- **Partially Implemented:** Cross-root artifact compatibility is test-backed for current artifact shapes, but future shape drift still requires ongoing coverage.

## 8) Demo reproducibility
- **Implemented:** Reproducible demo command path and deterministic artifact generation flow exist.
- **Partially Implemented:** Demo uses synthetic fallback evidence when live runtime data is unavailable.
- **Unconfirmed:** Demo realism does not guarantee production runtime parity.

## 9) Maintainability
- **Implemented:** Pipeline entrypoints are modular and test-covered across unit/integration-style boundaries.
- **Partially Implemented:** Documentation and claim audits are improved but require recurring maintenance to avoid drift.
- **Planned:** Automate claim-audit and compatibility checks in CI.

## 10) Next-step roadmap
- **Implemented:** Priority roadmap is defined below.
- **Planned:** Execute roadmap in small additive changes with test-first validation.

---

## Unresolved blockers

1. **Unconfirmed:** Upstream commit pinning for `onyx-main` and `myStarterKit-maindashb-main` is incomplete because nested `.git` metadata is not fully available in this workspace.
2. **Unconfirmed:** Canonical production event/eval/runtime-hook parity across all Onyx deployment modes is not yet validated.
3. **Partially Implemented:** Optional Onyx DB-backed exporter paths are not consistently runnable in all CI environments.

## Prioritized top 10 next implementation steps

1. **Planned:** Add machine-readable provenance lock file (`docs/upstream-provenance.lock.json`) and populate when nested git metadata is available.
2. **Planned:** Add adapter input contract versioning (`schema_version`) with explicit compatibility checks.
3. **Planned:** Add exporter telemetry counters (selected source, fallback mode, parse/validation failures) in non-sensitive logs.
4. **Planned:** Add environment-gated integration tests for optional Onyx DB exporter paths.
5. **Planned:** Add contract tests against pinned real Onyx artifact fixtures.
6. **Planned:** Add launch-gate artifact freshness checks (timestamp staleness thresholds).
7. **Planned:** Add adapter release-notes section for mapping/schema compatibility changes.
8. **Planned:** Add dashboard UX indicator for demo/synthetic evidence mode.
9. **Planned:** Add stricter static typing checks for adapter modules in CI.
10. **Planned:** Add periodic doc claim-audit automation in CI to keep status labels aligned with implementation.
