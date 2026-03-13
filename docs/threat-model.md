# Threat Model — rag-security-platform-main (Integration Workspace)

This threat model is scoped to the three-plane integration architecture:
- **Onyx runtime plane** (`onyx-main/`)
- **Integration adapter plane** (`integration-adapter/`)
- **Governance/evidence plane** (`myStarterKit-maindashb-main/`)

**Implemented:** This model focuses on threats that can be reasoned about using implementation that exists in this workspace.

Status labels:
- **Implemented**
- **Partially Implemented**
- **Demo-only**
- **Unconfirmed**
- **Planned**

---

## 1) Prompt injection

- **Threat description:** Malicious prompt content attempts to induce unsafe tool calls, policy bypass, or misleading evidence traces.
- **Affected plane:** Runtime (primary), Adapter (secondary evidence fidelity).
- **Relevant controls:**
  - Adapter event normalization preserves policy/tool/retrieval decisions as audit evidence.
  - Launch-gate checks for required lifecycle events and eval evidence presence.
  - Demo/eval artifact generation includes adversarial-style scenarios in evidence rows.
- **Current evidence source:**
  - `artifacts/logs/audit.jsonl`
  - `artifacts/logs/evals/*.jsonl`
  - `artifacts/logs/launch_gate/security-readiness-*.json`
- **Current implementation status:** **Partially Implemented** (artifact-side evidence checks exist; runtime enforcement proof remains outside adapter).
- **Gaps:** Runtime prompt-safety enforcement is not proven by adapter artifacts alone.
- **Planned next engineering action:** Add environment-backed contract tests against real runtime prompt-injection traces and pin source hooks.

## 2) Retrieval boundary bypass

- **Threat description:** Cross-tenant or out-of-scope retrieval access occurs without proper denial/control evidence.
- **Affected plane:** Runtime and Adapter.
- **Relevant controls:**
  - Normalized retrieval decision events (`retrieval.decision`) with `tenant_id`, `resource_scope`, `authz_result`, `decision_basis`.
  - Launch-gate required audit event checks.
- **Current evidence source:**
  - `audit.jsonl` normalized events
  - demo report story steps and realism gaps
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** Canonical production retrieval hook parity is **Unconfirmed** across deployment modes.
- **Planned next engineering action:** Validate retrieval decision hook mapping from real Onyx traces and add fixture-based regression tests.

## 3) Data exfiltration

- **Threat description:** Sensitive data leaves trust boundary via tools, MCP endpoints, or malformed output channels.
- **Affected plane:** Runtime, Adapter, Governance.
- **Relevant controls:**
  - Tool/MCP decision + execution-attempt evidence in normalized audit stream.
  - Launch-gate completeness/schema checks fail closed on malformed evidence.
- **Current evidence source:**
  - `audit.jsonl` (`tool.decision`, `tool.execution_attempt`)
  - `launch_gate` checks `artifact_completeness`, `artifact_schema_validity`.
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** Exfiltration prevention is not proven by artifact presence; only evidence quality is evaluated.
- **Planned next engineering action:** Add eval scenarios + critical severity mapping specifically for exfiltration attempts and verify runtime deny traces.

## 4) Tool escalation

- **Threat description:** Request escalates to high-risk tool execution without proper authz or confirmation semantics.
- **Affected plane:** Runtime and Adapter.
- **Relevant controls:**
  - Normalized `tool.decision` and `confirmation.required` events.
  - Identity/authz mapping fields (`authz_result`, `decision_basis`, `tool_invocation_id`, `delegation_chain`).
- **Current evidence source:**
  - `audit.jsonl`
  - launch-gate critical/high eval failure check.
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** Canonical runtime tool-policy checkpoint wiring remains **Unconfirmed**.
- **Planned next engineering action:** Capture/pin real tool decision and confirmation traces from runtime and add contract fixtures.

## 5) MCP privilege abuse

- **Threat description:** MCP server/tool access exceeds intended privilege or trust domain.
- **Affected plane:** Runtime and Adapter.
- **Relevant controls:**
  - MCP inventory export + classification (`mcp_servers.inventory.json`).
  - MCP usage represented via normalized `tool.execution_attempt` events.
  - Launch-gate MCP classification check.
- **Current evidence source:**
  - `mcp_servers.inventory.json`
  - `audit.jsonl`
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** Production MCP usage semantics are **Unconfirmed** and may be fallback-derived in this workspace.
- **Planned next engineering action:** Validate canonical MCP usage counters/decision semantics against live runtime and tighten mapping contracts.

## 6) Identity spoofing

- **Threat description:** Forged actor/session/persona context appears in runtime path without trustworthy provenance.
- **Affected plane:** Runtime and Adapter.
- **Relevant controls:**
  - Normalized identity/authz fields with per-field source attribution (`sourced`/`derived`/`unavailable`).
  - Schema validation of normalized events.
- **Current evidence source:**
  - `audit.jsonl` fields: `actor_id`, `tenant_id`, `session_id`, `persona_or_agent_id`, `delegation_chain`, `identity_authz_field_sources`.
- **Current implementation status:** **Implemented** (adapter mapping layer), **Unconfirmed** (runtime trust guarantees).
- **Gaps:** Source attribution does not cryptographically prove identity authenticity.
- **Planned next engineering action:** Add signed identity context or immutable provenance markers from runtime hooks where feasible.

## 7) Audit bypass

- **Threat description:** Critical request lifecycle or decision events are missing/invalid in evidence stream.
- **Affected plane:** Adapter and Governance.
- **Relevant controls:**
  - Launch-gate `required_audit_events_present` fail-closed behavior.
  - Schema-validity checks on `audit.jsonl`.
- **Current evidence source:**
  - `launch_gate/security-readiness-*.json` checks list
  - `audit.jsonl`
- **Current implementation status:** **Implemented**.
- **Gaps:** Does not guarantee runtime emitted every event in real-time; validates only available artifacts.
- **Planned next engineering action:** Add runtime-side event emission SLO checks and ingestion integrity counters.

## 8) Evidence tampering

- **Threat description:** Artifact files are edited/deleted/replaced post-generation to influence governance outcome.
- **Affected plane:** Adapter and Governance.
- **Relevant controls:**
  - Launch-gate completeness + schema-validity checks fail closed.
  - Read-only dashboard consumption model.
- **Current evidence source:**
  - `launch_gate` outputs with blockers/residual risks
  - artifact directory structure checks.
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** No cryptographic signing or immutable storage guarantees in this workspace.
- **Planned next engineering action:** Add artifact digest manifest/signature and optional immutable object-store write path.

## 9) Schema drift

- **Threat description:** Runtime payload changes silently break adapter mapping or degrade evidence semantics.
- **Affected plane:** Adapter.
- **Relevant controls:**
  - Mapper defaults + defensive parsing.
  - Schema validation tests and malformed-input tests.
  - Launch-gate schema-validity check.
- **Current evidence source:**
  - adapter tests
  - launch-gate `artifact_schema_validity`
- **Current implementation status:** **Partially Implemented**.
- **Gaps:** Upstream hook parity/version pinning remains **Unconfirmed**.
- **Planned next engineering action:** Introduce explicit input contract versioning and compatibility matrix automation.

---

## Control-to-Evidence Mapping Table

| Control / Checkpoint | Adapter implementation | Artifact evidence path | Launch-gate check linkage | Demo evidence path |
|---|---|---|---|---|
| Normalized audit event schema (identity/authz fields) | `integration_adapter/schemas.py` `NormalizedAuditEvent`; `integration_adapter/mappers.py` `map_runtime_event` | `integration-adapter/artifacts/logs/audit.jsonl` | `artifact_schema_validity`; `required_audit_events_present` | `integration-adapter/artifacts/logs/demo_scenario.report.json` + `audit.jsonl` |
| Retrieval decision normalization | `integration_adapter/translators.py` `translate_retrieval_events` | `audit.jsonl` (`retrieval.decision`) | `required_audit_events_present` (lifecycle presence baseline) | `demo_scenario.report.json.story_steps` |
| Tool authz decision normalization | `integration_adapter/translators.py` `translate_tool_decisions` | `audit.jsonl` (`tool.decision`, `confirmation.required`) | `artifact_schema_validity`; `critical_failures_or_blockers` | `demo_scenario.report.json.story_steps` |
| MCP inventory + usage representation | `integration_adapter/exporters.py` MCP exporter + runtime events exporter; `translate_mcp_usage` | `mcp_servers.inventory.json`, `audit.jsonl` (`tool.execution_attempt`) | `mcp_inventory_classified`; `artifact_schema_validity` | `demo_scenario.report.json.real_vs_synthetic.mcp_inventory` |
| Eval evidence normalization/output | `integration_adapter/pipeline.py` + `artifact_output.py` eval writing | `evals/*.jsonl`, `evals/*.summary.json` | `eval_results_present`; `critical_failures_or_blockers`; `artifact_schema_validity` | `evals/demo-e2e.jsonl` |
| Artifact integrity/completeness | `integration_adapter/launch_gate_evaluator.py` | full `artifacts/logs` tree | `artifact_completeness`; `artifact_schema_validity` | demo run writes + verifies `missing_outputs=[]` |
| Evidence vs control honesty | `integration_adapter/launch_gate_evaluator.py` output fields | `launch_gate/security-readiness-*.json` (`evidence_status`, `control_assessment`) | output-level semantics | `launch_gate/security-readiness-*.json` from demo run |

---

## Scope boundary notes

- This model is evidence-centric for the integration workspace and does **not** claim standalone production enforcement guarantees.
- **Unconfirmed:** canonical runtime hook parity across all deployment topologies remains to be validated with pinned upstream runtime commits.
