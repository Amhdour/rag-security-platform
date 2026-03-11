from __future__ import annotations

from pathlib import Path


def test_boundary_map_ui_renders_metadata_driven_links_and_context_columns() -> None:
    app_js = (Path(__file__).resolve().parents[2] / "observability/web/static/app.js").read_text()

    assert "what crosses this boundary" in app_js
    assert "what can go wrong" in app_js
    assert "what control exists" in app_js
    assert "relevant docs" in app_js
    assert "related controls" in app_js
    assert "evidence artifacts" in app_js
    assert "renderPathList(" in app_js
    assert "renderInlineList(" in app_js
