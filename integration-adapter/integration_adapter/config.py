from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class AdapterConfig:
    artifacts_root: Path
    profile: str = "dev"
    integrity_mode: str = "hash_only"
    integrity_signing_key: str | None = None
    integrity_signing_key_path: Path | None = None
    integrity_signing_key_id: str = "unspecified"

    @classmethod
    def from_env(cls, default_root: str = "artifacts/logs") -> "AdapterConfig":
        configured = os.environ.get("INTEGRATION_ADAPTER_ARTIFACTS_ROOT", default_root)
        profile = os.environ.get("INTEGRATION_ADAPTER_PROFILE", "dev")
        integrity_mode = os.environ.get("INTEGRATION_ADAPTER_INTEGRITY_MODE", "hash_only")
        signing_key = os.environ.get("INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY")
        signing_key_path_raw = os.environ.get("INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY_PATH", "").strip()
        signing_key_path = Path(signing_key_path_raw) if signing_key_path_raw else None
        signing_key_id = os.environ.get("INTEGRATION_ADAPTER_INTEGRITY_SIGNING_KEY_ID", "unspecified")
        return cls(
            artifacts_root=Path(configured),
            profile=profile,
            integrity_mode=integrity_mode,
            integrity_signing_key=signing_key,
            integrity_signing_key_path=signing_key_path,
            integrity_signing_key_id=signing_key_id,
        )

    def ensure_dirs(self) -> None:
        (self.artifacts_root / "replay").mkdir(parents=True, exist_ok=True)
        (self.artifacts_root / "evals").mkdir(parents=True, exist_ok=True)
        (self.artifacts_root / "launch_gate").mkdir(parents=True, exist_ok=True)
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
