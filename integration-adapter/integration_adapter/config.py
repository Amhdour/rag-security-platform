from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class AdapterConfig:
    artifacts_root: Path
    profile: str = "dev"

    @classmethod
    def from_env(cls, default_root: str = "artifacts/logs") -> "AdapterConfig":
        configured = os.environ.get("INTEGRATION_ADAPTER_ARTIFACTS_ROOT", default_root)
        profile = os.environ.get("INTEGRATION_ADAPTER_PROFILE", "dev")
        return cls(artifacts_root=Path(configured), profile=profile)

    def ensure_dirs(self) -> None:
        (self.artifacts_root / "replay").mkdir(parents=True, exist_ok=True)
        (self.artifacts_root / "evals").mkdir(parents=True, exist_ok=True)
        (self.artifacts_root / "launch_gate").mkdir(parents=True, exist_ok=True)
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
