from __future__ import annotations

from pathlib import Path
import sys

from integration_adapter.config import AdapterConfig
from integration_adapter.pipeline import generate_artifacts


def test_dashboard_service_reads_adapter_outputs_from_configured_root(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    starterkit_root = repo_root / "myStarterKit-maindashb-main"
    sys.path.insert(0, str(starterkit_root))

    artifacts_root = tmp_path / "integration-artifacts" / "logs"
    generate_artifacts(force_demo=True, config=AdapterConfig(artifacts_root=artifacts_root))

    from observability.service import DashboardService  # type: ignore

    service = DashboardService(starterkit_root, artifacts_root=str(artifacts_root.resolve()))
    overview = service.get_overview()

    assert overview["counts"]["traces"] >= 1
    assert overview["counts"]["eval_runs"] >= 1
    assert overview.get("empty_state", {}).get("present") is False

    trace = service.get_trace("trace-1")
    assert trace is not None
    assert trace.get("cross_links", {}).get("replay", {}).get("correlation") == "exact"

