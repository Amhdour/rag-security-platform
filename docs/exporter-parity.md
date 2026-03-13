# Exporter Parity and Source-Mode Status

This document records real extraction paths, fallback paths, and current parity gaps for each adapter exporter.

## Source-mode vocabulary

**Implemented:** Exporter outputs now include explicit source-mode metadata with one of:

**Implemented:** Source precedence target in adapter exporters is: `live` > `service_api` > `db_backed` > `file_backed` > `fixture_backed` > `synthetic`.

- `live`
- `service_api`
- `db_backed`
- `file_backed`
- `fixture_backed`
- `synthetic`

## Connector inventory exporter

- **Real extraction paths (Partially Implemented):** optional live/db extraction via `onyx.db.connector.fetch_connectors` + DB session (`live` when explicitly enabled, else `db_backed`).
- **Service API extraction (Partially Implemented):** optional JSON API source via `INTEGRATION_ADAPTER_ONYX_CONNECTORS_SERVICE_API`.
- **Fallback/static paths (Implemented):** JSON snapshot from configured/discovered file path.
- **Current parity status:** **mostly real**.
- **Parity gaps (Unconfirmed):** deployment-specific connector credential/status semantics can vary by Onyx version and deployment shape.

## Tool inventory exporter

- **Real extraction paths (Partially Implemented):** optional live/db extraction via `onyx.db.tools.get_tools` + DB session (`live` when explicitly enabled, else `db_backed`).
- **Service API extraction (Partially Implemented):** optional JSON API source via `INTEGRATION_ADAPTER_ONYX_TOOLS_SERVICE_API`.
- **Fallback/static paths (Implemented):** JSON snapshot from configured/discovered file path.
- **Current parity status:** **mostly real**.
- **Parity gaps (Unconfirmed):** risk-tier heuristics for tool metadata may differ from canonical runtime policy semantics.

## MCP inventory exporter

- **Real extraction paths (Partially Implemented):** optional live/db extraction via `onyx.db.mcp.get_all_mcp_servers` + usage count query (`live` when explicitly enabled, else `db_backed`).
- **Service API extraction (Partially Implemented):** optional JSON API source via `INTEGRATION_ADAPTER_ONYX_MCP_SERVICE_API`.
- **Fallback/static paths (Implemented):** JSON snapshot from configured/discovered file path.
- **Current parity status:** **partially real**.
- **Parity gaps (Unconfirmed):** usage count and status semantics can vary with runtime model and DB schema.

## Eval results exporter

- **Real extraction paths (Partially Implemented):** optional runtime config-backed extraction (`onyx.configs.app_configs`) and file-backed eval snapshots.
- **Service API extraction (Partially Implemented):** optional JSON API source via `INTEGRATION_ADAPTER_ONYX_EVALS_SERVICE_API`.
- **Fallback/static paths (Partially Implemented):** runtime config-backed scheduled eval inventory.
- **Current parity status:** **partially real**.
- **Parity gaps (Unconfirmed):** config fallback does not represent full canonical eval-run persistence payloads.

## Runtime events exporter

- **Real extraction paths (Partially Implemented):** live runtime log-backed JSONL feed via `INTEGRATION_ADAPTER_ONYX_RUNTIME_LOG_JSONL` and DB-derived session/tool events.
- **Service API extraction (Partially Implemented):** optional JSONL API source via `INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_SERVICE_API`.
- **Fallback/static paths (Partially Implemented):** DB-derived lifecycle/tool-call event synthesis when JSONL feed absent.
- **Current parity status:** **partially real**.
- **Parity gaps (Unconfirmed):** canonical event-feed parity for all runtime event types is not validated in this workspace.

## Failure-handling guarantees

- **Implemented:** malformed source files generate structured exporter errors/warnings.
- **Implemented:** fallback usage is explicit in output metadata.
- **Implemented:** degraded exporter outputs remain schema-valid with derived field labels.
- **Unconfirmed:** canonical runtime hook not validated in this workspace for full deployment parity.
