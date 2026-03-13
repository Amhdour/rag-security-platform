# launch_gate/

**Implemented:** Evidence-driven release-readiness checks for support-agent launches, based on available artifacts in this workspace.

**Implemented:** The launch gate evaluates launch status using artifact files (not inferred assumptions).
- **Implemented:** Policy artifact existence, parsing, and schema checks.
- **Implemented:** Retrieval boundary configuration presence checks (tenant/source allowlists and trust/provenance fields).
- **Partially Implemented:** Tool-router enforcement is inferred from required eval scenario outcomes in aligned eval summary+jsonl runs.
- **Implemented:** Telemetry evidence presence checks for required audit event types and lifecycle identity fields.
- **Implemented:** Replay evidence checks (when required) for replay schema and request lifecycle coverage.
- **Implemented:** Eval summary threshold checks and consistency checks against eval jsonl scenario rows.
- **Partially Implemented:** Eval runtime-realism checks rely on reported fields (for example `mocked=false` and required runtime components).
- **Partially Implemented:** Fallback readiness checks require policy + eval evidence but do not prove production runtime behavior.
- **Partially Implemented:** Kill-switch readiness checks depend on policy/evidence artifacts and deployment attestations.
- **Partially Implemented:** IAM integration readiness checks depend on module/docs/tests/eval evidence.
- **Partially Implemented:** Secrets-manager readiness checks depend on provider abstraction + startup policy/docs evidence.
- **Implemented:** Adversarial-eval coverage checks use scenario definitions and eval outcomes.
- **Partially Implemented:** Infrastructure boundary/deployment architecture checks are artifact-backed and may require external attestation.
- **Implemented:** Production deployment attestation is evaluated separately from framework/example readiness.
  - **Implemented:** Attestation must include explicit `verified_controls`, `residual_risks`, and `deferred_true_production_operations` sections.

Status semantics:
- **Implemented:** `go` = no blockers and no residual risks.
- **Implemented:** `conditional_go` = no blockers, but residual risks remain.
- **Implemented:** `no_go` = one or more blocker checks failed.

Run:

```bash
python -m launch_gate.engine
```

**Implemented:** Reproducible evidence workflow (clean-state regeneration of eval/replay/verification/launch-gate outputs):

```bash
./scripts/regenerate_core_evidence.sh
```


Extended summary fields:
- **Implemented:** `framework_complete` = core framework-level controls are complete.
- **Partially Implemented:** `production_example_ready` = production-realism example domains are evidenced in-repo.
- **Partially Implemented:** `production_deployment_ready` = external deployment attestation evidence is present (separate from framework/example readiness).

**Unconfirmed:** launch-gate outputs in this workspace do not independently prove production runtime enforcement without external runtime validation.
