from __future__ import annotations

import json
from pathlib import Path

from observability.artifact_readers import ArtifactReaders


def _make_reader(tmp_path: Path) -> ArtifactReaders:
    return ArtifactReaders(tmp_path, artifacts_root="artifacts/logs")


def test_artifact_readers_handle_missing_files_safely(tmp_path: Path) -> None:
    reader = _make_reader(tmp_path)

    payload = reader.read_all()

    assert payload["audit_jsonl"].exists is False
    assert payload["audit_jsonl"].parsed is True
    assert payload["audit_jsonl"].data == []
    assert payload["replay_json"] == []
    assert payload["eval_jsonl"] == []
    assert payload["eval_summary_json"] == []
    assert payload["verification_summaries"] == []
    assert payload["launch_gate_output_json"] == []


def test_artifact_readers_normalize_formats_and_malformed_lines(tmp_path: Path) -> None:
    root = tmp_path / "artifacts/logs"
    (root / "replay").mkdir(parents=True)
    (root / "evals").mkdir(parents=True)
    (root / "verification").mkdir(parents=True)
    (root / "launch_gate").mkdir(parents=True)

    (root / "audit.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event_id": "e1", "event_type": "request.start", "trace_id": "t1"}),
                "{bad-json}",
                json.dumps(["bad-shape"]),
            ]
        )
    )

    (root / "replay" / "trace-1.replay.json").write_text(json.dumps({"trace_id": "t1", "timeline": []}))

    (root / "evals" / "suite-1.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"scenario_id": "s1", "severity": "high", "passed": True, "title": "ok", "details": "ok"}),
                "not-json",
            ]
        )
    )
    (root / "evals" / "suite-1.summary.json").write_text(
        json.dumps({"suite_name": "suite-1", "passed": True, "total": 1, "passed_count": 1})
    )

    (root / "verification" / "security_guarantees.summary.json").write_text(json.dumps({"status": "pass"}))
    (root / "verification" / "security_guarantees.summary.md").write_text("# Verification\n- ok\n")

    (root / "launch_gate" / "security-readiness-1.json").write_text(
        json.dumps({"status": "go", "summary": "ok", "checks": [], "blockers": [], "residual_risks": []})
    )

    reader = _make_reader(tmp_path)

    audit = reader.read_audit_jsonl()
    assert audit.parsed is True
    assert audit.malformed_lines == 2
    assert isinstance(audit.data, list)
    assert len(audit.data) == 1

    replay = reader.read_replay_json()
    assert len(replay) == 1
    assert replay[0].parsed is True

    eval_rows = reader.read_eval_jsonl()
    assert len(eval_rows) == 1
    assert eval_rows[0].malformed_lines == 1

    eval_summary = reader.read_eval_summary_json()
    assert len(eval_summary) == 1
    assert eval_summary[0].parsed is True

    verification = reader.read_verification_summaries()
    assert len(verification) == 2
    assert {item.format for item in verification} == {"json", "markdown"}

    launch = reader.read_launch_gate_output_json()
    assert len(launch) == 1
    assert launch[0].parsed is True


def test_artifact_readers_report_parse_errors(tmp_path: Path) -> None:
    root = tmp_path / "artifacts/logs"
    (root / "replay").mkdir(parents=True)
    (root / "evals").mkdir(parents=True)

    (root / "replay" / "bad.replay.json").write_text("not-json")
    (root / "evals" / "bad.summary.json").write_text("not-json")

    reader = _make_reader(tmp_path)

    replay = reader.read_replay_json()
    assert replay[0].parsed is False
    assert replay[0].error is not None

    eval_summary = reader.read_eval_summary_json()
    assert eval_summary[0].parsed is False
    assert eval_summary[0].error == "parse_error"
