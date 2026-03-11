import pytest

from integration_adapter.mappers import map_runtime_event


def test_malformed_event_type_is_rejected() -> None:
    event = map_runtime_event({"event_type": "malformed", "request_id": "r", "trace_id": "t", "actor_id": "a", "tenant_id": "ten"})
    with pytest.raises(ValueError):
        event.to_dict()
