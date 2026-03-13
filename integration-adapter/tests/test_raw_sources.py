from __future__ import annotations

import json

from integration_adapter.raw_sources import (
    SourceReadError,
    load_json_records,
    load_json_records_from_url,
    load_jsonl_records,
    load_jsonl_records_from_url,
)


def test_load_json_records_accepts_list_and_rows_wrapper(tmp_path) -> None:
    list_path = tmp_path / "list.json"
    list_path.write_text(json.dumps([{"id": 1}, {"id": 2}, "bad"]), encoding="utf-8")

    wrapped_path = tmp_path / "wrapped.json"
    wrapped_path.write_text(json.dumps({"rows": [{"id": 3}, {"id": 4}, 5]}), encoding="utf-8")

    assert load_json_records(list_path) == [{"id": 1}, {"id": 2}]
    assert load_json_records(wrapped_path) == [{"id": 3}, {"id": 4}]


def test_load_json_records_rejects_invalid_json_shape(tmp_path) -> None:
    scalar_path = tmp_path / "scalar.json"
    scalar_path.write_text("123", encoding="utf-8")

    with __import__("pytest").raises(SourceReadError):
        load_json_records(scalar_path)


def test_load_jsonl_records_skips_malformed_lines(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        "\n".join([json.dumps({"a": 1}), "{bad", json.dumps([1, 2]), json.dumps({"b": 2})]),
        encoding="utf-8",
    )

    assert load_jsonl_records(path) == [{"a": 1}, {"b": 2}]


def test_load_json_records_from_url(monkeypatch) -> None:
    monkeypatch.setattr("integration_adapter.raw_sources._load_url_text", lambda _url, timeout_seconds=5.0: '[{"id": 1}, {"id": 2}]')
    rows = load_json_records_from_url("https://onyx.local/api/connectors")
    assert rows == [{"id": 1}, {"id": 2}]


def test_load_jsonl_records_from_url_skips_malformed(monkeypatch) -> None:
    payload = '{"a":1}\n{bad\n[1,2]\n{"b":2}'
    monkeypatch.setattr("integration_adapter.raw_sources._load_url_text", lambda _url, timeout_seconds=5.0: payload)
    rows = load_jsonl_records_from_url("https://onyx.local/api/events")
    assert rows == [{"a": 1}, {"b": 2}]


def test_load_json_records_from_url_raises_on_malformed_json(monkeypatch) -> None:
    monkeypatch.setattr("integration_adapter.raw_sources._load_url_text", lambda _url, timeout_seconds=5.0: '{bad')
    with __import__("pytest").raises(SourceReadError):
        load_json_records_from_url("https://onyx.local/api/connectors")
