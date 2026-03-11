"""Generate structured security-boundary metadata for dashboard rendering."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "observability/web/static/security_boundaries.json"


def build_payload() -> dict[str, object]:
    return {
        "schema_version": "1",
        "source_docs": [
            "docs/trust_boundaries.md",
            "docs/architecture.md",
            "docs/integration_boundary_security.md",
            "docs/reviewer_guide.md",
        ],
        "zones": [
            {"id": "client-interface", "name": "Client / Interface", "component_paths": ["app/models.py", "app/context.py"]},
            {"id": "app-orchestrator", "name": "App / Orchestrator", "component_paths": ["app/orchestrator.py"]},
            {"id": "policy-engine", "name": "Policy Engine", "component_paths": ["policies/engine.py", "policies/loader.py", "policies/schema.py"]},
            {"id": "retrieval-service", "name": "Retrieval Service", "component_paths": ["retrieval/service.py"]},
            {"id": "source-registry", "name": "Source Registry / Retriever Backend", "component_paths": ["retrieval/registry.py", "retrieval/contracts.py"]},
            {"id": "model-adapter", "name": "Model Adapter", "component_paths": ["app/modeling.py"]},
            {"id": "tool-router", "name": "Tool Router", "component_paths": ["tools/router.py"]},
            {"id": "tool-registry", "name": "Tool Registry / Executors", "component_paths": ["tools/registry.py", "tools/execution_guard.py", "tools/sandbox.py"]},
            {"id": "telemetry-audit", "name": "Telemetry / Audit pipeline", "component_paths": ["telemetry/audit/contracts.py", "telemetry/audit/events.py", "telemetry/audit/sinks.py", "telemetry/audit/replay.py"]},
            {"id": "artifact-storage", "name": "Artifact storage", "component_paths": ["artifacts/logs/"]},
            {"id": "launch-gate", "name": "Launch Gate", "component_paths": ["launch_gate/engine.py"]},
        ],
        "crossings": [
            {
                "from": "Client / Interface",
                "to": "App / Orchestrator",
                "what_crosses": ["SupportAgentRequest envelope", "request_id/session metadata", "user_text"],
                "control": "Identity validation + policy-gated orchestration entry flow",
                "control_locations": ["app/orchestrator.py", "app/context.py", "identity/models.py"],
                "evidence_artifacts": ["artifacts/logs/audit.jsonl", "artifacts/logs/replay/*.replay.json"],
                "what_can_go_wrong": ["Malformed identity context", "Prompt injection", "Tenant spoofing attempts"],
            },
            {
                "from": "App / Orchestrator",
                "to": "Policy Engine",
                "what_crosses": ["action strings", "actor identity", "request/stage context"],
                "control": "Deny-by-default policy decisions for retrieval/model/tools",
                "control_locations": ["app/orchestrator.py", "policies/engine.py", "policies/loader.py"],
                "evidence_artifacts": ["artifacts/logs/audit.jsonl"],
                "what_can_go_wrong": ["Missing policy checkpoint", "Unknown action allowed by mistake"],
            },
            {
                "from": "App / Orchestrator",
                "to": "Retrieval Service",
                "what_crosses": ["RetrievalQuery", "tenant and source constraints", "top_k bounds"],
                "control": "Fail-closed retrieval mediation with policy constraints",
                "control_locations": ["app/orchestrator.py", "retrieval/service.py", "retrieval/contracts.py"],
                "evidence_artifacts": ["artifacts/logs/audit.jsonl", "artifacts/logs/replay/*.replay.json"],
                "what_can_go_wrong": ["Cross-tenant retrieval", "Unauthorized source usage"],
            },
            {
                "from": "Retrieval Service",
                "to": "Source Registry / Retriever Backend",
                "what_crosses": ["registered source IDs", "document metadata and provenance"],
                "control": "Registered-source checks + trust/provenance validation",
                "control_locations": ["retrieval/service.py", "retrieval/registry.py", "retrieval/contracts.py"],
                "evidence_artifacts": ["artifacts/logs/audit.jsonl", "artifacts/logs/evals/*.jsonl"],
                "what_can_go_wrong": ["Disabled/unregistered source access", "Missing trust metadata"],
            },
            {
                "from": "App / Orchestrator",
                "to": "Model Adapter",
                "what_crosses": ["ModelInput with user text", "retrieved context", "trace/session metadata"],
                "control": "model.generate policy gate before inference",
                "control_locations": ["app/orchestrator.py", "app/modeling.py", "policies/engine.py"],
                "evidence_artifacts": ["artifacts/logs/audit.jsonl", "artifacts/logs/evals/*.jsonl"],
                "what_can_go_wrong": ["Unsafe generation", "Disclosure pressure via prompt injection"],
            },
            {
                "from": "App / Orchestrator",
                "to": "Tool Router",
                "what_crosses": ["ToolInvocation request context", "tool name/action/arguments", "confirmation flag"],
                "control": "SecureToolRouter mediation (allow/deny/require_confirmation)",
                "control_locations": ["app/orchestrator.py", "tools/router.py", "policies/engine.py"],
                "evidence_artifacts": ["artifacts/logs/audit.jsonl", "artifacts/logs/evals/*.jsonl"],
                "what_can_go_wrong": ["Unauthorized tool use", "Policy bypass attempts", "Missing confirmation"],
            },
            {
                "from": "Tool Router",
                "to": "Tool Registry / Executors",
                "what_crosses": ["Mediated tool execution decision", "sanitized execution request"],
                "control": "Execution guard blocks direct non-mediated invocation",
                "control_locations": ["tools/router.py", "tools/registry.py", "tools/execution_guard.py"],
                "evidence_artifacts": ["artifacts/logs/evals/*.jsonl", "artifacts/logs/sandbox/*.json"],
                "what_can_go_wrong": ["Direct executor bypass", "Unsafe high-risk execution path"],
            },
            {
                "from": "App / Orchestrator",
                "to": "Telemetry / Audit pipeline",
                "what_crosses": ["structured audit events", "trace/request/actor/tenant identifiers", "decision metadata"],
                "control": "Typed audit contracts + JSONL sink + replay completeness checks",
                "control_locations": ["telemetry/audit/contracts.py", "telemetry/audit/events.py", "telemetry/audit/sinks.py", "telemetry/audit/replay.py"],
                "evidence_artifacts": ["artifacts/logs/audit.jsonl", "artifacts/logs/replay/*.replay.json"],
                "what_can_go_wrong": ["Missing lifecycle events", "Incomplete replay reconstruction"],
            },
            {
                "from": "Telemetry / Audit pipeline",
                "to": "Artifact storage",
                "what_crosses": ["audit JSONL", "replay artifacts", "eval outputs", "verification summaries", "launch-gate reports"],
                "control": "Artifact serialization contracts and evidence-path conventions",
                "control_locations": ["telemetry/audit/sinks.py", "telemetry/audit/replay.py", "evals/runner.py", "verification/runner.py", "launch_gate/engine.py"],
                "evidence_artifacts": ["artifacts/logs/audit.jsonl", "artifacts/logs/replay/*.replay.json", "artifacts/logs/evals/*.summary.json", "artifacts/logs/verification/*.summary.json", "artifacts/logs/launch_gate/*.json"],
                "what_can_go_wrong": ["Malformed artifacts", "Missing expected evidence files"],
            },
            {
                "from": "Artifact storage",
                "to": "Launch Gate",
                "what_crosses": ["policy/eval/audit/replay/verification evidence"],
                "control": "Machine-checkable release-readiness checks with blockers/residual risks",
                "control_locations": ["launch_gate/engine.py", "verification/runner.py"],
                "evidence_artifacts": ["artifacts/logs/launch_gate/*.json", "artifacts/logs/verification/*.summary.json"],
                "what_can_go_wrong": ["False readiness claim", "Missing evidence interpreted as pass"],
            },
        ],
    }


def main() -> None:
    payload = build_payload()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
