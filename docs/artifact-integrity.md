# Artifact Integrity Safeguards

This workspace uses integrity metadata to improve evidence bundle reviewability.

## Implemented safeguards

- **Implemented:** `artifact_integrity.manifest.json` is generated for adapter artifact bundles.
- **Implemented:** Manifest records include:
  - relative file path
  - SHA-256 hash
  - file size
  - manifest generation timestamp
  - integrity manifest schema version
- **Implemented:** Launch-gate includes `artifact_integrity_manifest` fail-closed validation.

## Verification command

```bash
cd integration-adapter
python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs
```

This checks:
1. required artifact presence,
2. manifest completeness for required files,
3. SHA-256 hash consistency.

## Limitations

- **Implemented:** Integrity checks detect accidental or obvious tampering via hash mismatch.
- **Unconfirmed:** no cryptographic signing or key-based non-repudiation is implemented.
- **Planned:** signed attestations for stronger anti-tamper and provenance guarantees.
