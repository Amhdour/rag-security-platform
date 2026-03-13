from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from integration_adapter.config import AdapterConfig
from integration_adapter.env_profiles import get_profile_policy
from integration_adapter.integrity import ALLOWED_INTEGRITY_MODES, INTEGRITY_MODE_SIGNED_MANIFEST
from integration_adapter.raw_sources import load_json_records, load_jsonl_records

SOURCE_ENV_VARS: dict[str, str] = {
    "INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON": "json",
    "INTEGRATION_ADAPTER_ONYX_TOOLS_JSON": "json",
    "INTEGRATION_ADAPTER_ONYX_MCP_JSON": "json",
    "INTEGRATION_ADAPTER_ONYX_EVALS_JSON": "json",
    "INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL": "jsonl",
}


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    field: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    status: str
    strict_sources: bool
    profile: str
    profile_policy: dict[str, Any]
    artifacts_root: str
    checked_source_paths: dict[str, str]
    issues: list[ValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "strict_sources": self.strict_sources,
            "profile": self.profile,
            "profile_policy": self.profile_policy,
            "artifacts_root": self.artifacts_root,
            "checked_source_paths": self.checked_source_paths,
            "issues": [asdict(item) for item in self.issues],
        }


def _validate_source_file(path: Path, source_kind: str) -> str | None:
    if not path.exists():
        return "path does not exist"
    if not path.is_file():
        return "path is not a file"

    try:
        if source_kind == "json":
            load_json_records(path)
        else:
            load_jsonl_records(path)
    except Exception as exc:  # noqa: BLE001
        return f"failed to parse {source_kind}: {exc}"
    return None


def validate_configuration(*, config: AdapterConfig, strict_sources: bool = False) -> ValidationReport:
    issues: list[ValidationIssue] = []
    checked_source_paths: dict[str, str] = {}

    profile_name = config.profile.strip().lower()
    try:
        profile_policy = get_profile_policy(profile_name).to_dict()
    except ValueError as exc:
        issues.append(ValidationIssue(level="error", field="INTEGRATION_ADAPTER_PROFILE", message=str(exc)))
        profile_policy = {}


    integrity_mode = config.integrity_mode.strip().lower()
    if integrity_mode not in ALLOWED_INTEGRITY_MODES:
        issues.append(
            ValidationIssue(
                level="error",
                field="INTEGRATION_ADAPTER_INTEGRITY_MODE",
                message=f"unsupported integrity mode={config.integrity_mode!r}; expected one of {sorted(ALLOWED_INTEGRITY_MODES)}",
            )
        )
    if integrity_mode == INTEGRITY_MODE_SIGNED_MANIFEST:
        has_inline_key = bool((config.integrity_signing_key or "").strip())
        has_key_file = bool(config.integrity_signing_key_path and config.integrity_signing_key_path.exists() and config.integrity_signing_key_path.is_file())
        if not has_inline_key and not has_key_file:
            issues.append(
                ValidationIssue(
                    level="error",
                    field="INTEGRITY_SIGNING_KEY",
                    message="signed_manifest mode requires INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY or INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY_PATH",
                )
            )

    if config.artifacts_root.exists() and not config.artifacts_root.is_dir():
        issues.append(ValidationIssue(level="error", field="INTEGRATION_ADAPTER_ARTIFACTS_ROOT", message="artifacts root exists but is not a directory"))
    else:
        try:
            config.ensure_dirs()
        except Exception as exc:  # noqa: BLE001
            issues.append(
                ValidationIssue(
                    level="error",
                    field="INTEGRATION_ADAPTER_ARTIFACTS_ROOT",
                    message=f"failed to create artifacts directories: {exc}",
                )
            )

    for env_name, source_kind in SOURCE_ENV_VARS.items():
        raw = os.environ.get(env_name)
        if not raw:
            if strict_sources:
                issues.append(
                    ValidationIssue(
                        level="error",
                        field=env_name,
                        message="required in strict source mode but not set",
                    )
                )
            continue

        path = Path(raw)
        checked_source_paths[env_name] = str(path)
        parse_error = _validate_source_file(path, source_kind)
        if parse_error:
            issues.append(ValidationIssue(level="error", field=env_name, message=parse_error))

    if not strict_sources and not checked_source_paths:
        issues.append(
            ValidationIssue(
                level="warning",
                field="source_inputs",
                message="no source input env vars set; exporter fallbacks/demo mode may be used",
            )
        )

    status = "fail" if any(item.level == "error" for item in issues) else "pass"
    return ValidationReport(
        status=status,
        strict_sources=strict_sources,
        profile=profile_name,
        profile_policy=profile_policy,
        artifacts_root=str(config.artifacts_root),
        checked_source_paths=checked_source_paths,
        issues=issues,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate integration-adapter configuration and source paths")
    parser.add_argument("--artifacts-root", default=None, help="override artifacts root for this validation")
    parser.add_argument("--profile", default=None, choices=["demo", "dev", "ci", "prod_like"], help="execution profile override")
    parser.add_argument("--strict-sources", action="store_true", help="require all source env vars and parse checks")
    args = parser.parse_args()

    if args.artifacts_root or args.profile:
        base = AdapterConfig.from_env()
        root = Path(args.artifacts_root) if args.artifacts_root else base.artifacts_root
        profile = args.profile or os.environ.get("INTEGRATION_ADAPTER_PROFILE", base.profile)
        config = AdapterConfig(
            artifacts_root=root,
            profile=profile,
            integrity_mode=base.integrity_mode,
            integrity_signing_key=base.integrity_signing_key,
            integrity_signing_key_path=base.integrity_signing_key_path,
            integrity_signing_key_id=base.integrity_signing_key_id,
        )
    else:
        config = AdapterConfig.from_env()
    report = validate_configuration(config=config, strict_sources=args.strict_sources)

    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    if report.status == "fail":
        print("[integration-adapter] config validation failed", file=sys.stderr)
        return 1
    print("[integration-adapter] config validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
