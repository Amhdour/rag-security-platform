from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from integration_adapter.config import AdapterConfig


@dataclass(frozen=True)
class RetentionRule:
    family: str
    ttl_seconds: int
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class RetentionDecision:
    path: Path
    family: str
    age_seconds: int
    reason: str


@dataclass(frozen=True)
class RetentionResult:
    profile: str
    artifacts_root: Path
    dry_run: bool
    candidates: list[RetentionDecision]
    deleted_paths: list[Path]
    preserved_paths: list[Path]

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "artifacts_root": str(self.artifacts_root),
            "dry_run": self.dry_run,
            "candidate_count": len(self.candidates),
            "deleted_count": len(self.deleted_paths),
            "preserved_count": len(self.preserved_paths),
            "candidates": [
                {
                    "path": str(item.path),
                    "family": item.family,
                    "age_seconds": item.age_seconds,
                    "reason": item.reason,
                }
                for item in self.candidates
            ],
            "deleted_paths": [str(path) for path in self.deleted_paths],
            "preserved_paths": [str(path) for path in self.preserved_paths],
        }


PROFILE_RETENTION_RULES: dict[str, tuple[RetentionRule, ...]] = {
    "demo": (
        RetentionRule("audit_logs", 2 * 24 * 3600, ("audit*.jsonl",)),
        RetentionRule("eval_outputs", 3 * 24 * 3600, ("evals/*.jsonl", "evals/*.summary.json")),
        RetentionRule("launch_gate_outputs", 3 * 24 * 3600, ("launch_gate/security-readiness-*.json", "launch_gate/security-readiness-*.md")),
        RetentionRule("adapter_health", 3 * 24 * 3600, ("adapter_health/*.json",)),
        RetentionRule("integrity_manifests", 3 * 24 * 3600, ("artifact_integrity*.json",)),
    ),
    "dev": (
        RetentionRule("audit_logs", 7 * 24 * 3600, ("audit*.jsonl",)),
        RetentionRule("eval_outputs", 14 * 24 * 3600, ("evals/*.jsonl", "evals/*.summary.json")),
        RetentionRule("launch_gate_outputs", 14 * 24 * 3600, ("launch_gate/security-readiness-*.json", "launch_gate/security-readiness-*.md")),
        RetentionRule("adapter_health", 14 * 24 * 3600, ("adapter_health/*.json",)),
        RetentionRule("integrity_manifests", 14 * 24 * 3600, ("artifact_integrity*.json",)),
    ),
    "ci": (
        RetentionRule("audit_logs", 24 * 3600, ("audit*.jsonl",)),
        RetentionRule("eval_outputs", 2 * 24 * 3600, ("evals/*.jsonl", "evals/*.summary.json")),
        RetentionRule("launch_gate_outputs", 2 * 24 * 3600, ("launch_gate/security-readiness-*.json", "launch_gate/security-readiness-*.md")),
        RetentionRule("adapter_health", 2 * 24 * 3600, ("adapter_health/*.json",)),
        RetentionRule("integrity_manifests", 2 * 24 * 3600, ("artifact_integrity*.json",)),
    ),
    "prod_like": (
        RetentionRule("audit_logs", 30 * 24 * 3600, ("audit*.jsonl",)),
        RetentionRule("eval_outputs", 30 * 24 * 3600, ("evals/*.jsonl", "evals/*.summary.json")),
        RetentionRule("launch_gate_outputs", 90 * 24 * 3600, ("launch_gate/security-readiness-*.json", "launch_gate/security-readiness-*.md")),
        RetentionRule("adapter_health", 30 * 24 * 3600, ("adapter_health/*.json",)),
        RetentionRule("integrity_manifests", 30 * 24 * 3600, ("artifact_integrity*.json",)),
    ),
}


def _env_ttl_seconds(profile: str, family: str, default_ttl: int) -> int:
    key = f"INTEGRATION_ADAPTER_RETENTION_{profile.upper()}_{family.upper()}_SECONDS"
    value = os.environ.get(key)
    if not value:
        return default_ttl
    try:
        parsed = int(value)
    except ValueError:
        return default_ttl
    return max(0, parsed)


def _resolve_rules(profile: str) -> tuple[RetentionRule, ...]:
    normalized = profile.strip().lower()
    if normalized not in PROFILE_RETENTION_RULES:
        raise ValueError(f"unsupported retention profile={profile!r}; expected one of {sorted(PROFILE_RETENTION_RULES)}")
    rules = PROFILE_RETENTION_RULES[normalized]
    return tuple(
        RetentionRule(
            family=rule.family,
            ttl_seconds=_env_ttl_seconds(normalized, rule.family, rule.ttl_seconds),
            patterns=rule.patterns,
        )
        for rule in rules
    )


def _load_manifest_paths(artifacts_root: Path) -> set[Path]:
    manifest = artifacts_root / "artifact_integrity.manifest.json"
    if not manifest.exists():
        return set()
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    entries = payload.get("artifacts") if isinstance(payload, dict) else []
    if not isinstance(entries, list):
        return set()
    protected: set[Path] = set()
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            protected.add(artifacts_root / str(entry["path"]))
    return protected


def _launch_gate_files_for_run(launch_json: Path) -> set[Path]:
    maybe_md = launch_json.with_suffix(".md")
    output = {launch_json}
    if maybe_md.exists():
        output.add(maybe_md)
    return output


def _latest_successful_launch_gate_files(artifacts_root: Path, keep_count: int) -> set[Path]:
    launch_dir = artifacts_root / "launch_gate"
    if keep_count <= 0 or not launch_dir.exists():
        return set()

    successful: list[tuple[datetime, Path]] = []
    all_json = sorted(launch_dir.glob("security-readiness-*.json"))
    for path in all_json:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        status = str(payload.get("status", "")).strip().lower()
        if status not in {"go", "conditional_go"}:
            continue
        generated_at = payload.get("generated_at")
        try:
            dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        successful.append((dt, path))

    successful.sort(key=lambda item: item[0], reverse=True)
    protected: set[Path] = set()
    for _, launch_json in successful[:keep_count]:
        protected.update(_launch_gate_files_for_run(launch_json))

    return protected


def _required_protected_files(artifacts_root: Path) -> set[Path]:
    relative_paths = [
        "artifact_bundle.contract.json",
        "artifact_integrity.manifest.json",
        "audit.jsonl",
        "connectors.inventory.json",
        "tools.inventory.json",
        "mcp_servers.inventory.json",
        "evals.inventory.json",
        "adapter_health/adapter_run_summary.json",
    ]
    return {artifacts_root / rel for rel in relative_paths}


def _iter_family_files(artifacts_root: Path, rules: Iterable[RetentionRule]) -> list[tuple[RetentionRule, Path]]:
    matches: list[tuple[RetentionRule, Path]] = []
    for rule in rules:
        for pattern in rule.patterns:
            for path in artifacts_root.glob(pattern):
                if path.is_file():
                    matches.append((rule, path))
    return matches


def apply_retention_policy(
    *,
    artifacts_root: Path,
    profile: str,
    dry_run: bool,
    keep_latest_successful_runs: int = 1,
    now: datetime | None = None,
) -> RetentionResult:
    current = now or datetime.now(timezone.utc)
    rules = _resolve_rules(profile)

    protected = _required_protected_files(artifacts_root)
    protected.update(_load_manifest_paths(artifacts_root))
    protected.update(_latest_successful_launch_gate_files(artifacts_root, keep_latest_successful_runs))

    candidates: list[RetentionDecision] = []
    deleted: list[Path] = []

    for rule, path in _iter_family_files(artifacts_root, rules):
        if path in protected:
            continue
        age_seconds = int((current - datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)).total_seconds())
        if age_seconds < max(0, rule.ttl_seconds):
            continue
        decision = RetentionDecision(
            path=path,
            family=rule.family,
            age_seconds=age_seconds,
            reason=f"expired ttl ({rule.ttl_seconds}s) for family={rule.family}",
        )
        candidates.append(decision)
        if not dry_run:
            path.unlink(missing_ok=True)
            deleted.append(path)

    return RetentionResult(
        profile=profile.strip().lower(),
        artifacts_root=artifacts_root,
        dry_run=dry_run,
        candidates=sorted(candidates, key=lambda item: str(item.path)),
        deleted_paths=sorted(deleted),
        preserved_paths=sorted(protected),
    )


def write_retention_outcome(*, artifacts_root: Path, payload: dict[str, object]) -> Path:
    path = artifacts_root / "adapter_health" / "retention_last_run.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply artifact retention and cleanup policy")
    parser.add_argument("--artifacts-root", default="artifacts/logs", help="artifact root containing generated adapter artifacts")
    parser.add_argument("--profile", default=os.environ.get("INTEGRATION_ADAPTER_PROFILE", "dev"), choices=["demo", "dev", "ci", "prod_like"], help="retention profile")
    parser.add_argument("--keep-latest-successful-runs", type=int, default=1, help="number of successful Launch Gate runs to preserve")
    parser.add_argument("--dry-run", action="store_true", help="report expirations without deleting files")
    parser.add_argument("--apply", action="store_true", help="delete expired files (destructive)")
    args = parser.parse_args()

    if args.dry_run and args.apply:
        print("[integration-adapter] choose either --dry-run or --apply", flush=True)
        return 1

    dry_run = not args.apply
    if args.dry_run:
        dry_run = True

    config = AdapterConfig(artifacts_root=Path(args.artifacts_root), profile=args.profile)
    result = apply_retention_policy(
        artifacts_root=config.artifacts_root,
        profile=config.profile,
        dry_run=dry_run,
        keep_latest_successful_runs=max(0, args.keep_latest_successful_runs),
    )
    payload = result.to_dict()
    write_retention_outcome(artifacts_root=config.artifacts_root, payload=payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if dry_run:
        print("[integration-adapter] retention dry-run complete")
    else:
        print("[integration-adapter] retention cleanup applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
