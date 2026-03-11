# Dashboard Local Demo Mode

This repository supports a **clearly separated local demo mode** for dashboard learning.

## Why demo mode exists

Use demo mode when `artifacts/logs/*` is sparse or missing and you want to study:
- trace timelines and decision outcomes,
- eval run interpretation,
- launch-gate readiness visualization,
- trust-boundary navigation.

## Separation and safety

- Demo artifacts are written to: `artifacts/demo/dashboard_logs/`
- Real runtime artifacts remain under: `artifacts/logs/`
- Do **not** merge/copy demo files into real runtime evidence paths.
- Demo mode includes marker file: `artifacts/demo/dashboard_logs/DEMO_MODE.json`

## Seed demo artifacts

```bash
python scripts/generate_dashboard_demo_artifacts.py
```

The seeded dataset includes at least:
- one successful trace,
- one denied retrieval trace,
- one forbidden tool trace,
- one fallback-to-RAG trace,
- one eval summary (+ scenario jsonl),
- one launch-gate output.

## Run dashboard in demo mode

```bash
DASHBOARD_ARTIFACTS_ROOT=artifacts/demo/dashboard_logs python -m observability.api
```

Open `http://127.0.0.1:8080/`.

The UI banner and system-map metadata should indicate demo mode.
