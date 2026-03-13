from __future__ import annotations

from integration_adapter.versioning import evaluate_compatibility


def test_compatibility_policy_allowed_exact() -> None:
    decision = evaluate_compatibility(contract_name="artifact", expected_version="1.0", actual_version="1.0")
    assert decision.status == "allowed"


def test_compatibility_policy_allowed_backward_minor() -> None:
    decision = evaluate_compatibility(contract_name="artifact", expected_version="1.2", actual_version="1.1")
    assert decision.status == "allowed"


def test_compatibility_policy_warn_only_forward_minor() -> None:
    decision = evaluate_compatibility(contract_name="artifact", expected_version="1.0", actual_version="1.1")
    assert decision.status == "warn_only"


def test_compatibility_policy_blocked_major_mismatch() -> None:
    decision = evaluate_compatibility(contract_name="artifact", expected_version="1.0", actual_version="2.0")
    assert decision.status == "blocked"
