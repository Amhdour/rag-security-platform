from __future__ import annotations

import json
from pathlib import Path


def test_security_boundaries_metadata_has_required_zones_and_crossing_fields() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "observability/web/static/security_boundaries.json"
    payload = json.loads(path.read_text())

    zones = payload.get("zones", [])
    zone_names = {item.get("name") for item in zones if isinstance(item, dict)}
    required = {
        "Client / Interface",
        "App / Orchestrator",
        "Policy Engine",
        "Retrieval Service",
        "Source Registry / Retriever Backend",
        "Model Adapter",
        "Tool Router",
        "Tool Registry / Executors",
        "Telemetry / Audit pipeline",
        "Artifact storage",
        "Launch Gate",
    }
    assert required.issubset(zone_names)

    crossings = payload.get("crossings", [])
    assert crossings
    for row in crossings:
        assert row.get("boundary_id")
        assert row.get("from")
        assert row.get("to")
        assert row.get("what_crosses")
        assert row.get("control")
        assert row.get("control_locations")
        assert row.get("relevant_docs")
        assert row.get("related_controls")
        assert row.get("evidence_artifacts")
        assert row.get("what_can_go_wrong")

    for zone in zones:
        assert zone.get("component_paths")
        assert zone.get("relevant_docs")
        assert zone.get("related_controls")
        assert zone.get("related_evidence_artifacts")


def test_security_boundaries_control_locations_exist_when_file_paths() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "observability/web/static/security_boundaries.json"
    payload = json.loads(path.read_text())

    for zone in payload.get("zones", []):
        for raw in zone.get("component_paths", []):
            if raw.endswith("/"):
                continue
            assert (repo_root / raw).exists(), raw

    for row in payload.get("crossings", []):
        for raw in row.get("control_locations", []):
            assert (repo_root / raw).exists(), raw



def test_security_boundaries_docs_and_evidence_paths_are_repo_valid() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "observability/web/static/security_boundaries.json"
    payload = json.loads(path.read_text())

    def _path_exists_or_glob(raw: str) -> bool:
        if raw.startswith("artifacts/logs/"):
            return True
        if "*" in raw:
            return bool(list(repo_root.glob(raw)))
        return (repo_root / raw).exists()

    for zone in payload.get("zones", []):
        for raw in zone.get("relevant_docs", []):
            assert _path_exists_or_glob(raw), raw
        for raw in zone.get("related_evidence_artifacts", []):
            assert _path_exists_or_glob(raw), raw

    for row in payload.get("crossings", []):
        for raw in row.get("relevant_docs", []):
            assert _path_exists_or_glob(raw), raw
        for raw in row.get("evidence_artifacts", []):
            assert _path_exists_or_glob(raw), raw


def test_security_boundaries_schema_has_unique_ids_and_valid_zone_references() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "observability/web/static/security_boundaries.json"
    payload = json.loads(path.read_text())

    assert str(payload.get("schema_version", "")) == "1"

    zones = [item for item in payload.get("zones", []) if isinstance(item, dict)]
    zone_names = {str(item.get("name", "")) for item in zones}
    zone_ids = [str(item.get("id", "")) for item in zones]
    assert all(zone_ids)
    assert len(zone_ids) == len(set(zone_ids))

    crossings = [item for item in payload.get("crossings", []) if isinstance(item, dict)]
    boundary_ids = [str(item.get("boundary_id", "")) for item in crossings]
    assert all(boundary_ids)
    assert len(boundary_ids) == len(set(boundary_ids))

    for row in crossings:
        assert str(row.get("from", "")) in zone_names
        assert str(row.get("to", "")) in zone_names
