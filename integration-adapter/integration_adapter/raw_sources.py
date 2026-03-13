from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class SourceReadError(RuntimeError):
    """Raised when configured source payload cannot be parsed."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceReadError(f"invalid JSON in {path}: {exc}") from exc


def load_json_records(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        rows = payload.get("rows")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
        return [payload]
    raise SourceReadError(f"unsupported JSON payload type in {path}: {type(payload)}")


def load_jsonl_records(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            rows.append(decoded)
    return rows


def discover_default_paths(onyx_root: Path) -> dict[str, Path]:
    """Best-effort paths grounded in workspace layout.

    These are confirmed filesystem locations in this repository structure, but
    the specific artifact file presence is runtime-dependent.
    """

    return {
        "connectors": onyx_root / "backend" / "log" / "connectors.inventory.json",
        "tools": onyx_root / "backend" / "log" / "tools.inventory.json",
        "mcp_servers": onyx_root / "backend" / "log" / "mcp_servers.inventory.json",
        "evals": onyx_root / "backend" / "log" / "evals.json",
        "runtime_events": onyx_root / "backend" / "log" / "audit.jsonl",
    }


def env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value)


def _load_url_text(url: str, *, timeout_seconds: float = 5.0) -> str:
    req = Request(url, headers={"Accept": "application/json, application/x-ndjson"})
    try:
        with urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310
            raw = response.read()
    except URLError as exc:
        raise SourceReadError(f"failed to read URL {url}: {exc}") from exc
    return raw.decode("utf-8")


def load_json_records_from_url(url: str, *, timeout_seconds: float = 5.0) -> list[dict[str, Any]]:
    try:
        payload = json.loads(_load_url_text(url, timeout_seconds=timeout_seconds))
    except json.JSONDecodeError as exc:
        raise SourceReadError(f"invalid JSON from URL {url}: {exc}") from exc

    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        rows = payload.get("rows")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
        return [payload]
    raise SourceReadError(f"unsupported JSON payload type from URL {url}: {type(payload)}")


def load_jsonl_records_from_url(url: str, *, timeout_seconds: float = 5.0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = _load_url_text(url, timeout_seconds=timeout_seconds)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            rows.append(decoded)
    return rows
