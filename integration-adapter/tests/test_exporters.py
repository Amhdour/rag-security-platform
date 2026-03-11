from integration_adapter.exporters import (
    ConnectorInventoryExporter,
    EvalResultsExporter,
    MCPInventoryExporter,
    RuntimeEventsExporter,
    ToolInventoryExporter,
)


def test_placeholder_exporters_return_empty_lists() -> None:
    assert ConnectorInventoryExporter().export() == []
    assert ToolInventoryExporter().export() == []
    assert MCPInventoryExporter().export() == []
    assert EvalResultsExporter().export() == []
    assert RuntimeEventsExporter().export() == []
