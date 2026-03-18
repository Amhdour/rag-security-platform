from __future__ import annotations

"""Versioned contract policy for adapter source/normalized/artifact/Launch Gate schemas.

Implemented: explicit schema-version constants and compatibility decisions.
Implemented: blocked/warn-only/allowed outcomes for upgrade/downgrade handling.
"""

from dataclasses import dataclass
import os


RAW_SOURCE_SCHEMA_VERSION = "1.0"
NORMALIZED_SCHEMA_VERSION = "1.0"
ARTIFACT_BUNDLE_SCHEMA_VERSION = "1.0"
LAUNCH_GATE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class CompatibilityDecision:
    contract_name: str
    expected_version: str
    actual_version: str
    status: str  # allowed | warn_only | blocked
    reason: str


def _parse_version(version: str) -> tuple[int, int]:
    parts = version.split(".")
    if len(parts) != 2:
        raise ValueError(f"invalid version format: {version!r}; expected 'major.minor'")
    major, minor = parts
    return int(major), int(minor)


def evaluate_compatibility(*, contract_name: str, expected_version: str, actual_version: str) -> CompatibilityDecision:
    """Return compatibility decision.

    Policy:
    - allowed: exact match or same major with actual minor <= expected minor
    - warn_only: same major with actual minor > expected minor (forward minor drift)
    - blocked: major mismatch or invalid/missing versions
    """

    if not expected_version.strip() or not actual_version.strip():
        return CompatibilityDecision(
            contract_name=contract_name,
            expected_version=expected_version,
            actual_version=actual_version,
            status="blocked",
            reason="missing version value",
        )

    try:
        exp_major, exp_minor = _parse_version(expected_version)
        act_major, act_minor = _parse_version(actual_version)
    except ValueError as exc:
        return CompatibilityDecision(
            contract_name=contract_name,
            expected_version=expected_version,
            actual_version=actual_version,
            status="blocked",
            reason=str(exc),
        )

    if exp_major != act_major:
        return CompatibilityDecision(
            contract_name=contract_name,
            expected_version=expected_version,
            actual_version=actual_version,
            status="blocked",
            reason="major version mismatch",
        )

    if act_minor > exp_minor:
        return CompatibilityDecision(
            contract_name=contract_name,
            expected_version=expected_version,
            actual_version=actual_version,
            status="warn_only",
            reason="forward minor version drift",
        )

    return CompatibilityDecision(
        contract_name=contract_name,
        expected_version=expected_version,
        actual_version=actual_version,
        status="allowed",
        reason="compatible within major version",
    )


def expected_versions_from_env() -> dict[str, str]:
    return {
        "source_schema": os.getenv("INTEGRATION_ADAPTER_EXPECTED_SOURCE_SCHEMA_VERSION", RAW_SOURCE_SCHEMA_VERSION),
        "normalized_schema": os.getenv(
            "INTEGRATION_ADAPTER_EXPECTED_NORMALIZED_SCHEMA_VERSION", NORMALIZED_SCHEMA_VERSION
        ),
        "artifact_bundle_schema": os.getenv(
            "INTEGRATION_ADAPTER_EXPECTED_ARTIFACT_BUNDLE_SCHEMA_VERSION", ARTIFACT_BUNDLE_SCHEMA_VERSION
        ),
        "launch_gate_schema": os.getenv(
            "INTEGRATION_ADAPTER_EXPECTED_LAUNCH_GATE_SCHEMA_VERSION", LAUNCH_GATE_SCHEMA_VERSION
        ),
    }
