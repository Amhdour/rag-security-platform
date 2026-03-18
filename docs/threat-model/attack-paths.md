# Attack paths

| Path ID | Attack path | Expected control behavior | Implemented evidence point | Status |
|---|---|---|---|---|
| AP-01 | Prompt injection attempts instruction override -> unsafe output/tool step | Detect/contain unsafe pattern; score scenario with pass/fail/warn evidence | `integration_adapter.adversarial_harness` + `tests/test_adversarial_harness.py` | **Implemented** |
| AP-02 | Retrieval poisoning via malicious/hidden override docs | Identify poisoned retrieval indicators and fail expected scenarios | `tests/fixtures/adversarial/retrieval_poisoning/` + `tests/test_retrieval_poisoning_scenarios.py` | **Implemented** |
| AP-03 | Leakage of sensitive/tool result content into model output | Flag direct leakage and policy-conflicting responses | `tests/fixtures/adversarial/output_leakage/` + `tests/test_output_leakage_scenarios.py` | **Implemented** |
| AP-04 | Tampering with generated artifacts before review | Integrity verification fails and launch-gate blocks | `verify_artifact_integrity` + launch-gate integrity checks | **Implemented** |
| AP-05 | Schema/version drift bypasses control checks | Compatibility checks block mismatches | schema-versioning compatibility + launch-gate blocked outcomes | **Implemented** |
| AP-06 | Runtime hook changes silently reduce evidence fidelity | Gap must be marked unconfirmed until validated | explicit status language in docs + parity docs | **Unconfirmed** |
