# Observability Artifact Readers

This document defines assumptions and safe-failure behavior for the read-only dashboard data layer.

## Scope

- Module: `observability/artifact_readers.py`
- Purpose: parse runtime evidence artifacts for dashboard/explainer use.
- Non-goal: no runtime enforcement, no writes, no policy/tool/retrieval execution.

## Artifact formats detected in this repository

- Audit log: `artifacts/logs/audit.jsonl` (JSONL, one event object per line).
- Replay artifacts: `artifacts/logs/replay/*.replay.json` (JSON object).
- Eval scenario logs: `artifacts/logs/evals/*.jsonl` (JSONL scenario rows).
- Eval summary: `artifacts/logs/evals/*.summary.json` (JSON object).
- Verification summaries: `artifacts/logs/verification/*.summary.json` and `*.summary.md`.
- Launch-gate reports: `artifacts/logs/launch_gate/*.json` (JSON object).

## Safe read behavior

- Missing files return empty/absent normalized results (no exceptions surfaced to callers).
- Malformed JSONL lines are counted and skipped.
- Malformed JSON files return `parsed=false` with parse error metadata.
- All output structures are normalized with explicit fields:
  - `path`
  - `format`
  - `exists`
  - `parsed`
  - `data`
  - `malformed_lines`
  - `error`

## Integration guidance

- This module should be consumed by API/service layers only.
- Keep it read-only and artifact-backed.
- Do not route dashboard requests into enforcement components.
