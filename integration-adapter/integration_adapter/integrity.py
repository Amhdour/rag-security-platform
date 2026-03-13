from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTEGRITY_MANIFEST_FILENAME = "artifact_integrity.manifest.json"
INTEGRITY_MANIFEST_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class IntegrityVerificationResult:
    ok: bool
    missing_required: list[str]
    missing_manifest_entries: list[str]
    hash_mismatches: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "missing_required": self.missing_required,
            "missing_manifest_entries": self.missing_manifest_entries,
            "hash_mismatches": self.hash_mismatches,
        }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def build_integrity_manifest(*, artifacts_root: Path, file_paths: list[Path]) -> Path:
    manifest_path = artifacts_root / INTEGRITY_MANIFEST_FILENAME

    entries = []
    for path in sorted(file_paths, key=lambda p: str(p)):
        if not path.exists() or not path.is_file():
            continue
        entries.append(
            {
                "path": str(path.relative_to(artifacts_root)),
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    payload = {
        "integrity_manifest_schema_version": INTEGRITY_MANIFEST_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_count": len(entries),
        "artifacts": entries,
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def verify_integrity_manifest(*, artifacts_root: Path, required_paths: list[str]) -> IntegrityVerificationResult:
    manifest_path = artifacts_root / INTEGRITY_MANIFEST_FILENAME
    missing_required: list[str] = []
    missing_manifest_entries: list[str] = []
    hash_mismatches: list[str] = []

    for required in required_paths:
        if not (artifacts_root / required).exists():
            missing_required.append(required)

    if not manifest_path.exists():
        return IntegrityVerificationResult(
            ok=False,
            missing_required=missing_required + [INTEGRITY_MANIFEST_FILENAME],
            missing_manifest_entries=[],
            hash_mismatches=[],
        )

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return IntegrityVerificationResult(
            ok=False,
            missing_required=missing_required,
            missing_manifest_entries=["manifest_malformed"],
            hash_mismatches=[],
        )

    entries = payload.get("artifacts") if isinstance(payload, dict) else []
    if not isinstance(entries, list):
        return IntegrityVerificationResult(
            ok=False,
            missing_required=missing_required,
            missing_manifest_entries=["manifest_entries_invalid"],
            hash_mismatches=[],
        )

    by_path: dict[str, dict[str, Any]] = {}
    for item in entries:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            by_path[str(item["path"])] = item

    for required in required_paths:
        if required not in by_path:
            missing_manifest_entries.append(required)

    for rel_path, entry in by_path.items():
        file_path = artifacts_root / rel_path
        if not file_path.exists() or not file_path.is_file():
            missing_required.append(rel_path)
            continue
        actual = _sha256_file(file_path)
        expected = str(entry.get("sha256", ""))
        if not expected or actual != expected:
            hash_mismatches.append(rel_path)

    ok = not missing_required and not missing_manifest_entries and not hash_mismatches
    return IntegrityVerificationResult(
        ok=ok,
        missing_required=sorted(set(missing_required)),
        missing_manifest_entries=sorted(set(missing_manifest_entries)),
        hash_mismatches=sorted(set(hash_mismatches)),
    )
