# Exporter Parity and Source-Mode Status

This document records real extraction paths, fallback paths, and current parity gaps for each adapter exporter.

## Source-mode vocabulary

**Implemented:** Exporter outputs now include explicit source-mode metadata with one of:

- `live`
- `db_backed`
- `file_backed`
- `fixture_backed`
- `synthetic`

## Connector inventory exporter

- **Real extraction paths (Partially Implemented):** `onyx.db.connector.fetch_connectors` + DB session.
- **Fallback/static paths (Implemented):** JSON snapshot from configured/discovered file path.
- **Current parity status:** **mostly real**.
- **Parity gaps (Unconfirmed):** deployment-specific connector credential/status semantics can vary by Onyx version and deployment shape.

## Tool inventory exporter

- **Real extraction paths (Partially Implemented):** `onyx.db.tools.get_tools` + DB session.
- **Fallback/static paths (Implemented):** JSON snapshot from configured/discovered file path.
- **Current parity status:** **mostly real**.
- **Parity gaps (Unconfirmed):** risk-tier heuristics for tool metadata may differ from canonical runtime policy semantics.

## MCP inventory exporter

- **Real extraction paths (Partially Implemented):** `onyx.db.mcp.get_all_mcp_servers` + usage count query.
- **Fallback/static paths (Implemented):** JSON snapshot from configured/discovered file path.
- **Current parity status:** **partially real**.
- **Parity gaps (Unconfirmed):** usage count and status semantics can vary with runtime model and DB schema.

## Eval results exporter

- **Real extraction paths (Partially Implemented):** file-backed eval result snapshots.
- **Fallback/static paths (Partially Implemented):** runtime config-backed scheduled eval inventory.
- **Current parity status:** **partially real**.
- **Parity gaps (Unconfirmed):** config fallback does not represent full canonical eval-run persistence payloads.

## Runtime events exporter

- **Real extraction paths (Partially Implemented):** audit JSONL feed and DB-derived session/tool events.
- **Fallback/static paths (Partially Implemented):** DB-derived lifecycle/tool-call event synthesis when JSONL feed absent.
- **Current parity status:** **partially real**.
- **Parity gaps (Unconfirmed):** canonical event-feed parity for all runtime event types is not validated in this workspace.

## Failure-handling guarantees

- **Implemented:** malformed source files generate structured exporter errors/warnings.
- **Implemented:** fallback usage is explicit in output metadata.
- **Implemented:** degraded exporter outputs remain schema-valid with derived field labels.
- **Unconfirmed:** canonical runtime hook not validated in this workspace for full deployment parity.
