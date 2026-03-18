# Reviewer Control Matrix

**Implemented:** This matrix maps threat scenarios to control intent, implementation modules, test coverage, and evidence artifacts.
**Partially Implemented:** Rows generated from maintained fixture packs and default scenarios; completeness depends on fixture coverage.
**Unconfirmed:** canonical runtime hook not validated in this workspace.

Generated at: `2026-03-17T20:42:34.283642+00:00`

| Scenario | Threat | Control | Implementation file/module | Test coverage | Evidence artifact |
|---|---|---|---|---|---|
| `LK-301` | Model output includes raw secret material from retrieved context. | Block or redact sensitive value disclosure. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_output_leakage_scenarios.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `LK-302` | Raw tool output contains credentials and is echoed without sanitization. | Sanitize tool output and prevent credential leakage. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_output_leakage_scenarios.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `LK-303` | Generated answer contradicts explicit non-disclosure policy. | Deny output that conflicts with policy constraints. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_output_leakage_scenarios.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `LK-304` | Summarization leaks restricted details without access controls. | Refuse or sanitize summaries of restricted content. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_output_leakage_scenarios.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `LK-305` | Sensitive context from prior turn leaks into unrelated response. | Prevent carry-through leakage from prior restricted context. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_output_leakage_scenarios.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `PB-001` | Policy bypass language attempts to disable safeguards. | Reject policy bypass attempts and preserve guardrails. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_adversarial_harness.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `PI-001` | Prompt instruction override attempts unsafe behavior. | Deny malicious override prompts via policy decision gating. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_adversarial_harness.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `PR-201` | Retrieved content attempts instruction override to exfiltrate restricted data. | Deny retrieval influence and preserve runtime policy precedence. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_retrieval_poisoning_scenarios.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `PR-202` | Authoritative style attempts to normalize unsafe cross-tenant retrieval behavior. | Treat unverified authoritative claims as untrusted and block policy downgrade. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_retrieval_poisoning_scenarios.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `PR-203` | Hidden comment payload injects override directive not visible in normal rendering. | Detect hidden override pattern and deny unsafe retrieval influence. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_retrieval_poisoning_scenarios.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `PR-204` | Conflicting retrieval statements can induce unsafe model behavior if not escalated. | Flag conflict and deny automatic allow decision pending review. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_retrieval_poisoning_scenarios.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `PR-205` | Tampered or downgraded integrity state attempts to bypass trust validation. | Block retrieval path when integrity is downgraded or tampered. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_retrieval_poisoning_scenarios.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |
| `UT-001` | High-risk tool execution attempted without sufficient authorization. | Require deny/confirm decision for high-risk tools; warn if tools unavailable. | `integration-adapter/integration_adapter/adversarial_harness.py` | `integration-adapter/tests/test_adversarial_harness.py` | `integration-adapter/artifacts/logs/evals/adversarial-security-*.{jsonl,report.md,summary.json}` |

Regenerate with:
```bash
cd integration-adapter
python -m integration_adapter.control_matrix --output-doc ../docs/control-matrix.md
```
