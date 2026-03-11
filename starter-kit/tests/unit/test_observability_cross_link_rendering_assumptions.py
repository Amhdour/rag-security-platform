from __future__ import annotations

from pathlib import Path


def test_trace_and_launch_gate_render_cross_link_sections() -> None:
    app_js = (Path(__file__).resolve().parents[2] / "observability/web/static/app.js").read_text()

    assert "Related artifacts (correlation)" in app_js
    assert "renderTraceCrossLinks(" in app_js
    assert "Related control areas / eval categories" in app_js
    assert "renderLaunchGateRelatedLinks(" in app_js
    assert "Connected evidence summary" in app_js
    assert "Artifact integrity status" in app_js
    assert "renderArtifactIntegrity(" in app_js
    assert "integrity unverified" in app_js
    assert "signing not implemented" in app_js
