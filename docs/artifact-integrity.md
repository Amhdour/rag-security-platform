# Artifact Integrity Safeguards

This workspace uses integrity metadata to improve evidence bundle reviewability.

## Integrity modes

- **Implemented:** `hash_only` (default) verifies required artifact presence and SHA-256 consistency from `artifact_integrity.manifest.json`.
- **Partially Implemented:** `signed_manifest` adds optional HMAC-SHA256 signing over the integrity manifest payload.
- **Unconfirmed:** `signed_manifest` improves tamper resistance for configured key holders but is **not** cryptographic non-repudiation.

## Implemented safeguards

- **Implemented:** `artifact_integrity.manifest.json` is generated for adapter artifact bundles.
- **Implemented:** Manifest records include:
  - relative file path
  - SHA-256 hash
  - file size
  - manifest generation timestamp
  - integrity manifest schema version
  - integrity mode metadata
- **Implemented:** Launch Gate includes `artifact_integrity_manifest` fail-closed validation.

## Optional signed manifest configuration

Enable signed manifest mode with environment variables:

```bash
export INTEGRATION_ADAPTER_INTEGRITY_MODE=signed_manifest
export INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY_PATH=/secure/path/signing.key
export INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY_ID=ops-key-1
```

Alternative inline key (less preferred):

```bash
export INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY='replace-with-secret'
```

## Verification commands

Hash-only (default):

```bash
cd integration-adapter
python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs
```

Signed manifest verification:

```bash
cd integration-adapter
python -m integration_adapter.verify_artifact_integrity \
  --artifacts-root artifacts/logs \
  --integrity-mode signed_manifest \
  --signing-key-path /secure/path/signing.key
```

Checks include:
1. required artifact presence,
2. manifest completeness for required files,
3. SHA-256 hash consistency,
4. optional signed-manifest verification when `signed_manifest` mode is selected.

## Limits and trust assumptions

- **Implemented:** Hash and optional signature checks detect accidental or obvious tampering when keys are managed correctly.
- **Partially Implemented:** Signed-manifest mode currently uses shared-secret HMAC for integrity/authenticity among trusted operators.
- **Unconfirmed:** no asymmetric signature/attestation chain or key transparency is implemented in this workspace.
- **Unconfirmed:** no deployment-wide non-repudiation guarantees are implemented in this workspace.
