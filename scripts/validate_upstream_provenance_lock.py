#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

LOCK_PATH = Path("docs/upstream-provenance.lock.json")

REQUIRED_ROOT_KEYS = {"lock_version", "workspace", "components"}
REQUIRED_WORKSPACE_KEYS = {"repository", "tracked_at_workspace_commit", "generated_by", "notes"}
REQUIRED_COMPONENT_KEYS = {"component_id", "local_path", "role", "upstream", "local_snapshot"}
REQUIRED_UPSTREAM_KEYS = {"repo_name", "expected_remote_url", "expected_ref", "pinned_commit", "pin_status"}
REQUIRED_SNAPSHOT_KEYS = {
    "git_metadata_available",
    "snapshot_status",
    "unavailable_reason",
    "verification_commands",
    "maintainer_todo",
}

ALLOWED_PIN_STATUSES = {"IMPLEMENTED", "UNCONFIRMED", "PLANNED"}


def _ensure_keys(obj: dict, required: set[str], context: str, errors: list[str]) -> None:
    missing = sorted(required - set(obj.keys()))
    if missing:
        errors.append(f"{context}: missing required keys: {missing}")


def validate_lock(data: dict) -> list[str]:
    errors: list[str] = []

    _ensure_keys(data, REQUIRED_ROOT_KEYS, "root", errors)

    workspace = data.get("workspace")
    if not isinstance(workspace, dict):
        errors.append("root.workspace must be an object")
    else:
        _ensure_keys(workspace, REQUIRED_WORKSPACE_KEYS, "workspace", errors)
        for key in sorted(REQUIRED_WORKSPACE_KEYS):
            value = workspace.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"workspace.{key} must be a non-empty string")

    components = data.get("components")
    if not isinstance(components, list) or not components:
        errors.append("root.components must be a non-empty array")
        return errors

    component_ids: set[str] = set()
    for idx, component in enumerate(components):
        ctx = f"components[{idx}]"
        if not isinstance(component, dict):
            errors.append(f"{ctx} must be an object")
            continue

        _ensure_keys(component, REQUIRED_COMPONENT_KEYS, ctx, errors)

        component_id = component.get("component_id")
        if not isinstance(component_id, str) or not component_id.strip():
            errors.append(f"{ctx}.component_id must be a non-empty string")
        elif component_id in component_ids:
            errors.append(f"{ctx}.component_id must be unique; duplicate: {component_id}")
        else:
            component_ids.add(component_id)

        for key in ("local_path", "role"):
            value = component.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{ctx}.{key} must be a non-empty string")

        upstream = component.get("upstream")
        if not isinstance(upstream, dict):
            errors.append(f"{ctx}.upstream must be an object")
        else:
            _ensure_keys(upstream, REQUIRED_UPSTREAM_KEYS, f"{ctx}.upstream", errors)
            if not isinstance(upstream.get("repo_name"), str) or not upstream["repo_name"].strip():
                errors.append(f"{ctx}.upstream.repo_name must be a non-empty string")

            pin_status = upstream.get("pin_status")
            if pin_status not in ALLOWED_PIN_STATUSES:
                errors.append(
                    f"{ctx}.upstream.pin_status must be one of {sorted(ALLOWED_PIN_STATUSES)}, got {pin_status!r}"
                )

            pinned_commit = upstream.get("pinned_commit")
            if pin_status == "IMPLEMENTED":
                if not isinstance(pinned_commit, str) or not pinned_commit.strip():
                    errors.append(f"{ctx}.upstream.pinned_commit must be non-empty when pin_status=IMPLEMENTED")
            elif pinned_commit not in (None, "") and not isinstance(pinned_commit, str):
                errors.append(
                    f"{ctx}.upstream.pinned_commit must be null/empty string/non-empty string depending on pin_status"
                )

            expected_remote_url = upstream.get("expected_remote_url")
            if expected_remote_url is not None and not isinstance(expected_remote_url, str):
                errors.append(f"{ctx}.upstream.expected_remote_url must be string or null")

            expected_ref = upstream.get("expected_ref")
            if expected_ref is not None and not isinstance(expected_ref, str):
                errors.append(f"{ctx}.upstream.expected_ref must be string or null")

        snapshot = component.get("local_snapshot")
        if not isinstance(snapshot, dict):
            errors.append(f"{ctx}.local_snapshot must be an object")
        else:
            _ensure_keys(snapshot, REQUIRED_SNAPSHOT_KEYS, f"{ctx}.local_snapshot", errors)
            if not isinstance(snapshot.get("git_metadata_available"), bool):
                errors.append(f"{ctx}.local_snapshot.git_metadata_available must be a boolean")
            if not isinstance(snapshot.get("snapshot_status"), str) or not snapshot["snapshot_status"].strip():
                errors.append(f"{ctx}.local_snapshot.snapshot_status must be a non-empty string")

            verification_commands = snapshot.get("verification_commands")
            if not isinstance(verification_commands, list) or not verification_commands:
                errors.append(f"{ctx}.local_snapshot.verification_commands must be a non-empty array")
            else:
                for command_idx, command in enumerate(verification_commands):
                    if not isinstance(command, str) or not command.strip():
                        errors.append(
                            f"{ctx}.local_snapshot.verification_commands[{command_idx}] must be a non-empty string"
                        )

            for key in ("maintainer_todo",):
                value = snapshot.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{ctx}.local_snapshot.{key} must be a non-empty string")

    return errors


def main() -> int:
    if not LOCK_PATH.exists():
        print(f"[provenance-lock] FAIL: missing lock file: {LOCK_PATH}", file=sys.stderr)
        return 1

    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[provenance-lock] FAIL: invalid JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print("[provenance-lock] FAIL: root JSON value must be an object", file=sys.stderr)
        return 1

    errors = validate_lock(data)
    if errors:
        print("[provenance-lock] FAIL: lock validation errors detected:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"[provenance-lock] PASS: {LOCK_PATH} is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
