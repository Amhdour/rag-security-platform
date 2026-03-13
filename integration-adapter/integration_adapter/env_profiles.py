from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


ALLOWED_PROFILES = {"demo", "dev", "ci", "prod_like"}


@dataclass(frozen=True)
class ProfilePolicy:
    name: str
    allowed_source_modes: set[str]
    critical_freshness_seconds: int
    warning_freshness_seconds: int
    logging_verbosity: str
    synthetic_fallback_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_source_modes"] = sorted(self.allowed_source_modes)
        return payload


PROFILE_POLICIES: dict[str, ProfilePolicy] = {
    "demo": ProfilePolicy(
        name="demo",
        allowed_source_modes={"synthetic", "fixture_backed", "file_backed", "db_backed", "live"},
        critical_freshness_seconds=7 * 24 * 3600,
        warning_freshness_seconds=14 * 24 * 3600,
        logging_verbosity="debug",
        synthetic_fallback_allowed=True,
    ),
    "dev": ProfilePolicy(
        name="dev",
        allowed_source_modes={"synthetic", "fixture_backed", "file_backed", "db_backed", "live"},
        critical_freshness_seconds=2 * 24 * 3600,
        warning_freshness_seconds=4 * 24 * 3600,
        logging_verbosity="info",
        synthetic_fallback_allowed=True,
    ),
    "ci": ProfilePolicy(
        name="ci",
        allowed_source_modes={"synthetic", "fixture_backed", "file_backed", "db_backed"},
        critical_freshness_seconds=24 * 3600,
        warning_freshness_seconds=48 * 3600,
        logging_verbosity="info",
        synthetic_fallback_allowed=True,
    ),
    "prod_like": ProfilePolicy(
        name="prod_like",
        allowed_source_modes={"live", "db_backed", "file_backed"},
        critical_freshness_seconds=3600,
        warning_freshness_seconds=6 * 3600,
        logging_verbosity="warn",
        synthetic_fallback_allowed=False,
    ),
}


@dataclass(frozen=True)
class ProfileValidationResult:
    profile: str
    blocked_reasons: list[str]
    warnings: list[str]


def get_profile_policy(profile: str) -> ProfilePolicy:
    normalized = profile.strip().lower()
    if normalized not in PROFILE_POLICIES:
        raise ValueError(
            f"unsupported INTEGRATION_ADAPTER_PROFILE={profile!r}; supported values: {sorted(ALLOWED_PROFILES)}"
        )
    return PROFILE_POLICIES[normalized]


def validate_profile_safeguards(
    *,
    profile: str,
    force_demo: bool,
    exporter_diagnostics: dict[str, dict[str, Any]],
    launch_gate_freshness_evidence: dict[str, Any] | None,
) -> ProfileValidationResult:
    policy = get_profile_policy(profile)
    blocked: list[str] = []
    warnings: list[str] = []

    if policy.name == "prod_like" and force_demo:
        blocked.append("prod_like profile cannot run with --demo / force_demo enabled")

    runtime_diag = exporter_diagnostics.get("runtime_events", {})
    runtime_mode = str(runtime_diag.get("source_mode", "unknown"))
    runtime_rows = int(runtime_diag.get("rows_count", 0) or 0)
    if runtime_mode == "unknown":
        if policy.name == "prod_like":
            blocked.append("prod_like requires explicit runtime_events source_mode metadata")
        else:
            warnings.append("runtime_events source_mode missing; treated as unknown")
    elif runtime_mode not in policy.allowed_source_modes:
        blocked.append(
            f"runtime_events source_mode={runtime_mode!r} is not allowed for profile={policy.name}; "
            f"allowed={sorted(policy.allowed_source_modes)}"
        )
    if policy.name == "prod_like" and (runtime_mode == "synthetic" or runtime_rows == 0):
        blocked.append("prod_like requires non-synthetic runtime evidence with at least one runtime event row")

    fallback_count = sum(1 for item in exporter_diagnostics.values() if bool(item.get("fallback_used", False)))
    if fallback_count > 0 and not policy.synthetic_fallback_allowed:
        blocked.append(f"profile={policy.name} forbids synthetic fallback usage, but fallback_count={fallback_count}")

    if launch_gate_freshness_evidence and policy.name == "prod_like":
        stale_critical = list(launch_gate_freshness_evidence.get("stale_critical", []))
        missing_critical = list(launch_gate_freshness_evidence.get("missing_critical", []))
        if stale_critical:
            blocked.append(f"prod_like requires fresh critical evidence; stale_critical={stale_critical}")
        if missing_critical:
            blocked.append(f"prod_like requires complete critical evidence; missing_critical={missing_critical}")

    if runtime_mode == "fixture_backed" and policy.name in {"dev", "ci"}:
        warnings.append("fixture-backed runtime evidence used")

    return ProfileValidationResult(profile=policy.name, blocked_reasons=blocked, warnings=warnings)
