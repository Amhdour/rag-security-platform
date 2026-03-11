from __future__ import annotations

from pathlib import Path


def test_trace_explorer_filter_controls_include_security_workflow_fields() -> None:
    app_js = (Path(__file__).resolve().parents[2] / "observability/web/static/app.js").read_text()

    assert 'data-filter="final_outcome"' in app_js
    assert 'data-filter="decision_class"' in app_js
    assert 'data-filter="date_from"' in app_js
    assert 'data-filter="date_to"' in app_js
    assert 'data-filter-bool="replay_only"' in app_js
    assert 'data-filter-bool="partial_only"' in app_js
    assert 'data-filter-bool="security_only"' in app_js
    assert 'data-filter="sort_by"' in app_js
    assert 'data-filter="sort_order"' in app_js
