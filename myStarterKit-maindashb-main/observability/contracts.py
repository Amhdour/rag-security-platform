"""Contracts for read-only dashboard API payloads."""

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class NormalizedAuditEvent:
    """Stable event shape used by dashboard clients."""

    event_id: str
    trace_id: str
    request_id: str
    actor_id: str
    tenant_id: str
    event_type: str
    created_at: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class TraceSummary:
    """Summary row for one trace."""

    trace_id: str
    request_id: str
    actor_id: str
    tenant_id: str
    started_at: str | None
    ended_at: str | None
    event_count: int
    event_types: Sequence[str]


@dataclass(frozen=True)
class EvalRunSummary:
    """Summary descriptor for one eval run."""

    run_id: str
    suite_name: str
    passed: bool
    total: int
    passed_count: int
    summary_path: str


@dataclass(frozen=True)
class ReplaySummary:
    """Summary descriptor for one replay artifact."""

    replay_id: str
    trace_id: str
    request_id: str
    path: str
