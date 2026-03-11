from __future__ import annotations

from pathlib import Path


def test_overview_includes_global_empty_state_guidance_rendering() -> None:
    app_js = (Path(__file__).resolve().parents[2] / "observability/web/static/app.js").read_text()

    assert "renderGlobalEmptyState(" in app_js
    assert "Try this demo workflow:" in app_js
    assert "Artifacts root:" in app_js
