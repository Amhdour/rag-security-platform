from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTEGRITY_MANIFEST_FILENAME = "artifact_integrity.manifest.json"
INTEGRITY_MANIFEST_SCHEMA_VERSION = "1.1"

INTEGRITY_MODE_HASH_ONLY = "hash_only"
INTEGRITY_MODE_SIGNED_MANIFEST = "signed_manifest"
ALLOWED_INTEGRITY_MODES = {INTEGRITY_MODE_HASH_ONLY, INTEGRITY_MODE_SIGNED_MANIFEST}


@dataclass(frozen=True)
class IntegrityVerificationResult:
    ok: bool
    missing_required: list[str]
    missing_manifest_entries: list[str]
    hash_mismatches: list[str]
    integrity_mode: str
    signature_verified: bool
    signature_errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "missing_required": self.missing_required,
            "missing_manifest_entries": self.missing_manifest_entries,
            "hash_mismatches": self.hash_mismatches,
            "integrity_mode": self.integrity_mode,
            "signature_verified": self.signature_verified,
            "signature_errors": self.signature_errors,
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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load_signing_secret(*, signing_key: str | None, signing_key_path: Path | None) -> str | None:
    if signing_key and signing_key.strip():
        return signing_key.strip()
    if signing_key_path and signing_key_path.exists() and signing_key_path.is_file():
        return signing_key_path.read_text(encoding="utf-8").strip() or None
    return None


def _signature_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key != "signature"
    }


def _compute_hmac_signature(*, payload: dict[str, Any], signing_secret: str) -> tuple[str, str]:
    canonical = _canonical_json(_signature_payload(payload))
    payload_sha256 = _sha256_text(canonical)
    signature = hmac.new(signing_secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return payload_sha256, signature


def build_integrity_manifest(
    *,
    artifacts_root: Path,
    file_paths: list[Path],
    integrity_mode: str = INTEGRITY_MODE_HASH_ONLY,
    signing_key: str | None = None,
    signing_key_path: Path | None = None,
    signing_key_id: str = "unspecified",
) -> Path:
    manifest_path = artifacts_root / INTEGRITY_MANIFEST_FILENAME

    normalized_mode = integrity_mode.strip().lower()
    if normalized_mode not in ALLOWED_INTEGRITY_MODES:
        raise ValueError(f"unsupported integrity mode={integrity_mode!r}; allowed={sorted(ALLOWED_INTEGRITY_MODES)}")

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

    payload: dict[str, Any] = {
        "integrity_manifest_schema_version": INTEGRITY_MANIFEST_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_count": len(entries),
        "artifacts": entries,
        "integrity_mode": normalized_mode,
    }

    if normalized_mode == INTEGRITY_MODE_SIGNED_MANIFEST:
        secret = _load_signing_secret(signing_key=signing_key, signing_key_path=signing_key_path)
        if not secret:
            raise ValueError("signed_manifest mode requires a signing key (value or file path)")
        payload_sha256, signature_hex = _compute_hmac_signature(payload=payload, signing_secret=secret)
        payload["signature"] = {
            "algorithm": "hmac-sha256",
            "key_id": signing_key_id,
            "signed_payload_sha256": payload_sha256,
            "signature_hex": signature_hex,
        }

    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def verify_integrity_manifest(
    *,
    artifacts_root: Path,
    required_paths: list[str],
    integrity_mode: str | None = None,
    signing_key: str | None = None,
    signing_key_path: Path | None = None,
) -> IntegrityVerificationResult:
    manifest_path = artifacts_root / INTEGRITY_MANIFEST_FILENAME
    missing_required: list[str] = []
    missing_manifest_entries: list[str] = []
    hash_mismatches: list[str] = []
    signature_errors: list[str] = []

    for required in required_paths:
        if not (artifacts_root / required).exists():
            missing_required.append(required)

    if not manifest_path.exists():
        return IntegrityVerificationResult(
            ok=False,
            missing_required=missing_required + [INTEGRITY_MANIFEST_FILENAME],
            missing_manifest_entries=[],
            hash_mismatches=[],
            integrity_mode=integrity_mode or INTEGRITY_MODE_HASH_ONLY,
            signature_verified=False,
            signature_errors=[],
        )

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return IntegrityVerificationResult(
            ok=False,
            missing_required=missing_required,
            missing_manifest_entries=["manifest_malformed"],
            hash_mismatches=[],
            integrity_mode=integrity_mode or INTEGRITY_MODE_HASH_ONLY,
            signature_verified=False,
            signature_errors=[],
        )

    if not isinstance(payload, dict):
        return IntegrityVerificationResult(
            ok=False,
            missing_required=missing_required,
            missing_manifest_entries=["manifest_entries_invalid"],
            hash_mismatches=[],
            integrity_mode=integrity_mode or INTEGRITY_MODE_HASH_ONLY,
            signature_verified=False,
            signature_errors=[],
        )

    declared_mode = str(payload.get("integrity_mode", INTEGRITY_MODE_HASH_ONLY)).strip().lower()
    selected_mode = (integrity_mode or declared_mode).strip().lower()
    if selected_mode not in ALLOWED_INTEGRITY_MODES:
        selected_mode = INTEGRITY_MODE_HASH_ONLY

    if declared_mode not in ALLOWED_INTEGRITY_MODES:
        signature_errors.append(f"manifest declared unsupported integrity_mode={declared_mode!r}")

    if integrity_mode and selected_mode != declared_mode:
        signature_errors.append(
            f"integrity mode override mismatch: requested={selected_mode}, manifest={declared_mode}"
        )

    entries = payload.get("artifacts")
    if not isinstance(entries, list):
        return IntegrityVerificationResult(
            ok=False,
            missing_required=missing_required,
            missing_manifest_entries=["manifest_entries_invalid"],
            hash_mismatches=[],
            integrity_mode=selected_mode,
            signature_verified=False,
            signature_errors=sorted(set(signature_errors)),
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

    signature_verified = False
    if selected_mode == INTEGRITY_MODE_SIGNED_MANIFEST:
        signature = payload.get("signature")
        if not isinstance(signature, dict):
            signature_errors.append("signature block missing for signed_manifest mode")
        else:
            algo = str(signature.get("algorithm", "")).strip().lower()
            if algo != "hmac-sha256":
                signature_errors.append(f"unsupported signature algorithm={algo!r}")
            secret = _load_signing_secret(signing_key=signing_key, signing_key_path=signing_key_path)
            if not secret:
                signature_errors.append("signing key not provided for signed_manifest verification")
            if algo == "hmac-sha256" and secret:
                expected_payload_sha256, expected_signature = _compute_hmac_signature(payload=payload, signing_secret=secret)
                actual_payload_sha256 = str(signature.get("signed_payload_sha256", ""))
                actual_signature = str(signature.get("signature_hex", ""))
                if actual_payload_sha256 != expected_payload_sha256:
                    signature_errors.append("signed payload digest mismatch")
                if not hmac.compare_digest(actual_signature, expected_signature):
                    signature_errors.append("signature verification failed")
                if not signature_errors:
                    signature_verified = True
    else:
        signature_verified = True

    ok = not missing_required and not missing_manifest_entries and not hash_mismatches and not signature_errors
    return IntegrityVerificationResult(
        ok=ok,
        missing_required=sorted(set(missing_required)),
        missing_manifest_entries=sorted(set(missing_manifest_entries)),
        hash_mismatches=sorted(set(hash_mismatches)),
        integrity_mode=selected_mode,
        signature_verified=signature_verified,
        signature_errors=sorted(set(signature_errors)),
    )
