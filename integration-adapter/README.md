# Integration Adapter

**Implemented:** Additive adapter translating Onyx runtime concepts into starter-kit-compatible governance artifacts.

## Scope

- **Implemented:** No Onyx core rewrites.
- **Implemented:** No direct starter-kit policy/dashboard mutation paths.
- **Implemented:** Artifact files are the integration boundary.

## Implementation status (claims audit)

### Implemented
- **Implemented:** Artifact pipeline commands:
  - `collect_from_onyx`
  - `generate_artifacts`
  - `run_launch_gate`
  - `demo_scenario`
- **Implemented:** Schema validation for normalized events.
- **Implemented:** Artifact writing for audit/replay/eval/launch-gate.
- **Implemented:** Evidence-based launch-gate evaluator with fail-closed behavior on malformed/missing evidence.

### Partially Implemented
- **Partially Implemented:** Exporters support file-backed extraction and optional direct Onyx DB extraction where runtime imports/session are available.

### Demo-only
- **Demo-only:** Demo scenario can synthesize schema-valid runtime events/inventory/evals when live data is unavailable.

### Unconfirmed
- **Unconfirmed:** Canonical production runtime hook locations for all deployment modes (especially event feed semantics and multi-provider eval shape).

### Planned
- **Planned:** Environment-specific live-hook validation and commit-pinned runtime compatibility matrix updates.


## Exporter runtime-hook status

- **Implemented:** Exporter source precedence target is `live` > `service_api` > `db_backed` > `file_backed` > `fixture_backed` > `synthetic`.

- **Connector inventory exporter**: **Partially Implemented** (optional Onyx live/db read via `onyx.db.connector.fetch_connectors`; optional service API source via `INTEGRATION_ADAPTER_ONYX_CONNECTORS_SERVICE_API`; file-backed fallback).
- **Tool inventory exporter**: **Partially Implemented** (optional Onyx live/db read via `onyx.db.tools.get_tools`; optional service API source via `INTEGRATION_ADAPTER_ONYX_TOOLS_SERVICE_API`; file-backed fallback).
- **MCP inventory exporter**: **Partially Implemented** (optional Onyx live/db read via `onyx.db.mcp.get_all_mcp_servers` with ToolCall-derived usage counts; optional service API source via `INTEGRATION_ADAPTER_ONYX_MCP_SERVICE_API`; file-backed fallback).
- **Eval results exporter**: **Partially Implemented** (runtime config-backed scheduled eval inventory via `onyx.configs.app_configs`, optional service API source via `INTEGRATION_ADAPTER_ONYX_EVALS_SERVICE_API`, and file-backed snapshot extraction).
- **Runtime events exporter**: **Partially Implemented** (prefers live runtime log-backed JSONL via `INTEGRATION_ADAPTER_ONYX_RUNTIME_LOG_JSONL`, then optional service API JSONL via `INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_SERVICE_API`, then ChatSession/ToolCall DB-derived fallback events, then file-backed JSONL).

> Unconfirmed: canonical runtime hook not validated in this workspace for deployment-wide parity.


## Normalized identity and authorization evidence

**Implemented:** Normalized audit events include identity/authorization evidence fields:
- **Implemented:** `actor_id`
- **Implemented:** `tenant_id`
- **Implemented:** `session_id`
- **Implemented:** `persona_or_agent_id`
- **Implemented:** `tool_invocation_id`
- **Implemented:** `delegation_chain`
- **Implemented:** `decision_basis`
- **Implemented:** `resource_scope`
- **Implemented:** `authz_result`
- **Implemented:** `identity_authz_field_sources` (per-field: `sourced`, `derived`, or `unavailable`)

Proven vs inferred guidance:
- **Proven in artifacts:** a field value exists in the normalized artifact and indicates whether it was sourced/derived/unavailable.
- **Inferred/Derived:** adapter inferred value from adjacent payload semantics (e.g., `resource_scope` from `source_id` or `tool_name`).
- **Unconfirmed:** canonical runtime hook parity across deployment modes is not established by this workspace alone.
- **Implemented:** See `../docs/identity-authz-evidence.md` for explicit proven vs inferred semantics and launch-gate authz provenance quality policy.

**Partially Implemented:** Best-effort Onyx concept mapping used by adapter:
- **Partially Implemented:** `session_id` uses `session_id` or Onyx `chat_session_id` when present, else derives from `trace_id`.
- **Partially Implemented:** `persona_or_agent_id` uses `persona_or_agent_id`, `persona_id`, or `agent_id`.
- **Partially Implemented:** `tool_invocation_id` uses `tool_invocation_id` or Onyx `tool_call_id`.
- **Partially Implemented:** `delegation_chain` uses runtime `delegation_chain` when present, else derives from `delegated_by` when available.

**Unconfirmed:** canonical runtime hook not validated in this workspace for all deployment modes.


## Defensibility documentation boundary

For close-review claim hygiene across the workspace:

- **Implemented:** See `../docs/defensibility-claims.md` for a strict split of
  - demonstrated in code,
  - demonstrated in tests,
  - conceptual only,
  - future work.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.

## Included modules

- `integration_adapter/config.py` — adapter configuration / artifact root handling.
- `integration_adapter/schemas.py` — normalized event and launch-gate schema models.
- `integration_adapter/artifact_output.py` — writes audit, replay, eval, and launch-gate artifacts.
- `integration_adapter/mappers.py` — runtime payload -> normalized schema mapping.
- `integration_adapter/translators.py` — domain translators.
- `integration_adapter/exporters.py` — read-only exporters from Onyx-facing sources.
- `integration_adapter/raw_sources.py` — JSON/JSONL source readers and path discovery.
- `integration_adapter/pipeline.py` — collection + artifact generation + launch-gate orchestration.
- `integration_adapter/collect_from_onyx.py` — CLI entrypoint.
- `integration_adapter/generate_artifacts.py` — CLI entrypoint.
- `integration_adapter/run_launch_gate.py` — CLI entrypoint.
- `integration_adapter/demo_scenario.py` — end-to-end demo runner.
- `integration_adapter/artifact_retention.py` — profile-aware artifact retention planning and cleanup CLI.
- `integration_adapter/health_report.py` — operator-focused health summary CLI (json/text/metrics formats).
- `integration_adapter/control_matrix.py` — auto-generates reviewer control matrix from adversarial scenario packs + default harness mappings.
- `integration_adapter/evidence_report.py` — generates conservative evidence summary outputs (markdown/json/optional html) from artifacts and control mappings.
- `integration_adapter/launch_gate_bridge.py` — bridges eval results into a launch-gate style verdict with conservative baseline comparison semantics.

## Threat model package

- **Implemented:** Reviewer-facing threat model package is published under `../docs/threat-model/` with sections for system overview, assets, trust boundaries, threat actors, attack paths, control points, residual risks, and an end-to-end secure pipeline walkthrough.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.

## Mapping contract

- `docs/onyx-to-starterkit-mapping.md`

## Upstream provenance lock

- **Implemented:** Workspace-level upstream provenance is tracked in `../docs/upstream-provenance.lock.json`.
- **Implemented:** Validate lock-file shape via `make provenance-check` (repo root) or `python ../scripts/validate_upstream_provenance_lock.py` (from `integration-adapter/`).
- **Unconfirmed:** Runtime/governance upstream commit pins remain unavailable when nested `.git` metadata is absent.

## Schema versioning and compatibility

- **Implemented:** Source, normalized, artifact bundle, and launch-gate schema versions are explicit and enforced.
- **Implemented:** Compatibility policy outcomes are `allowed`, `warn_only`, and `blocked` with deterministic behavior.
- **Implemented:** Artifact generation blocks on incompatible major-version contracts and warns on forward minor drift.
- **Implemented:** See `../docs/schema-versioning.md` for policy and upgrade/downgrade guidance.

## Exporter source modes and parity

- **Implemented:** Exporters emit explicit source-mode metadata (`live`, `db_backed`, `file_backed`, `fixture_backed`, `synthetic`).
- **Implemented:** Fallback usage, warnings, errors, and derived/defaulted fields are included in exporter outputs.
- **Partially Implemented:** Real extraction paths are available for connector/tool/MCP/runtime-event DB hooks, with deployment-dependent parity caveats.
- **Implemented:** See `../docs/exporter-parity.md` for exporter-by-exporter parity status and gaps.

## Adapter health telemetry

- **Implemented:** Adapter emits `artifacts/logs/adapter_health/adapter_run_summary.json` for run-level observability.
- **Implemented:** Health metrics include source modes, fallback count, parse failures, schema validation failures, artifact write failures, launch-gate failure reasons, stale evidence detections, and partial extraction warnings.
- **Implemented:** Health run status is explicit: `success`, `degraded_success`, or `failed_run`.
- **Implemented:** Operator summary CLI is available via `python -m integration_adapter.health_report --artifacts-root artifacts/logs --format text`.
- **Implemented:** See `../docs/adapter-health.md` for details.

## Artifact integrity safeguards

- **Implemented:** Adapter writes `artifact_integrity.manifest.json` with per-file SHA-256 and size metadata.
- **Implemented:** Integrity modes: `hash_only` (default) and optional `signed_manifest` (HMAC-SHA256).
- **Implemented:** Launch-gate fail-closes on missing/invalid integrity manifests, hash mismatches, and signed-manifest verification failures.
- **Implemented:** Verify hash-only mode with `python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs`.
- **Implemented:** Verify signed mode with `python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs --integrity-mode signed_manifest --signing-key-path /secure/path/signing.key`.
- **Unconfirmed:** no cryptographic non-repudiation/signature chain is implemented in this workspace.
- **Implemented:** See `../docs/artifact-integrity.md`.


## Artifact retention lifecycle policy

**Implemented:** Artifact lifecycle management is profile-aware and operator-invoked via `integration_adapter.artifact_retention`.

Safety behavior:
- **Implemented:** default mode is dry-run (no deletion).
- **Implemented:** destructive deletion requires `--apply`.
- **Implemented:** required baseline artifacts are preserved.
- **Implemented:** files referenced by `artifact_integrity.manifest.json` are preserved.
- **Implemented:** latest successful launch-gate run(s) are preserved with `--keep-latest-successful-runs` (default `1`).

See `../docs/artifact-retention-policy.md` for family windows, profile defaults, and environment overrides.

## Negative-path security validation

- **Implemented:** Deterministic failure/adversarial-path coverage is documented in `../docs/negative-path-validation.md`.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.
- **Planned:** stronger anti-tamper guarantees via signed artifact attestations.

## Launch-gate policy

- **Implemented:** Launch-gate evaluates evidence quality (not only presence) including freshness, compatibility, source quality, exporter degradation, identity/authz fields, and threat-control mapping completeness.
- **Implemented:** Critical stale/missing evidence fails closed; non-critical degradation is surfaced as warnings.
- **Implemented:** See `../docs/launch-gate-policy.md` for thresholds and PASS/WARN/FAIL policy.

## Contract fixtures

- **Implemented:** Pinned fixture sets for connector/tool/MCP/eval/runtime-event contracts live under `tests/fixtures/onyx_contracts/`.
- **Implemented:** Fixture provenance and sanitization metadata is tracked in `tests/fixtures/onyx_contracts/fixture_manifest.json`.
- **Implemented:** See `../docs/fixture-catalog.md` for lineage labels (`real-derived`, `sanitized`, `synthetic`, `Demo-only`) and regeneration guidance.

## Packaging and command entrypoints

- **Implemented:** Install in editable mode with dev tooling:

```bash
cd integration-adapter
python -m pip install -e .[dev]
```

- **Implemented:** `pyproject.toml` publishes CLI entrypoints:
  - `integration-adapter-collect`
  - `integration-adapter-generate`
  - `integration-adapter-gate`
  - `integration-adapter-evidence`
  - `integration-adapter-validate`
  - `integration-adapter-ci-smoke`

## Environment profiles and safeguards

- **Implemented:** Supported profiles are `demo`, `dev`, `ci`, and `prod_like`.
- **Implemented:** Profiles define allowed source modes, freshness thresholds, logging verbosity expectations, and synthetic fallback policy.
- **Implemented:** `prod_like` blocks unsafe combinations (demo mode, synthetic runtime evidence, stale/missing critical evidence, and fallback usage).
- **Implemented:** See `../docs/environment-profiles.md` for policy details and examples.

## Configuration validation

- **Implemented:** Validate artifacts root and currently configured source inputs:

```bash
cd integration-adapter
python -m integration_adapter.validate_config
```

- **Implemented:** Strict mode fails when required source env vars are missing or malformed:

```bash
cd integration-adapter
python -m integration_adapter.validate_config --strict-sources
```

- **Implemented:** No hidden required state in non-strict mode; absent source env vars are surfaced as warnings and adapter may use file/db/demo fallbacks.

## Operational runbook

| Goal | Command | Success signal | Failure signal |
|---|---|---|---|
| Validate config/profile | `python -m integration_adapter.validate_config --profile dev` | JSON `"status": "pass"` | non-zero exit + `config validation failed` |
| Generate artifacts | `python -m integration_adapter.generate_artifacts --demo --profile demo --artifacts-root artifacts/logs` | prints contract/audit/launch-gate/integrity paths | non-zero exit + `artifact generation failed` |
| Verify integrity | `python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs` | JSON `"ok": true` | non-zero exit + missing/hash mismatch details |
| Retention dry-run | `python -m integration_adapter.artifact_retention --dry-run --profile ci --artifacts-root artifacts/logs` | JSON candidate list, `deleted_count: 0` | non-zero exit for invalid profile/args |
| Retention apply | `python -m integration_adapter.artifact_retention --apply --profile ci --artifacts-root artifacts/logs` | JSON `deleted_count >= 0` + explicit completion message | non-zero exit for invalid profile/args |
| Health summary | `python -m integration_adapter.health_report --artifacts-root artifacts/logs --format text` | concise run status + counters + integrity/gate/retention summary | non-zero exit for invalid args |
| Evaluate gate | `python -m integration_adapter.run_launch_gate --profile demo --artifacts-root artifacts/logs` | launch-gate JSON path printed | non-zero exit + `launch gate failed` |

Profile behavior summary:
- **Implemented:** `demo` allows synthetic/fixture fallback for reproducible demos.
- **Implemented:** `dev` allows fallback with warnings for iterative local use.
- **Implemented:** `ci` allows deterministic smoke checks without external services.
- **Implemented:** `prod_like` blocks synthetic fallback and stale/missing critical evidence.

Real vs synthetic vs derived:
- **Implemented:** `source_mode` on inventories/events distinguishes `live`, `db_backed`, `file_backed`, `fixture_backed`, `synthetic`.
- **Implemented:** identity/authz `identity_authz_field_sources` marks each field as `sourced`, `derived`, or `unavailable`.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.

## Output layout

**Implemented:** Generated artifacts are written under:
- **Implemented:** `artifacts/logs/audit.jsonl`
- **Implemented:** `artifacts/logs/replay/*.replay.json`
- **Implemented:** `artifacts/logs/evals/*.jsonl`
- **Implemented:** `artifacts/logs/evals/*.summary.json`
- **Implemented:** `artifacts/logs/launch_gate/*.json`
- **Implemented:** `artifacts/logs/launch_gate/*.md`

## Quick start

```bash
cd integration-adapter
python -m pytest -q
```

## CI automation and local parity

**Implemented:** Workspace CI is defined at `../.github/workflows/ci.yml` and runs on `push` and `pull_request`.

**Implemented:** CI checks for adapter verification are:
1. `python scripts/validate_upstream_provenance_lock.py`
2. `cd integration-adapter && pytest -q`
3. `cd integration-adapter && python -m integration_adapter.ci_smoke --profile ci --artifacts-root artifacts/logs-ci-smoke`
4. `cd integration-adapter && python -m integration_adapter.generate_artifacts --demo --profile ci --artifacts-root artifacts/logs-ci-smoke`
5. `cd integration-adapter && python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs-ci-smoke`

Run the same checks locally from repo root:

```bash
python scripts/validate_upstream_provenance_lock.py
cd integration-adapter && pytest -q
cd integration-adapter && python -m integration_adapter.ci_smoke --profile ci --artifacts-root artifacts/logs-ci-smoke
cd integration-adapter && python -m integration_adapter.generate_artifacts --demo --profile ci --artifacts-root artifacts/logs-ci-smoke
cd integration-adapter && python -m integration_adapter.verify_artifact_integrity --artifacts-root artifacts/logs-ci-smoke
```

**Implemented:** CI blockers are any non-zero exits from the checks above, including contract/provenance failures, smoke output verification failures, and artifact integrity/hash mismatches.

**Demo-only:** `integration_adapter.ci_smoke` intentionally relies on deterministic demo-compatible flows and local fixtures rather than requiring live runtime services.

## Runnable evidence pipeline

Preferred step-by-step commands:

```bash
cd integration-adapter
python -m integration_adapter.collect_from_onyx
python -m integration_adapter.generate_artifacts
python -m integration_adapter.run_launch_gate
```

Optional path override for reproducible runs:

```bash
cd integration-adapter
python -m integration_adapter.generate_artifacts --demo --profile demo --artifacts-root artifacts/logs
python -m integration_adapter.run_launch_gate --profile demo --artifacts-root artifacts/logs
```

One-command pipeline from repo root:

```bash
make evidence
```

Step-by-step pipeline from repo root:

```bash
make evidence-step
```

Alternative one-command pipeline from adapter directory:

```bash
cd integration-adapter
python -m integration_adapter.evidence_pipeline
```

Force demo mode:

```bash
make evidence-demo
```

Step-by-step demo mode:

```bash
make evidence-step-demo
```

Or:

```bash
cd integration-adapter
python -m integration_adapter.evidence_pipeline --demo --profile demo
```

CI-friendly smoke command (demo, no external services):

```bash
cd integration-adapter
python -m integration_adapter.ci_smoke
```

Environment overrides:
- `INTEGRATION_ADAPTER_ARTIFACTS_ROOT`
- `INTEGRATION_ADAPTER_PROFILE`
- `INTEGRATION_ADAPTER_ONYX_CONNECTORS_JSON`
- `INTEGRATION_ADAPTER_ONYX_TOOLS_JSON`
- `INTEGRATION_ADAPTER_ONYX_MCP_JSON`
- `INTEGRATION_ADAPTER_ONYX_EVALS_JSON`
- `INTEGRATION_ADAPTER_ONYX_RUNTIME_EVENTS_JSONL`

## Launch-gate criteria (evidence-based)

`python -m integration_adapter.run_launch_gate` checks:
1. **Implemented:** connector inventory presence
2. **Implemented:** tool inventory classification quality
3. **Implemented:** MCP inventory classification quality
4. **Implemented:** required audit lifecycle events
5. **Implemented:** eval evidence presence
6. **Implemented:** artifact completeness
7. **Implemented:** critical/high eval failures
8. **Implemented:** artifact schema validity (fail-closed on malformed evidence)

Status semantics:
- **Implemented:** `go` means all checks pass
- **Implemented:** `conditional_go` means no fails and one or more warnings
- **Implemented:** `no_go` means one or more failures

Machine-readable output includes:
- **Implemented:** per-check status and evidence
- **Implemented:** `blockers` (fail) and `residual_risks` (warn) separated
- **Implemented:** `evidence_status.present` and `evidence_status.incomplete`
- **Implemented:** `control_assessment.enforced`, `control_assessment.proven`, `control_assessment.not_proven`
- **Implemented:** `decision_breakdown.blocker_count` and `decision_breakdown.warning_count`

**Implemented:** Human-readable output (`launch_gate/*.md`) includes the same distinction with explicit **Blockers (fail)** and **Residual risks (warn)** sections.

Limitations:
- **Implemented:** Evaluates evidence presence/quality only.
- **Unconfirmed:** Does **not** independently prove production runtime enforcement.

## End-to-end demo scenario

```bash
cd integration-adapter
python -m integration_adapter.demo_scenario
```

Or from repo root:

```bash
make demo
```

**Implemented:** The demo report at `artifacts/logs/demo_scenario.report.json` explicitly labels per-domain and per-story-step `real` vs `synthetic` sources and includes `remaining_realism_gaps` with UNCONFIRMED runtime-hook caveats.

**Implemented:** See `../docs/demo-scenario.md` for full steps, expected outputs, and realism gaps.

## Testing notes

- **Implemented:** Adapter tests include unit and integration-style coverage.
- **Unconfirmed:** Untestable runtime assumptions are documented in `../docs/testing-blind-spots.md`.


## Practical adversarial harness

- **Implemented:** Compact scenario harness covers prompt injection, poisoned retrieval, policy bypass attempts, and unsafe tool-use attempts.
- **Implemented:** Each scenario is scored as `pass`, `fail`, or `warn`.
- **Implemented:** Harness emits machine-readable JSONL + summary JSON and a markdown report under `evals/`.
- **Implemented:** Retrieval poisoning fixtures cover embedded malicious instructions, misleading authoritative content, hidden overrides, context conflicts, and integrity downgrade attempts (`tests/fixtures/adversarial/retrieval_poisoning/`).
- **Implemented:** Data leakage / unsafe output fixtures cover direct sensitive disclosure, tool-result leakage, policy-conflicting outputs, unsafe restricted summaries, and context carry-through leakage (`tests/fixtures/adversarial/output_leakage/`).
- **Partially Implemented:** Tool-use scenario is `warn` when no tool inventory is discovered in the artifact root.

Run a quick demo:

```bash
cd integration-adapter
python -m integration_adapter.adversarial_harness --artifacts-root artifacts/logs --demo
```

Run retrieval poisoning scenario pack:

```bash
cd integration-adapter
python -m integration_adapter.adversarial_harness \
  --artifacts-root artifacts/logs \
  --scenario-file tests/fixtures/adversarial/retrieval_poisoning/scenarios.json
```


Run output leakage scenario pack:

```bash
cd integration-adapter
python -m integration_adapter.adversarial_harness \
  --artifacts-root artifacts/logs \
  --scenario-file tests/fixtures/adversarial/output_leakage/scenarios.json
```


## Reviewer control matrix

- **Implemented:** Auto-generated reviewer-friendly matrix maps threat -> control -> implementation module -> test coverage -> evidence artifact.
- **Partially Implemented:** Matrix coverage follows maintained adversarial scenario packs and default harness scenarios.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.

Generate/update the matrix:

```bash
make control-matrix
```

Direct command:

```bash
cd integration-adapter
python -m integration_adapter.control_matrix --output-doc ../docs/control-matrix.md
```


## Automated evidence summary workflow

- **Implemented:** Generates evidence summary outputs from current artifacts and control matrix mappings without claiming unverified production enforcement.
- **Implemented:** Output formats include markdown and JSON, with optional HTML rendering.
- **Partially Implemented:** Content fidelity depends on available artifacts in the configured artifacts root.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.

Generate reports:

```bash
make evidence-summary
```

Direct command:

```bash
cd integration-adapter
python -m integration_adapter.evidence_report \
  --artifacts-root artifacts/logs \
  --output-md ../docs/evidence-summary.md \
  --output-json ../docs/evidence-summary.json \
  --output-html ../docs/evidence-summary.html
```


## Launch-gate bridge verdict workflow

- **Implemented:** Produces a launch-gate style verdict from current evaluation artifacts and control mappings.
- **Implemented:** Verdict explicitly reports core control presence, adversarial-test posture, remaining risks, and relative baseline-safety signal.
- **Partially Implemented:** Baseline safety conclusion is artifact-relative and not a production runtime enforcement proof.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.

Generate bridge verdict:

```bash
make launch-gate-bridge
```

Direct command:

```bash
cd integration-adapter
python -m integration_adapter.launch_gate_bridge \
  --artifacts-root artifacts/logs \
  --output-json ../docs/launch-gate-bridge.example.json \
  --output-md ../docs/launch-gate-bridge.example.md
```
