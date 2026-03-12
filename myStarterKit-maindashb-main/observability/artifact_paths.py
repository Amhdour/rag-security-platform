"""Artifact path adapter for observability readers.

This keeps artifact-location concerns separate from parsing/rendering logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArtifactPaths:
    """Resolved artifact locations for dashboard consumption."""

    repo_root: Path
    artifacts_root: Path

    @classmethod
    def from_root(cls, *, repo_root: Path, artifacts_root: str | Path = "artifacts/logs") -> "ArtifactPaths":
        resolved_repo = Path(repo_root)
        root = Path(artifacts_root).expanduser()
        resolved_artifacts = root if root.is_absolute() else resolved_repo / root
        return cls(repo_root=resolved_repo, artifacts_root=resolved_artifacts)

    @property
    def default_root(self) -> Path:
        return self.repo_root / "artifacts/logs"

    @property
    def demo_mode(self) -> bool:
        return "demo" in self.relative(self.artifacts_root)

    @property
    def audit_jsonl(self) -> Path:
        return self.artifacts_root / "audit.jsonl"

    @property
    def replay_dir(self) -> Path:
        return self.artifacts_root / "replay"

    @property
    def evals_dir(self) -> Path:
        return self.artifacts_root / "evals"

    @property
    def launch_gate_dir(self) -> Path:
        return self.artifacts_root / "launch_gate"

    def glob(self, pattern: str):
        return self.artifacts_root.glob(pattern)

    def relative(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.repo_root))
        except ValueError:
            return str(path)
