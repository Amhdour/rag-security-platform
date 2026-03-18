# RAG Security Evaluation & Evidence Conversion Plan

## Purpose

This document converts the repository conceptually from a general security framework into a practical **RAG security evaluation and evidence** workspace centered on executable adversarial tests and machine-verifiable artifacts.

Status labels used below:
- **Implemented**
- **Partially Implemented**
- **Demo-only**
- **Unconfirmed**
- **Planned**

---

## 1) Current-state assessment

### 1.1 What already exists

#### Three-plane architecture baseline
- **Implemented:** Workspace is already structured into runtime (`onyx-main/`), translation (`integration-adapter/`), and governance/observability (`myStarterKit-maindashb-main/`).
- **Implemented:** Integration boundary is artifact-first (audit, replay, eval, launch-gate outputs), not runtime coupling.

#### Adapter pipeline and contracts
- **Implemented:** `integration-adapter` already supports collect/generate/gate workflows with schema validation and fail-closed launch-gate checks for malformed/missing evidence.
- **Partially Implemented:** Exporters support multiple source modes (`live`, `service_api`, `db_backed`, `file_backed`, `fixture_backed`, `synthetic`) with runtime-hook parity still incomplete.
- **Implemented:** Identity/authorization evidence normalization exists (`actor_id`, `tenant_id`, `session_id`, `authz_result`, `decision_basis`, `identity_authz_field_sources`, etc.).

#### Threat model and claim discipline
- **Implemented:** Threat model is present and evidence-centric across prompt injection, retrieval bypass, leakage/exfiltration, tool escalation, MCP abuse, identity spoofing, audit bypass, evidence tampering, and schema drift.
- **Implemented:** Claim status labels are consistently used in integration docs.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.

#### Governance/read-only observability plane
- **Implemented:** Starter Kit has launch-gate, observability, eval normalization, artifact readers, and tests emphasizing read-only behavior.
- **Demo-only:** Demo artifacts are present to support reproducible walkthroughs.

### 1.2 What is missing (gaps to practical evaluation)

#### Adversarial scenario depth
- **Partially Implemented:** Security eval scaffolding exists, but explicit attack-pack modules for all requested threat categories are not yet fully wired end-to-end in adapter-owned CI.
- **Planned:** Dedicated scenario packs with expected outcomes and severity mapping for prompt injection, poisoned retrieval, leakage, unsafe tools.

#### Claim-to-test linkage
- **Partially Implemented:** Threat claims reference controls/evidence, but there is no single claim registry that binds each claim to concrete executable tests and artifact fields.
- **Planned:** Machine-readable control-claim-test matrix used by CI and launch-gate.

#### Evidence automation hardening
- **Partially Implemented:** Artifact generation is automated, but cryptographic tamper evidence and immutable provenance attestations are not complete.
- **Planned:** Signed manifest/digest chain for generated artifacts and stricter evidence freshness/version gates.

#### Observability/audit query ergonomics
- **Partially Implemented:** Artifacts exist, but there is limited standardized “security SLO” reporting (pass rates, drift trends, evidence freshness, unresolved critical findings).
- **Planned:** Deterministic scorecards and trend reports generated from artifacts.

---

## 2) Target-state architecture

## 2.1 Design intent

A practical RAG security evaluation system should operate as:

1. Runtime emits or exposes security-relevant events (Onyx plane).
2. Adapter performs read-only extraction and deterministic normalization.
3. Adapter runs adversarial evaluation modules and writes evidence artifacts.
4. Governance plane consumes artifacts read-only and enforces launch-gate decisions.
5. CI blocks release candidates on integrity failure, schema mismatch, or critical unresolved findings.

## 2.2 Required target modules (exact)

### Module A — `integration_adapter/adversarial/scenario_catalog.py` (**Planned**)
Defines canonical scenario IDs and metadata:
- `scenario_id`
- `threat_category` (`prompt_injection`, `poisoned_retrieval`, `leakage`, `unsafe_tool_usage`)
- `severity` (`low|medium|high|critical`)
- `required_artifact_events`
- `expected_control_outcome`
- `claim_ids`

### Module B — `integration_adapter/adversarial/prompt_injection_suite.py` (**Planned**)
Contains deterministic prompt-injection cases:
- instruction override attempts,
- retrieval-context override attacks,
- tool-coercion prompts,
- policy-bypass phrasing variants.

Outputs:
- per-case verdicts,
- detected policy decision traces,
- expected deny/confirm outcomes.

### Module C — `integration_adapter/adversarial/poisoned_retrieval_suite.py` (**Planned**)
Tests retrieval poisoning and trust-boundary violations:
- malicious chunk insertion fixtures,
- tenant boundary crossing attempts,
- provenance mismatch scenarios.

Outputs:
- retrieval decision evidence coverage,
- allow/deny correctness,
- provenance integrity markers.

### Module D — `integration_adapter/adversarial/leakage_suite.py` (**Planned**)
Validates exfiltration resistance:
- secret extraction prompts,
- cross-tenant leakage prompts,
- sensitive tool-output redirection attempts.

Outputs:
- leakage detection outcomes,
- masked/blocked vs leaked classifications,
- high/critical failure annotations.

### Module E — `integration_adapter/adversarial/unsafe_tool_usage_suite.py` (**Planned**)
Validates risky tool authorization paths:
- unauthorized high-risk tool invocations,
- confirmation bypass attempts,
- delegated identity misuse.

Outputs:
- tool authz trace completeness,
- confirmation enforcement outcomes,
- escalation failure counts.

### Module F — `integration_adapter/claims/claim_registry.yaml` (**Planned**)
Machine-readable claim catalog:
- `claim_id`
- status label
- control description
- expected evidence fields
- required tests
- blocker threshold (e.g., fail if any critical test fails)

### Module G — `integration_adapter/claims/claim_verifier.py` (**Planned**)
Executes claim assertions against generated artifacts:
- checks presence/completeness/schema of required fields,
- validates claim-specific pass criteria,
- emits claim verification report (`claims_verification.json`).

### Module H — `integration_adapter/evidence/sign_manifest.py` (**Planned**)
Creates cryptographic digest manifest for evidence pack:
- SHA256 per artifact,
- signed manifest support (optional key material),
- verification mode used in CI.

### Module I — `integration_adapter/reporting/security_scorecard.py` (**Planned**)
Generates stable summaries for observability:
- attack-category pass/fail rates,
- unresolved high/critical counts,
- evidence freshness,
- schema compatibility status,
- drift delta since prior run.

---

## 3) Threat claims to executable tests (binding model)

Use a deterministic mapping pipeline:

1. Define claim in `claim_registry.yaml` with status label and acceptance criteria.
2. Map claim to one or more adversarial scenarios.
3. Execute scenarios in adapter CI.
4. Verify expected audit/eval/launch-gate evidence fields exist and satisfy rules.
5. Emit machine-readable claim verdicts (`implemented`, `partially_implemented`, `unconfirmed`, etc.) with reasons.

### Example bindings

- `CLM-PI-001` (prompt injection resistance)
  - tests: prompt injection suite cases `PI-*`
  - required evidence: `policy.decision`, `tool.decision`, `authz_result`
  - gate rule: fail on any critical bypass.

- `CLM-RET-002` (retrieval boundary integrity)
  - tests: poisoned retrieval suite cases `PR-*`
  - required evidence: `retrieval.decision`, `tenant_id`, `resource_scope`, provenance markers
  - gate rule: fail on cross-tenant allow without explicit authorization evidence.

- `CLM-LEAK-003` (data leakage prevention)
  - tests: leakage suite `LK-*`
  - required evidence: output classification + deny/mask traces
  - gate rule: fail on high/critical confirmed leak.

- `CLM-TOOL-004` (unsafe tool usage prevention)
  - tests: unsafe tool suite `UT-*`
  - required evidence: `confirmation.required`, `tool.execution_attempt`, decision basis
  - gate rule: fail on unauthorized high-risk execution.

---

## 4) Automatic evidence artifact generation model

## 4.1 Required artifact set (target)

- `audit.jsonl` (normalized runtime security events)
- `replay/*.replay.json` (trace reconstruction)
- `evals/security-*.jsonl` (scenario results)
- `evals/security-*.summary.json` (aggregates)
- `launch_gate/security-readiness-*.json` (blocker verdicts)
- `claims/claims_verification.json` (**Planned**)
- `integrity/manifest.sha256.json` (**Planned**)
- `reporting/security_scorecard.json` and `.md` (**Planned**)

## 4.2 Pipeline execution stages (target)

1. `collect_from_onyx` (read-only extraction)
2. `generate_artifacts` (normalized core outputs)
3. `run_adversarial_evals` (**Planned**)
4. `verify_claims` (**Planned**)
5. `sign_manifest` (**Planned**)
6. `run_launch_gate` (block/fail-closed)
7. `generate_scorecard` (**Planned**)

## 4.3 CI policy gates (target)

Release-quality pipeline should block on:
- schema/version incompatibility,
- integrity verification failure,
- missing critical evidence,
- any unresolved critical adversarial scenario failure,
- claim marked **Implemented** without passing required tests.

---

## 5) Prioritized implementation plan

### Phase 0 — Stabilize baseline (immediate)
1. Keep additive boundary and read-only governance guarantees explicit in docs/tests.
2. Ensure existing adapter CI path and integrity verification are the default local/CI workflow.
3. Publish this conversion plan in root docs and README pointer.

### Phase 1 — Adversarial suites (high priority)
1. Add scenario catalog + deterministic fixtures.
2. Implement prompt injection and poisoned retrieval suites first.
3. Emit normalized eval result contract with severity and claim links.

### Phase 2 — Claim verification (high priority)
1. Add machine-readable claim registry.
2. Add claim verifier consuming eval + audit + launch-gate artifacts.
3. Fail CI when **Implemented** claims lack passing evidence.

### Phase 3 — Evidence integrity & auditability (medium/high)
1. Add signed digest manifest generation/verification.
2. Add tamper-detection checks in launch-gate and CI.
3. Produce immutable evidence index for governance consumption.

### Phase 4 — Observability products (medium)
1. Build security scorecard artifacts from evidence.
2. Add trend reporting (drift, pass-rate deltas, unresolved criticals).
3. Expose scorecard to dashboard read-only views.

### Phase 5 — Runtime parity validation (ongoing)
1. Pin canonical runtime hooks to upstream commits and deployment modes.
2. Expand compatibility matrix with verified hook coverage.
3. Downgrade `Unconfirmed` claims only after environment-backed tests pass.

---

## 6) First five pull requests to make

### PR-1: Add adversarial scenario catalog and contracts
- Files:
  - `integration-adapter/integration_adapter/adversarial/scenario_catalog.py`
  - `integration-adapter/integration_adapter/adversarial/contracts.py`
  - `integration-adapter/tests/test_scenario_catalog.py`
- Outcome: canonical IDs, severity model, threat-category taxonomy, deterministic schema.

### PR-2: Implement prompt injection + poisoned retrieval suites
- Files:
  - `integration-adapter/integration_adapter/adversarial/prompt_injection_suite.py`
  - `integration-adapter/integration_adapter/adversarial/poisoned_retrieval_suite.py`
  - fixtures under `integration-adapter/tests/fixtures/adversarial/`
  - tests under `integration-adapter/tests/test_adversarial_*.py`
- Outcome: executable attack tests with pass/fail outputs and severity.

### PR-3: Add claim registry + claim verifier
- Files:
  - `integration-adapter/integration_adapter/claims/claim_registry.yaml`
  - `integration-adapter/integration_adapter/claims/claim_verifier.py`
  - `integration-adapter/tests/test_claim_verifier.py`
  - docs update in `docs/threat-model/README.md` and `docs/testing-blind-spots.md`
- Outcome: enforceable mapping from threat model claims to tests and evidence.

### PR-4: Add evidence integrity signing + CI enforcement
- Files:
  - `integration-adapter/integration_adapter/evidence/sign_manifest.py`
  - `integration-adapter/integration_adapter/verify_artifact_integrity.py` (integration)
  - CI workflow updates + Makefile target extensions
  - tests for tamper detection
- Outcome: cryptographic tamper-evident evidence pack verification.

### PR-5: Add security scorecard + launch-gate integration
- Files:
  - `integration-adapter/integration_adapter/reporting/security_scorecard.py`
  - launch-gate evaluator integration to include scorecard blockers
  - `myStarterKit-maindashb-main/observability` read-only ingestion support for scorecard artifacts
  - docs update in `docs/adapter-health.md` and observability docs
- Outcome: auditable, trendable security posture report from executable evidence.

---

## 7) Definition of done for conversion

Conversion from “framework repo” to “practical evaluation/evidence repo” is complete when all are true:

1. Every high-level threat claim has executable tests and machine-verifiable evidence bindings.
2. CI fails closed on integrity, schema, and critical adversarial failures.
3. Evidence artifacts are deterministic, reproducible, and tamper-evident.
4. Dashboard remains read-only and consumes only generated artifacts.
5. `Unconfirmed` labels are reduced only via environment-backed verification, not narrative claims.
