# Integration Adapter

Additive adapter translating Onyx runtime concepts into starter-kit-compatible governance artifacts.

## Scope

This package is intentionally non-invasive:
- no Onyx core rewrites,
- no direct starter-kit policy/dashboard mutation paths,
- artifacts as the integration boundary.

## Included modules

- `integration_adapter/config.py` — adapter configuration / artifact root handling.
- `integration_adapter/schemas.py` — normalized event and launch-gate schema models.
- `integration_adapter/artifact_output.py` — writes audit, replay, eval, and launch-gate artifacts.
- `integration_adapter/mappers.py` — runtime payload -> normalized schema mapping.
- `integration_adapter/translators.py` — domain translators (connectors/retrieval/tools/MCP/evals/lifecycle).
- `integration_adapter/exporters.py` — placeholder exporter interfaces for runtime hook wiring.
- `integration_adapter/sample_data.py` — local demo artifact generation.

## Mapping contract

- `docs/onyx-to-starterkit-mapping.md` documents domain-level mappings from Onyx concepts into starter-kit artifacts.

## Runtime hook status

`exporters.py` intentionally contains TODO markers where canonical Onyx runtime hooks still need repository confirmation, including:
- connector inventory source,
- tool inventory source,
- MCP server inventory/usage source,
- eval output source,
- security-relevant runtime event feed.

## Output layout

Generated (runtime or demo) artifacts are written under:

- `artifacts/logs/audit.jsonl`
- `artifacts/logs/replay/*.replay.json`
- `artifacts/logs/evals/*.jsonl`
- `artifacts/logs/evals/*.summary.json`
- `artifacts/logs/launch_gate/*.json`

Artifacts are intentionally ignored from git (`integration-adapter/.gitignore`).

## Quick start

```bash
cd integration-adapter
python -m pytest -q
python -m integration_adapter.sample_data
```
