from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


REQUIRED_EVENT_TYPES = {
    "request.start",
    "policy.decision",
    "retrieval.decision",
    "tool.decision",
    "tool.execution_attempt",
    "confirmation.required",
    "deny.event",
    "fallback.event",
    "request.end",
    "error.event",
}

IDENTITY_AUTHZ_SOURCE_VALUES = {"sourced", "derived", "unavailable"}
IDENTITY_AUTHZ_SOURCE_KEYS = {
    "actor_id",
    "tenant_id",
    "session_id",
    "persona_or_agent_id",
    "tool_invocation_id",
    "delegation_chain",
    "decision_basis",
    "resource_scope",
    "authz_result",
}


@dataclass
class NormalizedAuditEvent:
    event_id: str
    trace_id: str
    request_id: str
    event_type: str
    actor_id: str
    tenant_id: str
    event_payload: Mapping[str, Any] = field(default_factory=dict)
    session_id: str = "adapter-session"
    actor_type: str = "assistant_runtime"

    # Normalized identity/authz evidence fields
    persona_or_agent_id: str = "unavailable"
    tool_invocation_id: str = "unavailable"
    delegation_chain: list[str] = field(default_factory=list)
    decision_basis: str = "unavailable"
    resource_scope: str = "unavailable"
    authz_result: str = "unavailable"

    # Marks whether each field is sourced from runtime, derived by adapter, or unavailable.
    # Values: sourced | derived | unavailable
    identity_authz_field_sources: Mapping[str, str] = field(default_factory=dict)

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> None:
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.trace_id:
            raise ValueError("trace_id is required")
        if not self.request_id:
            raise ValueError("request_id is required")
        if self.event_type not in REQUIRED_EVENT_TYPES:
            raise ValueError(f"unsupported event_type: {self.event_type}")
        if not self.actor_id:
            raise ValueError("actor_id is required")
        if not self.tenant_id:
            raise ValueError("tenant_id is required")
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.actor_type:
            raise ValueError("actor_type is required")
        if not isinstance(self.delegation_chain, list):
            raise ValueError("delegation_chain must be a list")
        if any(not isinstance(item, str) for item in self.delegation_chain):
            raise ValueError("delegation_chain must contain only strings")
        for key, value in self.identity_authz_field_sources.items():
            if key not in IDENTITY_AUTHZ_SOURCE_KEYS:
                raise ValueError(f"identity_authz_field_sources contains unsupported key: {key}")
            if value not in IDENTITY_AUTHZ_SOURCE_VALUES:
                raise ValueError(
                    f"identity_authz_field_sources[{key}] must be one of {sorted(IDENTITY_AUTHZ_SOURCE_VALUES)}"
                )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class InventoryRecord:
    domain: str
    record_id: str
    name: str
    status: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class LaunchGateSummary:
    generated_at: str
    status: str
    checks_passed: int
    checks_total: int
    blockers: list[str]
    residual_risks: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Onyx-side source models (normalized by adapter, not direct runtime imports)
@dataclass
class OnyxRetrievalRecord:
    request_id: str
    trace_id: str
    tenant_id: str
    actor_id: str
    source_id: str
    query: str = ""
    allowed: bool = True
    reason: str = ""
    top_k: int = 0


@dataclass
class OnyxToolDecisionRecord:
    request_id: str
    trace_id: str
    tenant_id: str
    actor_id: str
    tool_name: str
    decision: str
    reason: str = ""
    requires_confirmation: bool = False


@dataclass
class OnyxMCPUsageRecord:
    request_id: str
    trace_id: str
    tenant_id: str
    actor_id: str
    mcp_server: str
    tool_name: str
    decision: str
    reason: str = ""


@dataclass
class OnyxEvalResultRecord:
    run_id: str
    scenario_id: str
    category: str
    severity: str
    passed: bool
    details: str = ""


# Starter-kit artifact row models
@dataclass
class StarterKitEvalRow:
    scenario_id: str
    category: str
    severity: str
    outcome: str
    passed: bool
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
