from integration_adapter.mappers import map_connector_inventory, map_runtime_event


def test_missing_inventory_fields_get_defaults() -> None:
    rows = map_connector_inventory([{}])
    assert rows[0].name == "unknown_connector"
    assert rows[0].status == "unknown"


def test_missing_runtime_fields_are_tolerated_with_defaults() -> None:
    event = map_runtime_event({"event_type": "fallback.event"})
    assert event.request_id == "unknown-request"
    assert event.actor_id == "unknown-actor"
    assert event.persona_or_agent_id == "unavailable"
    assert event.authz_result == "unavailable"
