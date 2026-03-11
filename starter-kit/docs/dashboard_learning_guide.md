# Dashboard Learning Guide

Use this guide to master the repository using the implemented read-only dashboard.

The dashboard is **observability-only**:
- it reads artifacts,
- it does not execute tools,
- it does not mutate policy,
- it is not part of runtime enforcement.

---

## 0) Start the dashboard

### Real artifacts
```bash
python -m observability.api
```

### Local demo mode (if real artifacts are sparse)
```bash
python scripts/generate_dashboard_demo_artifacts.py
DASHBOARD_ARTIFACTS_ROOT=artifacts/demo/dashboard_logs python -m observability.api
```

Open: `http://127.0.0.1:8080/`.

---

## 1) Inspect the architecture

1. Open **Overview**.
2. Review metric cards (traces, replay artifacts, eval runs, launch-gate status, verification status).
3. Review the **Readiness card** (status, passed checks, blockers, residual risks, missing evidence, latest artifact timestamp).
4. Open **Security Boundaries / Trust Zones**.
5. Read the trust-zone table and boundary crossing table:
   - what crosses each boundary,
   - control in place,
   - code location,
   - evidence artifact,
   - what can go wrong.

Goal: understand where controls live and what artifacts prove behavior.

---

## 2) Follow one trace end-to-end

1. Open **Trace Explorer**.
2. Filter by `trace_id` or `request_id` if needed.
3. Select a trace (click trace id).
4. In **Trace Detail**, read the **Timeline (primary view)** from top to bottom.

Focus on event order and stage transitions (lifecycle → policy/retrieval/model/tools → terminal outcome).

---

## 3) Inspect policy decisions

1. In **Trace Detail**, inspect **Policy / Model decisions**.
2. Review `event_type`, `decision_outcome`, and `reason` columns.
3. Confirm policy decisions are visible before key runtime stages.

---

## 4) Inspect retrieval boundary decisions

1. In **Trace Detail**, inspect **Retrieval decisions**.
2. Check retrieval-specific events and reasons.
3. For denied traces, confirm retrieval-stage denial appears in timeline and final disposition.

---

## 5) Inspect tool routing decisions

1. In **Trace Detail**, inspect **Tool decisions**.
2. Check allow/deny/confirmation outcomes and reasons.
3. Use timeline payload details when you need event-level context.

---

## 6) Inspect deny/fallback/error paths

1. In **Trace Explorer**, filter by `event_type`:
   - `deny.event`
   - `fallback.event`
   - `error.event`
2. Open each trace in **Trace Detail**.
3. Compare terminal behavior using:
   - timeline,
   - **Deny / Fallback / Error** panel,
   - final disposition.

---

## 7) Inspect replay artifacts

1. Open **Replay Viewer**.
2. Select a replay artifact.
3. Review `trace_id`, `request_id`, path, and replay payload.
4. Cross-check the same trace in **Trace Detail** (linked replay section).

---

## 8) Inspect eval results

1. Open **Evals**.
2. Select an eval run.
3. Review:
   - run summary and counts,
   - high/critical failures,
   - baseline category coverage,
   - scenario outcomes with control/boundary links.
4. Validate repository-grounded baseline categories shown by the page:
   - prompt injection,
   - malicious retrieval content,
   - cross-tenant retrieval attempt,
   - unsafe disclosure attempt,
   - forbidden/unauthorized tool usage,
   - policy bypass attempt,
   - fallback-to-RAG verification,
   - auditability verification.

---

## 9) Inspect launch-gate readiness

1. Open **Launch Gate**.
2. Review:
   - overall status (`go`, `conditional_go`, `no_go`),
   - latest artifact timestamp,
   - passed checks,
   - blockers,
   - residual risks,
   - missing evidence.
3. Interpret this as release-readiness evidence, not live enforcement behavior.

---

## Practical study loop

1. Start from **Overview**.
2. Drill into one trace.
3. Cross-check replay.
4. Compare eval failures and boundary links.
5. Confirm launch-gate readiness impact.

Repeat with:
- one successful trace,
- one denied trace,
- one fallback trace,
- one error trace.


## Fast reviewer walkthrough

For a first pass, use this sequence:

1. Open **Overview** to check launch status + evidence/integrity summaries.
2. Open **Trace Explorer** and filter to one security-relevant trace.
3. Open **Trace Detail** and review timeline + decisions + related artifacts.
4. Open **Evals** and review high/critical failures.
5. Open **Launch Gate** and verify blockers/residual risks.

If screenshots are not generated yet, keep placeholders in review docs:
- `docs/images/dashboard-overview.png`
- `docs/images/dashboard-trace-explorer.png`
- `docs/images/dashboard-trace-detail.png`
- `docs/images/dashboard-evals.png`
- `docs/images/dashboard-launch-gate.png`
