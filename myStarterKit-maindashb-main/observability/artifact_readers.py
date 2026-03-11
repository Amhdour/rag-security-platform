"""Artifact readers/adapters for dashboard data ingestion.

This module provides a stable, read-only data layer over repository artifacts.
It never invokes runtime enforcement components and only parses filesystem evidence.

Assumptions (detected from repository artifacts):
- audit log is JSONL with one event object per line.
- replay artifacts are JSON objects under `replay/*.replay.json`.
- eval outputs include `<run_id>.jsonl` and `<run_id>.summary.json` under `evals/`.
- verification outputs may include `*.summary.json` and/or `*.summary.md`.
- launch-gate outputs are JSON files under `launch_gate/*.json`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from observability.artifact_paths import ArtifactPaths
from observability.eval_normalization import parse_eval_jsonl, parse_eval_summary
from observability.launch_gate_normalization import parse_launch_gate_report
from observability.trace_normalization import read_audit_jsonl


@dataclass(frozen=True)
class SafeParsedFile:
    """Generic normalized representation for one parsed file."""

    path: str
    format: str
    exists: bool
    parsed: bool
    data: dict[str, Any] | list[dict[str, Any]] | None
    malformed_lines: int = 0
    error: str | None = None


class ArtifactReaders:
    """Read-only adapters over runtime evidence artifacts."""

    def __init__(self, repo_root: Path, *, artifacts_root: str | Path = "artifacts/logs") -> None:
        self.paths = ArtifactPaths.from_root(repo_root=repo_root, artifacts_root=artifacts_root)

    def read_audit_jsonl(self) -> SafeParsedFile:
        path = self.paths.audit_jsonl
        if not path.is_file():
            return SafeParsedFile(
                path=self.paths.relative(path),
                format="jsonl",
                exists=False,
                parsed=True,
                data=[],
            )
        try:
            events, malformed = read_audit_jsonl(path)
        except OSError as exc:
            return SafeParsedFile(
                path=self.paths.relative(path),
                format="jsonl",
                exists=True,
                parsed=False,
                data=None,
                error=f"read_error: {exc.__class__.__name__}",
            )
        return SafeParsedFile(
            path=self.paths.relative(path),
            format="jsonl",
            exists=True,
            parsed=True,
            data=events,
            malformed_lines=malformed,
        )

    def read_replay_json(self) -> list[SafeParsedFile]:
        rows: list[SafeParsedFile] = []
        for path in sorted(self.paths.glob("replay/*.replay.json"), reverse=True):
            rows.append(self._read_json_object(path, expected_format="json"))
        return rows

    def read_eval_jsonl(self) -> list[SafeParsedFile]:
        rows: list[SafeParsedFile] = []
        for path in sorted(self.paths.glob("evals/*.jsonl"), reverse=True):
            if not path.is_file():
                continue
            try:
                data, malformed = parse_eval_jsonl(path)
            except OSError as exc:
                rows.append(
                    SafeParsedFile(
                        path=self.paths.relative(path),
                        format="jsonl",
                        exists=True,
                        parsed=False,
                        data=None,
                        error=f"read_error: {exc.__class__.__name__}",
                    )
                )
                continue
            rows.append(
                SafeParsedFile(
                    path=self.paths.relative(path),
                    format="jsonl",
                    exists=True,
                    parsed=True,
                    data=data,
                    malformed_lines=malformed,
                )
            )
        return rows

    def read_eval_summary_json(self) -> list[SafeParsedFile]:
        rows: list[SafeParsedFile] = []
        for path in sorted(self.paths.glob("evals/*.summary.json"), reverse=True):
            parsed = parse_eval_summary(path)
            if parsed is None:
                rows.append(
                    SafeParsedFile(
                        path=self.paths.relative(path),
                        format="json",
                        exists=True,
                        parsed=False,
                        data=None,
                        error="parse_error",
                    )
                )
                continue
            rows.append(
                SafeParsedFile(
                    path=self.paths.relative(path),
                    format="json",
                    exists=True,
                    parsed=True,
                    data=parsed,
                )
            )
        return rows

    def read_verification_summaries(self) -> list[SafeParsedFile]:
        rows: list[SafeParsedFile] = []
        for path in sorted(self.paths.glob("verification/*.summary.json"), reverse=True):
            rows.append(self._read_json_object(path, expected_format="json"))
        for path in sorted(self.paths.glob("verification/*.summary.md"), reverse=True):
            rows.append(self._read_markdown(path))
        return rows

    def read_launch_gate_output_json(self) -> list[SafeParsedFile]:
        rows: list[SafeParsedFile] = []
        for path in sorted(self.paths.glob("launch_gate/*.json"), reverse=True):
            parsed = parse_launch_gate_report(path)
            if parsed is None:
                rows.append(
                    SafeParsedFile(
                        path=self.paths.relative(path),
                        format="json",
                        exists=True,
                        parsed=False,
                        data=None,
                        error="parse_error",
                    )
                )
                continue
            rows.append(
                SafeParsedFile(
                    path=self.paths.relative(path),
                    format="json",
                    exists=True,
                    parsed=True,
                    data=parsed,
                )
            )
        return rows

    def read_all(self) -> dict[str, Any]:
        return {
            "audit_jsonl": self.read_audit_jsonl(),
            "replay_json": self.read_replay_json(),
            "eval_jsonl": self.read_eval_jsonl(),
            "eval_summary_json": self.read_eval_summary_json(),
            "verification_summaries": self.read_verification_summaries(),
            "launch_gate_output_json": self.read_launch_gate_output_json(),
        }

    def _read_json_object(self, path: Path, *, expected_format: str) -> SafeParsedFile:
        if not path.is_file():
            return SafeParsedFile(
                path=self.paths.relative(path),
                format=expected_format,
                exists=False,
                parsed=True,
                data=None,
            )
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            return SafeParsedFile(
                path=self.paths.relative(path),
                format=expected_format,
                exists=True,
                parsed=False,
                data=None,
                error=f"parse_error: {exc.__class__.__name__}",
            )
        if not isinstance(payload, dict):
            return SafeParsedFile(
                path=self.paths.relative(path),
                format=expected_format,
                exists=True,
                parsed=False,
                data=None,
                error="parse_error: expected_object",
            )
        return SafeParsedFile(
            path=self.paths.relative(path),
            format=expected_format,
            exists=True,
            parsed=True,
            data=payload,
        )

    def _read_markdown(self, path: Path) -> SafeParsedFile:
        if not path.is_file():
            return SafeParsedFile(
                path=self.paths.relative(path),
                format="markdown",
                exists=False,
                parsed=True,
                data=None,
            )
        try:
            content = path.read_text()
        except OSError as exc:
            return SafeParsedFile(
                path=self.paths.relative(path),
                format="markdown",
                exists=True,
                parsed=False,
                data=None,
                error=f"read_error: {exc.__class__.__name__}",
            )
        return SafeParsedFile(
            path=self.paths.relative(path),
            format="markdown",
            exists=True,
            parsed=True,
            data={"content": content, "line_count": len(content.splitlines())},
        )
