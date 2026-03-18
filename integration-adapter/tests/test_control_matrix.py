from __future__ import annotations

from pathlib import Path

from integration_adapter.control_matrix import build_control_matrix, render_markdown


def test_control_matrix_includes_fixture_scenarios() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    rows = build_control_matrix(repo_root)
    scenario_ids = {row.scenario_id for row in rows}

    assert "PR-201" in scenario_ids
    assert "LK-301" in scenario_ids
    assert "PI-001" in scenario_ids


def test_control_matrix_markdown_has_required_columns() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    markdown = render_markdown(build_control_matrix(repo_root))

    assert "| Scenario | Threat | Control | Implementation file/module | Test coverage | Evidence artifact |" in markdown
    assert "reviewer control matrix" in markdown.lower()
