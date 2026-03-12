# Final Hardening Review (Surgical)

This review is scoped to repository integrity and explainability for AI Trust & Security readiness work.

## 1) Architecture integrity
- **Status:** Good with caveats.
- **Implemented:** clear three-plane separation (`onyx-main`, `integration-adapter`, `myStarterKit-maindashb-main`).
- **Risk:** some optional DB-backed adapter paths are runtime-environment dependent.

## 2) Coupling risk
- **Status:** Moderate, controlled.
- **Implemented:** artifact contract boundary and read-only dashboard ingestion.
- **Partially Implemented:** adapter optionally imports Onyx DB modules when available.
- **Hardening update:** demo scenario now cleans temporary `sys.path` insertion to reduce import side effects.

## 3) Provenance clarity
- **Status:** Partial.
- **Implemented:** provenance and compatibility docs exist.
- **Unconfirmed:** nested upstream git metadata unavailable in this workspace for complete commit pinning.

## 4) Exporter robustness
- **Status:** Moderate.
- **Implemented:** file-backed extraction, malformed input tolerance, safe fallback behavior.
- **Partially Implemented:** optional DB extraction guarded by try/fallback.
- **Risk:** broad exception handling hides exact runtime failures (intentional fail-soft behavior).

## 5) Schema drift risk
- **Status:** Moderate.
- **Implemented:** schema/event vocabulary tests and malformed input tests.
- **Risk:** live runtime payloads may evolve; adapter normalization may need versioned contracts.

## 6) Launch-gate honesty
- **Status:** Good.
- **Implemented:** evidence-quality checks with fail-closed semantics on missing/malformed artifacts.
- **Explicit limitation:** launch-gate output does not claim production enforcement proof.

## 7) Dashboard read-only integrity
- **Status:** Good.
- **Implemented:** GET-only API; mutating methods return 405.
- **Implemented:** localhost-safe default binding with explicit remote opt-in.

## 8) Demo reproducibility
- **Status:** Good.
- **Implemented:** deterministic demo CLI + smoke tests + expected artifact outputs.
- **Implemented:** real-vs-synthetic labeling in demo report.

## 9) Maintainability
- **Status:** Improving.
- **Implemented:** modular adapter commands and docs.
- **Risk:** growing docs need periodic claim-audit to avoid drift.

## 10) Next-step roadmap
See prioritized list below.

---

## Unresolved blockers

1. Upstream commit pinning for `onyx-main` and `myStarterKit-maindashb-main` cannot be fully verified from current checkout state (no nested `.git`).
2. Canonical production event/eval hook parity across all Onyx deployment modes remains unconfirmed.
3. Optional Onyx DB-backed exporter paths are not consistently runnable in all CI/test environments.

## Prioritized next 10 implementation steps

1. Add machine-readable provenance lock file (`docs/upstream-provenance.lock.json`) and populate once nested git metadata is available.
2. Add adapter input contract versioning for runtime payload shapes (e.g., `schema_version` field and compatibility checks).
3. Add exporter telemetry counters (read source, fallback mode, parse failures) in non-sensitive logs.
4. Add environment-gated integration tests for optional Onyx DB exporter paths.
5. Add contract tests against representative real Onyx artifacts captured from a pinned runtime version.
6. Add launch-gate check for artifact freshness windows (timestamp staleness thresholds).
7. Add explicit adapter release notes section documenting breaking/non-breaking mapping changes.
8. Add dashboard UI badge to highlight demo/synthetic evidence mode more prominently.
9. Add stricter static type checks for adapter modules in CI (e.g., mypy/pyright profile).
10. Add periodic doc claim-audit checklist in CI to ensure status labels remain aligned with implementation.
