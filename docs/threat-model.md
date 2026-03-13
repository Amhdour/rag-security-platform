# Threat Model — `rag-security-platform-main` (Integration Workspace)

This threat model covers the three-plane integration boundary used in this repository:

- **Runtime plane:** `onyx-main/`
- **Translation plane:** `integration-adapter/`
- **Governance/evidence plane:** `myStarterKit-maindashb-main/`

**Implemented:** This document is implementation-backed and evidence-centric.
**Unconfirmed:** It does **not** claim standalone production runtime enforcement proof.

Status labels:
- **Implemented**
- **Partially Implemented**
- **Demo-only**
- **Unconfirmed**
- **Planned**

---

## 1) Prompt injection

- **Threat description:** Malicious prompt content tries to coerce unsafe retrieval/tool behavior and produce misleading downstream evidence.
- **Affected plane:** Runtime (primary), Adapter (evidence normalization).
- **Relevant controls:**
  - Normalized audit events preserve lifecycle/policy/retrieval/tool decisions.
  - Launch-gate checks required audit lifecycle presence and eval evidence presence.
- **Current evidence source:**
  - `integration-adapter/artifacts/logs/audit.jsonl`
  - `integration-adapter/artifacts/logs/evals/*.jsonl`
  - `integration-adapter/artifacts/logs/launch_gate/security-readiness-*.json`
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** Artifact presence does not prove runtime prompt defenses were enforced for every request.
- **Next engineering action:** Add pinned-runtime prompt-injection trace fixtures and adapter contract tests against them.

## 2) Retrieval boundary bypass

- **Threat description:** Retrieval returns out-of-scope or cross-tenant sources without trustworthy deny/allow evidence.
- **Affected plane:** Runtime and Adapter.
- **Relevant controls:**
  - `retrieval.decision` normalization with `tenant_id`, `resource_scope`, `authz_result`, `decision_basis`.
  - Launch-gate lifecycle and schema-validity checks.
- **Current evidence source:**
  - `audit.jsonl` (`retrieval.decision` rows)
  - launch-gate machine output
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** **Unconfirmed:** canonical production retrieval hook parity across deployment modes.
- **Next engineering action:** Validate retrieval hook mapping from pinned real runtime traces.

## 3) Data exfiltration

- **Threat description:** Sensitive data leaves allowed boundary through tool/MCP calls or weak output controls.
- **Affected plane:** Runtime, Adapter, Governance.
- **Relevant controls:**
  - Normalized `tool.decision` and `tool.execution_attempt` evidence.
  - Launch-gate fail-closed checks for malformed/missing evidence.
- **Current evidence source:**
  - `audit.jsonl`
  - launch-gate checks `artifact_completeness`, `artifact_schema_validity`, `critical_failures_or_blockers`
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** Evidence quality checks do not prove runtime exfiltration prevention.
- **Next engineering action:** Add explicit exfiltration eval scenarios with high/critical severity and contract fixtures.

## 4) Tool escalation

- **Threat description:** Request is escalated to higher-risk tool behavior without sufficient authorization/confirmation evidence.
- **Affected plane:** Runtime and Adapter.
- **Relevant controls:**
  - `tool.decision` and `confirmation.required` normalization.
  - Identity/authz fields (`authz_result`, `decision_basis`, `tool_invocation_id`, `delegation_chain`).
- **Current evidence source:**
  - `audit.jsonl`
  - launch-gate critical/high eval failure check
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** **Unconfirmed:** canonical runtime tool-policy checkpoint semantics.
- **Next engineering action:** Capture real tool authorization traces and assert field-level mapping contract.

## 5) MCP privilege abuse

- **Threat description:** MCP server/tool use exceeds intended privilege, trust domain, or policy.
- **Affected plane:** Runtime and Adapter.
- **Relevant controls:**
  - MCP inventory export and classification checks.
  - MCP usage representation through `tool.execution_attempt` events.
- **Current evidence source:**
  - `mcp_servers.inventory.json`
  - `audit.jsonl`
  - launch-gate check `mcp_inventory_classified`
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** **Unconfirmed:** production MCP usage semantics may differ from fallback representations.
- **Next engineering action:** Validate MCP usage semantics against pinned runtime data and tighten mapping docs/tests.

## 6) Identity spoofing

- **Threat description:** Actor/session/persona context is forged or ambiguous, weakening attribution trust.
- **Affected plane:** Runtime and Adapter.
- **Relevant controls:**
  - Normalized identity/authz fields.
  - Per-field source attribution: `sourced` / `derived` / `unavailable`.
  - Schema validation of identity source markers.
- **Current evidence source:**
  - `audit.jsonl` identity/authz fields and `identity_authz_field_sources`
  - adapter tests for identity mapping and missing fields
- **Current implementation status:** **Implemented** (adapter mapping), **Unconfirmed** (runtime authenticity guarantees).
- **Gaps:** No cryptographic identity attestation in workspace artifacts.
- **Next engineering action:** Add immutable/signed identity context inputs where runtime supports them.

## 7) Audit bypass

- **Threat description:** Required lifecycle/audit evidence is missing, malformed, or silently skipped.
- **Affected plane:** Adapter and Governance.
- **Relevant controls:**
  - Launch-gate `required_audit_events_present` (fail-closed).
  - Launch-gate `artifact_schema_validity` (fail-closed).
- **Current evidence source:**
  - `launch_gate/security-readiness-*.json`
  - `audit.jsonl`
- **Current implementation status:** **Implemented**.
- **Gaps:** Artifact checks cannot prove runtime emitted every event in real time.
- **Next engineering action:** Add runtime-side emission/integrity counters and correlate with adapter ingestion counts.

## 8) Evidence tampering

- **Threat description:** Generated evidence artifacts are modified/replaced after generation to influence governance outcomes.
- **Affected plane:** Adapter and Governance.
- **Relevant controls:**
  - Artifact completeness and schema-validity fail-closed checks.
  - Read-only dashboard ingestion.
- **Current evidence source:**
  - launch-gate machine/markdown outputs
  - expected artifact tree under `artifacts/logs`
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** No cryptographic signature/attestation pipeline for artifacts in this workspace.
- **Next engineering action:** Add digest/signature manifest and optional immutable storage flow.

## 9) Schema drift

- **Threat description:** Upstream runtime shape changes degrade adapter mapping semantics without immediate detection.
- **Affected plane:** Adapter.
- **Relevant controls:**
  - Defensive mapping defaults.
  - Adapter schema/malformed-input tests.
  - Launch-gate `artifact_schema_validity`.
- **Current evidence source:**
  - adapter test suite under `integration-adapter/tests/`
  - launch-gate output
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** **Unconfirmed:** pinned runtime hook/version parity coverage is incomplete.
- **Next engineering action:** Introduce explicit input contract versioning and compatibility automation.

---

## Control-to-Evidence Mapping (implementation-backed)

| Control area | Adapter schema/code anchor | Artifact evidence | Launch-gate check(s) | Demo evidence path |
|---|---|---|---|---|
| Normalized audit schema + identity/authz attribution | `integration-adapter/integration_adapter/schemas.py` (`NormalizedAuditEvent`), `integration-adapter/integration_adapter/mappers.py` (`map_runtime_event`) | `integration-adapter/artifacts/logs/audit.jsonl` | `artifact_schema_validity`, `required_audit_events_present` | `integration-adapter/artifacts/logs/demo_scenario.report.json` + `audit.jsonl` |
| Retrieval boundary decision evidence | `integration-adapter/integration_adapter/translators.py` (`translate_retrieval_events`) | `audit.jsonl` (`retrieval.decision`) | `required_audit_events_present` | `demo_scenario.report.json` (`story_steps`, `event_type_coverage`) |
| Tool authz / escalation evidence | `integration-adapter/integration_adapter/translators.py` (`translate_tool_decisions`) | `audit.jsonl` (`tool.decision`, `confirmation.required`) | `artifact_schema_validity`, `critical_failures_or_blockers` | `demo_scenario.report.json` (`story_steps`) |
| MCP inventory + usage evidence | `integration-adapter/integration_adapter/exporters.py` + `translate_mcp_usage` | `mcp_servers.inventory.json`, `audit.jsonl` (`tool.execution_attempt`) | `mcp_inventory_classified`, `artifact_schema_validity` | `demo_scenario.report.json` (`real_vs_synthetic.mcp_inventory`) |
| Eval evidence availability + severity signaling | `integration-adapter/integration_adapter/pipeline.py`, `integration-adapter/integration_adapter/artifact_output.py` | `evals/*.jsonl`, `evals/*.summary.json` | `eval_results_present`, `critical_failures_or_blockers`, `artifact_schema_validity` | `integration-adapter/artifacts/logs/evals/demo-e2e.jsonl` |
| Artifact integrity/completeness | `integration-adapter/integration_adapter/launch_gate_evaluator.py` | `artifacts/logs` tree and launch-gate outputs | `artifact_completeness`, `artifact_schema_validity` | `demo_scenario.report.json` (`missing_outputs`) |
| Evidence-vs-control honesty | `integration-adapter/integration_adapter/launch_gate_evaluator.py` output fields (`evidence_status`, `control_assessment`) | `launch_gate/security-readiness-*.json` | output semantics (machine + markdown) | demo launch-gate output in `integration-adapter/artifacts/logs/launch_gate/` |

---

## Scope notes

- **Implemented:** This threat model is specific to this integration workspace and artifact contracts.
- **Unconfirmed:** canonical runtime hook parity across all deployment topologies is not fully validated here.
- **Implemented:** Claims above are restricted to implementation that is present and test-backed in this repository.
