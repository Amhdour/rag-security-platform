# End-to-end secure RAG pipeline walkthrough (repository-scoped)

This walkthrough explains how the repository models a secure RAG pipeline through adapter artifacts and checks.

> Scope note: this is an integration-workspace walkthrough, not a claim of full production runtime enforcement.

## Stage map

1. Document ingestion
2. Retrieval
3. Context assembly
4. Model generation
5. Tool use (if applicable)
6. Output validation
7. Logging and audit

## Stage-by-stage control walkthrough

| Stage | Risk | Control (repo source of truth) | Implementation location | Evidence artifact |
|---|---|---|---|---|
| Document ingestion | Malformed/untrusted source payloads or silent fallback can contaminate downstream evidence | Source-mode metadata + read-only exporters + schema normalization checks | `integration-adapter/integration_adapter/exporters.py`, `integration-adapter/integration_adapter/raw_sources.py`, `integration-adapter/integration_adapter/mappers.py` | `artifacts/logs/adapter_health/adapter_run_summary.json`, `artifacts/logs/artifact_bundle.contract.json` |
| Retrieval | Poisoned or policy-conflicting retrieved content influences decisions | Retrieval decision normalization + adversarial retrieval-poisoning scoring | `integration-adapter/integration_adapter/translators.py` (`translate_retrieval_events`), `integration-adapter/integration_adapter/adversarial_harness.py` | `artifacts/logs/audit.jsonl` (`retrieval.decision`), `artifacts/logs/evals/adversarial-results.jsonl` |
| Context assembly | Context conflict/override instructions carried into answer path | Poisoned-context scenario checks and explicit deny expectations in scenario packs | `integration-adapter/integration_adapter/adversarial_harness.py`, `integration-adapter/tests/fixtures/adversarial/retrieval_poisoning/scenarios.json` | `artifacts/logs/evals/adversarial-summary.json`, `artifacts/logs/evals/adversarial-results.jsonl` |
| Model generation | Unsafe response content or policy-conflicting answer generation | Unsafe-output scenarios (sensitive disclosure, policy conflict, context carry-through leakage) | `integration-adapter/integration_adapter/adversarial_harness.py`, `integration-adapter/tests/fixtures/adversarial/output_leakage/scenarios.json` | `artifacts/logs/evals/adversarial-results.jsonl`, `artifacts/logs/evals/adversarial-report.md` |
| Tool use (if applicable) | High-risk tool invocation without adequate gating/authorization evidence | Tool decision normalization + unsafe-tool scenario scoring (`warn` when tools absent, `fail` when unsafe allow) | `integration-adapter/integration_adapter/translators.py` (`translate_tool_decisions`), `integration-adapter/integration_adapter/adversarial_harness.py` | `artifacts/logs/audit.jsonl` (`tool.decision`, `confirmation.required`, `tool.execution_attempt`), `artifacts/logs/tools.inventory.json` |
| Output validation | Artifacts exist but fail quality/integrity/freshness requirements | Launch Gate fail-closed checks (critical evidence, compatibility, integrity, severity blockers) | `integration-adapter/integration_adapter/launch_gate_evaluator.py`, `integration-adapter/integration_adapter/verify_artifact_integrity.py` | `artifacts/logs/launch_gate/security-readiness-<STAMP>.json`, `artifacts/logs/artifact_integrity.manifest.json` |
| Logging / audit | Missing or low-provenance evidence weakens attribution and review trust | Normalized audit schema + identity/authz field provenance + required lifecycle checks | `integration-adapter/integration_adapter/schemas.py`, `integration-adapter/integration_adapter/mappers.py`, `integration-adapter/integration_adapter/pipeline.py` | `artifacts/logs/audit.jsonl`, `artifacts/logs/launch_gate/security-readiness-<STAMP>.json` |

## Practical command flow

```bash
cd integration-adapter
python -m integration_adapter.generate_artifacts --demo --profile demo --artifacts-root artifacts/logs
python -m integration_adapter.adversarial_harness --artifacts-root artifacts/logs --demo
python -m integration_adapter.run_launch_gate --profile demo --artifacts-root artifacts/logs
python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs
```

## Residual-risk notes for reviewers

- **Unconfirmed:** canonical runtime hook not validated in this workspace.
- **Demo-only:** demo artifact runs are useful for pipeline verification but do not prove production enforcement.
- **Partially Implemented:** model-generation safety is evaluated via adversarial output scenarios in this workspace; runtime-side model guardrail enforcement semantics remain deployment-dependent.
