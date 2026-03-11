const state = {
  view: "overview",
  traces: [],
  selectedTraceId: "",
  replayItems: [],
  selectedReplayId: "",
  evalRuns: [],
  selectedEvalId: "",
  launchGate: null,
  verification: null,
  systemMap: null,
  overview: null,
  boundaryData: null,
  loading: true,
  errors: [],
  filters: {
    request_id: "",
    trace_id: "",
    tenant_id: "",
    actor_id: "",
    event_type: "",
    final_outcome: "",
    decision_class: "",
    date_from: "",
    date_to: "",
    replay_only: "",
    partial_only: "",
    security_only: "",
    sort_by: "started_at",
    sort_order: "desc",
  },
};

const PRIMARY_TIMELINE_ORDER = [
  "request.start",
  "policy.decision",
  "retrieval.decision",
  "tool.execution_attempt",
  "tool.decision",
  "confirmation.required",
  "deny.event",
  "fallback.event",
  "error.event",
  "request.end",
];

init();

function init() {
  bindTabs();
  render();
  refreshAll();
}

function bindTabs() {
  document.querySelectorAll("#tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      state.view = button.dataset.view;
      document.querySelectorAll("#tabs button").forEach((node) => node.classList.remove("active"));
      button.classList.add("active");
      render();
    });
  });
}

async function refreshAll() {
  state.loading = true;
  state.errors = [];
  render();
  await Promise.all([
    loadOverview(),
    loadTraces(),
    loadReplay(),
    loadEvals(),
    loadLaunchGate(),
    loadVerification(),
    loadSystemMap(),
    loadBoundaryData(),
  ]);
  state.loading = false;
  render();
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${text}`);
  }
  return response.json();
}

function pushError(message) {
  state.errors.push(message);
}

function renderAlerts() {
  const node = document.getElementById("alerts");
  const demo = state.systemMap && state.systemMap.demo_mode;
  const banners = [];
  if (demo) {
    banners.push(`<div class="panel warning">Demo mode: ${escapeHtml(state.systemMap.artifacts_root || "artifacts/demo")}</div>`);
  }
  if (state.errors.length) {
    banners.push(`<div class="panel error">${state.errors.map((item) => `<div>${escapeHtml(item)}</div>`).join("")}</div>`);
  }
  node.innerHTML = banners.join("");
}

async function loadOverview() {
  try {
    state.overview = await fetchJson("/api/overview");
  } catch (error) {
    state.overview = null;
    pushError(`Overview unavailable: ${error.message}`);
  }
}

async function loadTraces() {
  try {
    const params = new URLSearchParams();
    Object.entries(state.filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    const payload = await fetchJson(`/api/traces?${params.toString()}`);
    state.traces = payload.items || [];
    if (!state.selectedTraceId && state.traces.length > 0) {
      state.selectedTraceId = state.traces[0].trace_id || state.traces[0].request_id;
    }
  } catch (error) {
    state.traces = [];
    pushError(`Traces unavailable: ${error.message}`);
  }
}

async function loadReplay() {
  try {
    const payload = await fetchJson("/api/replay");
    state.replayItems = payload.items || [];
    if (!state.selectedReplayId && state.replayItems.length > 0) {
      state.selectedReplayId = state.replayItems[0].replay_id;
    }
  } catch (error) {
    state.replayItems = [];
    pushError(`Replay list unavailable: ${error.message}`);
  }
}

async function loadEvals() {
  try {
    const payload = await fetchJson("/api/evals");
    state.evalRuns = payload.items || [];
    if (!state.selectedEvalId && state.evalRuns.length > 0) {
      state.selectedEvalId = state.evalRuns[0].run_id;
    }
  } catch (error) {
    state.evalRuns = [];
    pushError(`Eval list unavailable: ${error.message}`);
  }
}

async function loadLaunchGate() {
  try {
    state.launchGate = await fetchJson("/api/launch-gate/latest");
  } catch (_error) {
    state.launchGate = null;
  }
}

async function loadVerification() {
  try {
    state.verification = await fetchJson("/api/verification/latest");
  } catch (_error) {
    state.verification = null;
  }
}

async function loadSystemMap() {
  try {
    state.systemMap = await fetchJson("/api/system-map");
  } catch (_error) {
    state.systemMap = null;
  }
}


async function loadBoundaryData() {
  try {
    state.boundaryData = await fetchJson('/static/security_boundaries.json');
  } catch (_error) {
    state.boundaryData = null;
  }
}

function render() {
  renderAlerts();
  if (state.loading) {
    document.getElementById("content").innerHTML = '<div class="panel">Loading dashboard data…</div>';
    return;
  }
  if (state.view === "overview") return renderOverview();
  if (state.view === "traces") return renderTraceExplorer();
  if (state.view === "trace-detail") return renderTraceDetail();
  if (state.view === "boundary-map") return renderBoundaryMap();
  if (state.view === "evals") return renderEvals();
  if (state.view === "launch-gate") return renderLaunchGate();
  if (state.view === "replay") return renderReplay();
}

function renderOverview() {
  const overview = state.overview;
  const launchStatus = state.launchGate ? state.launchGate.status : "unavailable";
  const verificationStatus = state.verification ? state.verification.status : "unavailable";

  document.getElementById("content").innerHTML = `
    <div class="panel">
      <h2>Overview</h2>
      <p class="muted">Read-only operational dashboard for runtime evidence. This UI does not execute tools, mutate policies, or alter enforcement.</p>
    </div>
    <div class="grid">
      ${metricCard("Traces", overview?.counts?.traces ?? state.traces.length)}
      ${metricCard("Replay artifacts", overview?.counts?.replay_artifacts ?? state.replayItems.length)}
      ${metricCard("Eval runs", overview?.counts?.eval_runs ?? state.evalRuns.length)}
      ${metricCard("Launch Gate", statusChip(launchStatus))}
      ${metricCard("Verification", statusChip(verificationStatus))}
    </div>
    <div class="panel">
      <h3>Readiness card</h3>
      ${renderOverviewReadinessCard(overview?.readiness_card || null)}
    </div>
    <div class="panel">
      <h3>Connected evidence summary</h3>
      ${renderConnectedEvidenceSummary(overview?.connected_evidence_summary || null)}
    </div>
    <div class="panel">
      <h3>Artifact integrity status</h3>
      ${renderArtifactIntegrity(overview?.artifact_integrity || null)}
    </div>
    <div class="panel">
      <h3>Evidence sources</h3>
      ${renderEvidenceSources(overview?.evidence_sources || [], {includeLegend: true})}
    </div>
    <div class="panel">
      <h3>Runtime flow</h3>
      <ol>
        <li>Request normalization and trace context creation.</li>
        <li>Policy checks gate retrieval/model/tool routing stages.</li>
        <li>Retrieval enforces tenant/source boundaries.</li>
        <li>Tool mediation enforces allow/deny/confirmation controls.</li>
        <li>Telemetry emits auditable and replay-friendly events.</li>
        <li>Evals and launch-gate artifacts drive readiness outputs.</li>
      </ol>
    </div>
  `;
}

function renderOverviewReadinessCard(card) {
  if (!card || !card.status) {
    return '<p class="empty">No launch-gate readiness artifact available.</p>';
  }
  return `<div class="grid">
    ${metricCard('Status', statusChip(card.status))}
    ${metricCard('Passed checks', `${escapeHtml(String(card.passed_checks ?? 0))}/${escapeHtml(String(card.total_checks ?? 0))}`)}
    ${metricCard('Blockers', card.blockers ?? 0)}
    ${metricCard('Residual risks', card.residual_risks ?? 0)}
    ${metricCard('Missing evidence', card.missing_evidence ?? 0)}
    ${metricCard('Latest artifact timestamp', escapeHtml(String(card.latest_artifact_timestamp || 'unknown')))}
  </div>`;
}

function renderTraceExplorer() {
  document.getElementById("content").innerHTML = `
    <div class="panel">
      <h2>Trace Explorer</h2>
      <p class="muted">Filter normalized traces. Select a trace to inspect event order and decisions.</p>
      ${renderTraceFilters()}
    </div>
    <div class="panel">${renderTraceTable(state.traces)}</div>
    <div class="panel"><h3>Evidence source</h3>${renderEvidenceSources(traceExplorerSources())}</div>
  `;
  bindTraceFilters();
  bindTraceLinks();
}

function renderTraceFilters() {
  return `
    <div class="filters">
      <input data-filter="trace_id" placeholder="trace_id" value="${escapeHtml(state.filters.trace_id)}" />
      <input data-filter="request_id" placeholder="request_id" value="${escapeHtml(state.filters.request_id)}" />
      <input data-filter="tenant_id" placeholder="tenant_id" value="${escapeHtml(state.filters.tenant_id)}" />
      <input data-filter="actor_id" placeholder="actor_id" value="${escapeHtml(state.filters.actor_id)}" />
      <input data-filter="event_type" placeholder="event_type" value="${escapeHtml(state.filters.event_type)}" />
      <select data-filter="final_outcome">
        ${renderSelectOptions(state.filters.final_outcome, ["", "completed", "denied", "fallback", "error", "in_progress", "blocked"], "final outcome")}
      </select>
      <select data-filter="decision_class">
        ${renderSelectOptions(state.filters.decision_class, ["", "allow", "deny", "fallback", "error"], "decision class")}
      </select>
      <input data-filter="date_from" placeholder="date_from (ISO)" value="${escapeHtml(state.filters.date_from)}" />
      <input data-filter="date_to" placeholder="date_to (ISO)" value="${escapeHtml(state.filters.date_to)}" />
      <label><input type="checkbox" data-filter-bool="replay_only" ${state.filters.replay_only ? "checked" : ""}/> replay only</label>
      <label><input type="checkbox" data-filter-bool="partial_only" ${state.filters.partial_only ? "checked" : ""}/> partial only</label>
      <label><input type="checkbox" data-filter-bool="security_only" ${state.filters.security_only ? "checked" : ""}/> security decisions only</label>
      <select data-filter="sort_by">
        ${renderSelectOptions(state.filters.sort_by, ["started_at", "updated_at", "event_count", "final_outcome"], "sort by")}
      </select>
      <select data-filter="sort_order">
        ${renderSelectOptions(state.filters.sort_order, ["desc", "asc"], "sort order")}
      </select>
      <button id="trace-filter-apply">Apply</button>
      <button id="trace-filter-clear">Clear</button>
    </div>
  `;
}

function bindTraceFilters() {
  document.getElementById("trace-filter-apply")?.addEventListener("click", async () => {
    document.querySelectorAll("input[data-filter], select[data-filter]").forEach((node) => {
      state.filters[node.dataset.filter] = node.value.trim();
    });
    document.querySelectorAll("input[data-filter-bool]").forEach((node) => {
      state.filters[node.dataset.filterBool] = node.checked ? "true" : "";
    });
    await loadTraces();
    renderTraceExplorer();
  });
  document.getElementById("trace-filter-clear")?.addEventListener("click", async () => {
    state.filters = {
      request_id: "", trace_id: "", tenant_id: "", actor_id: "", event_type: "", final_outcome: "", decision_class: "",
      date_from: "", date_to: "", replay_only: "", partial_only: "", security_only: "", sort_by: "started_at", sort_order: "desc",
    };
    await loadTraces();
    renderTraceExplorer();
  });
}

function renderTraceTable(rows) {
  if (!rows.length) {
    return '<p class="empty">No traces found for current artifacts/filters.</p>';
  }
  return `<table><thead><tr><th>trace_id</th><th>request_id</th><th>actor_id</th><th>tenant_id</th><th>events</th><th>final</th><th>flags</th><th>started</th></tr></thead><tbody>
    ${rows
      .map(
        (row) => `<tr>
          <td><button class="link-btn trace-link" data-trace-id="${escapeHtml(row.trace_id || row.request_id || "")}">${escapeHtml(row.trace_id || "(none)")}</button></td>
          <td>${escapeHtml(row.request_id || "")}</td>
          <td>${escapeHtml(row.actor_id || "")}</td>
          <td>${escapeHtml(row.tenant_id || "")}</td>
          <td>${renderEventTypeChips(row.event_types || [])}</td>
          <td>${statusChip(row.final_outcome || "unknown")}</td>
          <td>${renderTraceFlags(row)}</td>
          <td>${escapeHtml(row.started_at || row.updated_at || "")}</td>
        </tr>`
      )
      .join("")}
  </tbody></table>`;
}

function renderTraceFlags(row) {
  const flags = [];
  if (row.has_replay) flags.push('<span class="chip ok">replay</span>');
  if (row.partial_trace) flags.push('<span class="chip fallback">partial</span>');
  if (row.security_relevant) flags.push('<span class="chip deny">security</span>');
  return flags.join('') || '<span class="empty">none</span>';
}

function renderSelectOptions(selected, values, placeholder) {
  return values.map((value, idx) => {
    const label = value || placeholder;
    return `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
  }).join('');
}

function bindTraceLinks() {
  document.querySelectorAll(".trace-link").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedTraceId = node.dataset.traceId;
      state.view = "trace-detail";
      document.querySelectorAll("#tabs button").forEach((n) => n.classList.remove("active"));
      document.querySelector('#tabs button[data-view="trace-detail"]').classList.add("active");
      renderTraceDetail();
    });
  });
}

async function renderTraceDetail() {
  if (!state.selectedTraceId) {
    document.getElementById("content").innerHTML = '<div class="panel empty">No trace selected.</div>';
    return;
  }
  document.getElementById("content").innerHTML = '<div class="panel">Loading trace detail…</div>';
  try {
    const trace = await fetchJson(`/api/traces/${encodeURIComponent(state.selectedTraceId)}`);
    const timeline = trace.timeline || [];
    const explanation = trace.explanation || {};

    document.getElementById("content").innerHTML = `
      <div class="panel">
        <h2>Trace Detail</h2>
        <p class="muted">trace_id=${escapeHtml(trace.trace_id || "")}, request_id=${escapeHtml(trace.request_id || "")}, actor_id=${escapeHtml(trace.actor_id || "")}, tenant_id=${escapeHtml(trace.tenant_id || "")}</p>
        <p><strong>Final disposition:</strong> ${statusChip(explanation.final_disposition || explanation.final_outcome || "unknown")}</p>
        <p>${escapeHtml(explanation.final_disposition_summary || "No final disposition summary available.")}</p>
      </div>
      <div class="panel"><h3>Evidence source</h3>${renderEvidenceSources(traceDetailSources(trace, explanation))}</div>
      <div class="panel"><h3>Related artifacts (correlation)</h3>${renderTraceCrossLinks(trace.cross_links || explanation.cross_links || {})}</div>
      <div class="panel"><h3>Artifact integrity status</h3>${renderArtifactIntegrity(trace.artifact_integrity || explanation.artifact_integrity || null)}</div>
      <div class="panel">
        <h3>What happened, in what order</h3>
        ${renderTimeline(timeline)}
      </div>
      <div class="panel">
        <h3>What was checked (by stage)</h3>
        ${renderStageGroups(explanation.stage_groups || {})}
      </div>
      <div class="grid two">
        <div class="panel"><h3>Decision reasons</h3>${renderDecisionReasons(explanation.decision_reasons || [])}</div>
        <div class="panel"><h3>Evidence used</h3>${renderEvidenceUsed(explanation.evidence_used || [])}</div>
      </div>
      <div class="panel">
        <h3>Replay artifact</h3>
        ${renderReplayLink(explanation.replay || null)}
      </div>
      <div class="panel">
        <h3>Raw event inspector (compact)</h3>
        ${renderRawInspector(explanation.raw_event_inspector || [])}
      </div>
    `;
    const replayButton = document.getElementById("trace-linked-replay");
    if (replayButton && explanation.replay?.replay_id) {
      replayButton.addEventListener("click", () => {
        state.selectedReplayId = explanation.replay.replay_id;
        state.view = "replay";
        document.querySelectorAll("#tabs button").forEach((n) => n.classList.remove("active"));
        document.querySelector('#tabs button[data-view="replay"]').classList.add("active");
        renderReplay();
      });
    }
  } catch (error) {
    document.getElementById("content").innerHTML = `<div class="panel error">Unable to load trace detail: ${escapeHtml(error.message)}</div>`;
  }
}

function renderStageGroups(stageGroups) {
  const orderedStages = ["lifecycle", "policy", "retrieval", "model", "tools", "deny", "fallback", "error"];
  const cards = orderedStages
    .filter((stage) => Array.isArray(stageGroups[stage]) && stageGroups[stage].length)
    .map((stage) => {
      const rows = stageGroups[stage] || [];
      const latest = rows[rows.length - 1] || {};
      return `<div class="panel stage-panel">
        <div class="muted">${escapeHtml(stage)}</div>
        <div><strong>${escapeHtml(String(rows.length))}</strong> checks/events</div>
        <div class="chips"><span class="chip ${statusClass(latest.decision_outcome || "")}">${escapeHtml(String(latest.decision_outcome || "observed"))}</span></div>
        ${latest.reason ? `<div class="muted">${escapeHtml(String(latest.reason))}</div>` : ""}
      </div>`;
    });
  if (!cards.length) return '<p class="empty">No stage-grouped checks found.</p>';
  return `<div class="grid">${cards.join("")}</div>`;
}

function renderDecisionReasons(rows) {
  if (!rows.length) return '<p class="empty">No explicit reasons captured.</p>';
  return `<table><thead><tr><th>time</th><th>stage</th><th>event</th><th>outcome</th><th>reason</th></tr></thead><tbody>
    ${rows.map((row) => `<tr>
      <td>${escapeHtml(String(row.created_at || ""))}</td>
      <td>${escapeHtml(String(row.stage || ""))}</td>
      <td>${escapeHtml(String(row.event_type || ""))}</td>
      <td>${statusChip(row.decision_outcome || "")}</td>
      <td>${escapeHtml(String(row.reason || ""))}</td>
    </tr>`).join("")}
  </tbody></table>`;
}

function renderEvidenceUsed(rows) {
  if (!rows.length) return '<p class="empty">No structured evidence captured for this trace.</p>';
  return rows.map((row) => `<details>
    <summary>${escapeHtml(String(row.label || row.kind || "evidence"))} <span class="muted">(${escapeHtml(String(row.created_at || ""))})</span></summary>
    <div class="chips"><span class="chip">kind=${escapeHtml(String(row.kind || ""))}</span><span class="chip">stage=${escapeHtml(String(row.stage || ""))}</span></div>
    <pre>${escapeHtml(JSON.stringify(row.details || {}, null, 2))}</pre>
  </details>`).join("");
}

function renderReplayLink(replay) {
  if (!replay) return '<p class="empty">No replay artifact linked for this trace.</p>';
  const replayId = String(replay.replay_id || "");
  return `<p><button class="link-btn" id="trace-linked-replay">${escapeHtml(replayId || "open replay")}</button></p>
    <p class="muted">${escapeHtml(String(replay.replay_path || ""))}</p>`;
}

function renderRawInspector(rows) {
  if (!rows.length) return '<p class="empty">No raw events available.</p>';
  return rows.map((row) => `<details>
    <summary>#${escapeHtml(String(row.index || ""))} ${escapeHtml(String(row.event_type || ""))} <span class="muted">${escapeHtml(String(row.created_at || ""))}</span></summary>
    <div class="chips"><span class="chip">stage=${escapeHtml(String(row.stage || ""))}</span><span class="chip ${statusClass(row.decision_outcome || "")}">outcome=${escapeHtml(String(row.decision_outcome || ""))}</span></div>
    <pre>${escapeHtml(JSON.stringify(row.payload || {}, null, 2))}</pre>
  </details>`).join("");
}

function renderTimeline(timeline) {
  if (!timeline.length) {
    return '<p class="empty">No timeline events available.</p>';
  }
  return timeline
    .slice()
    .sort((a, b) => String(a.created_at || "").localeCompare(String(b.created_at || "")))
    .map((event, index) => {
      const payload = event.payload || {};
      return `<div class="timeline-item ${escapeHtml(event.event_category || "")}">
        <div class="timeline-title">${index + 1}. ${escapeHtml(event.event_type || "unknown")}</div>
        <div class="muted">${escapeHtml(event.created_at || "")}</div>
        <div class="chips">
          <span class="chip">stage=${escapeHtml(event.stage || "")}</span>
          <span class="chip ${statusClass(event.event_type || event.decision_outcome || "")}">outcome=${escapeHtml(event.decision_outcome || "")}</span>
        </div>
        ${event.reason ? `<div><strong>Reason:</strong> ${escapeHtml(event.reason)}</div>` : ""}
        ${Object.keys(payload).length ? `<details><summary>Event payload</summary><pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre></details>` : ""}
      </div>`;
    })
    .join("");
}

function renderDecisionTable(events, keys) {
  if (!events.length) {
    return '<p class="empty">No events in this category.</p>';
  }
  return `<table><thead><tr>${keys.map((k) => `<th>${escapeHtml(k)}</th>`).join("")}</tr></thead><tbody>
    ${events
      .map((row) => `<tr>${keys.map((key) => `<td>${escapeHtml(String(row[key] ?? ""))}</td>`).join("")}</tr>`)
      .join("")}
  </tbody></table>`;
}

function renderBoundaryMap() {
  const components = state.boundaryData?.zones || state.systemMap?.components || [];
  const crossings = state.boundaryData?.crossings || [];
  document.getElementById("content").innerHTML = `
    <div class="panel">
      <h2>Security Boundaries / Trust Zones</h2>
      <p class="muted">Repository-grounded trust boundaries across runtime and readiness pathways.</p>
    </div>
    <div class="panel">
      <h3>Trust zones</h3>
      ${!components.length ? '<p class="empty">No boundary metadata available.</p>' : `<table><thead><tr><th>zone</th><th>code locations</th><th>relevant docs</th><th>related controls</th><th>evidence artifacts</th></tr></thead><tbody>${components
        .map((c) => `<tr><td>${escapeHtml(c.name || c.id || '')}</td><td>${renderPathList(c.component_paths || [])}</td><td>${renderPathList(c.relevant_docs || [])}</td><td>${renderInlineList(c.related_controls || [])}</td><td>${renderPathList(c.related_evidence_artifacts || [])}</td></tr>`)
        .join('')}</tbody></table>`}
    </div>
    <div class="panel">
      <h3>Boundary crossings and controls</h3>
      ${renderBoundaryCrossings(crossings)}
    </div>
    <div class="panel"><h3>Evidence source</h3>${renderEvidenceSources(boundarySources())}</div>
  `;
}

function renderBoundaryCrossings(crossings) {
  if (!crossings.length) {
    return '<p class="empty">No crossing metadata found.</p>';
  }
  return `<table><thead><tr><th>from → to</th><th>what crosses this boundary</th><th>what can go wrong</th><th>what control exists</th><th>code locations</th><th>relevant docs</th><th>related controls</th><th>evidence artifacts</th></tr></thead><tbody>${crossings
    .map((row) => `<tr>
      <td><strong>${escapeHtml(row.from || '')}</strong><br/>→ ${escapeHtml(row.to || '')}</td>
      <td>${renderInlineList(row.what_crosses || [])}</td>
      <td>${renderInlineList(row.what_can_go_wrong || [])}</td>
      <td>${escapeHtml(row.control || '')}</td>
      <td>${renderPathList(row.control_locations || [])}</td>
      <td>${renderPathList(row.relevant_docs || [])}</td>
      <td>${renderInlineList(row.related_controls || [])}</td>
      <td>${renderPathList(row.evidence_artifacts || [])}</td>
    </tr>`).join('')}</tbody></table>`;
}



function renderPathList(paths) {
  if (!paths.length) return '<span class="empty">-</span>';
  return `<ul>${paths.map((path) => `<li><code>${escapeHtml(String(path))}</code></li>`).join('')}</ul>`;
}

function renderInlineList(items) {
  if (!items.length) return '<span class="empty">-</span>';
  return `<ul>${items.map((item) => `<li>${escapeHtml(String(item))}</li>`).join('')}</ul>`;
}

async function renderEvals() {
  if (!state.evalRuns.length) {
    document.getElementById("content").innerHTML = '<div class="panel empty">No eval summaries found.</div>';
    return;
  }
  if (!state.selectedEvalId) {
    state.selectedEvalId = state.evalRuns[0].run_id;
  }

  document.getElementById("content").innerHTML = '<div class="panel">Loading eval run…</div>';
  try {
    const run = await fetchJson(`/api/evals/${encodeURIComponent(state.selectedEvalId)}`);
    document.getElementById("content").innerHTML = `
      <div class="panel">
        <h2>Evals</h2>
        <select id="eval-select">${state.evalRuns
          .map((item) => `<option value="${escapeHtml(item.run_id)}" ${item.run_id === state.selectedEvalId ? "selected" : ""}>${escapeHtml(item.run_id)}</option>`)
          .join("")}</select>
        <p class="muted">${escapeHtml(run.summary?.summary || "")}</p>
      </div>
      <div class="grid">
        ${metricCard("Total", run.summary?.total ?? 0)}
        ${metricCard("Passed", run.summary?.passed_count ?? 0)}
        ${metricCard("Malformed rows", run.scenario_malformed_lines ?? 0)}
      </div>
      <div class="panel"><h3>High/Critical failures</h3>${renderScenarioRows(run.high_or_critical_failures || [])}</div>
      <div class="panel"><h3>Baseline category coverage</h3>${renderBaselineCoverage(run.baseline_coverage || [])}</div>
      <div class="panel"><h3>Scenario outcomes</h3>${renderScenarioRows(run.scenario_results || [])}</div>
      <div class="panel"><h3>Evidence sources</h3>${renderEvidenceSources(evalSources(run))}</div>
    `;
    document.getElementById("eval-select").addEventListener("change", async (event) => {
      state.selectedEvalId = event.target.value;
      await renderEvals();
    });
  } catch (error) {
    document.getElementById("content").innerHTML = `<div class="panel error">Unable to load eval run: ${escapeHtml(error.message)}</div>`;
  }
}

function renderScenarioRows(rows) {
  if (!rows.length) {
    return '<p class="empty">No rows available.</p>';
  }
  return `<table><thead><tr><th>scenario_id</th><th>title</th><th>severity</th><th>outcome</th><th>category</th><th>controls / boundaries</th><th>details</th></tr></thead><tbody>
    ${rows
      .map((row) => {
        const links = (row.control_boundary_links || [])
          .map((item) => `${escapeHtml(item.control || '')} → ${escapeHtml(item.boundary || '')}`)
          .join('; ');
        return `<tr><td>${escapeHtml(row.scenario_id || '')}</td><td>${escapeHtml(row.title || '')}</td><td>${escapeHtml(row.severity || '')}</td><td>${statusChip(row.outcome || '')}</td><td>${escapeHtml(row.category || '')}</td><td>${links || '-'}</td><td>${escapeHtml(row.details || '')}</td></tr>`;
      })
      .join('')}
  </tbody></table>`;
}

function renderBaselineCoverage(items) {
  if (!items.length) {
    return '<p class="empty">No baseline coverage metadata available.</p>';
  }
  return `<table><thead><tr><th>baseline category</th><th>repository scenarios</th><th>observed in run</th><th>high/critical failures</th><th>controls / boundaries</th></tr></thead><tbody>
    ${items
      .map((item) => {
        const repoNames = (item.repository_scenarios || []).map((s) => s.scenario_id || s.title || '').filter(Boolean);
        const failures = (item.high_or_critical_failures || []).map((s) => s.scenario_id || '').filter(Boolean);
        const links = (item.repository_scenarios || [])
          .flatMap((s) => s.control_boundary_links || [])
          .map((link) => `${escapeHtml(link.control || '')} → ${escapeHtml(link.boundary || '')}`);
        return `<tr>
          <td>${escapeHtml(item.baseline_category || '')}</td>
          <td>${repoNames.length ? escapeHtml(repoNames.join('; ')) : '<span class="empty">not present in repo baseline</span>'}</td>
          <td>${escapeHtml(String(item.observed_in_run || 0))}</td>
          <td>${failures.length ? `<span class="chip deny">${escapeHtml(failures.join('; '))}</span>` : '<span class="chip ok">none</span>'}</td>
          <td>${links.length ? links.join('<br/>') : '-'}</td>
        </tr>`;
      })
      .join('')}
  </tbody></table>`;
}

function renderLaunchGate() {
  const report = state.launchGate;
  if (!report) {
    document.getElementById("content").innerHTML = '<div class="panel empty">No launch-gate artifact found.</div>';
    return;
  }
  document.getElementById("content").innerHTML = `
    <div class="panel">
      <h2>Launch Gate</h2>
      <p><strong>Status:</strong> ${statusChip(report.status || "unknown")}</p>
      <p class="muted">${escapeHtml(report.summary || "")}</p>
      <p class="muted">Latest artifact timestamp: ${escapeHtml(report.latest_artifact_timestamp || "unknown")}</p>
    </div>
    <div class="grid">
      ${metricCard("Checks", report.snapshot?.check_total ?? (report.checks || []).length)}
      ${metricCard("Passed", report.snapshot?.check_passed ?? (report.passed_checks || []).length)}
      ${metricCard("Blockers", (report.blockers || []).length)}
      ${metricCard("Residual risks", (report.residual_risks || []).length)}
    </div>
    <div class="panel"><h3>Blockers</h3>${renderStringList(report.blockers || [])}</div>
    <div class="panel"><h3>Residual Risks</h3>${renderStringList(report.residual_risks || [])}</div>
    <div class="panel"><h3>Missing Evidence</h3>${renderMissingEvidence(report.missing_evidence || [])}</div>
    <div class="panel"><h3>Passed checks</h3>${renderPassedChecks(report.passed_checks || [])}</div>
    <div class="panel"><h3>Related control areas / eval categories</h3>${renderLaunchGateRelatedLinks(report.related_links || {})}</div>
    <div class="panel"><h3>Artifact integrity status</h3>${renderArtifactIntegrity(launchGateIntegrity(report))}</div>
    <div class="panel"><h3>Evidence source</h3>${renderEvidenceSources(launchGateSources(report))}</div>
  `;
}

function renderStringList(items) {
  if (!items.length) {
    return '<p class="empty">None</p>';
  }
  return `<ul>${items.map((item) => `<li>${escapeHtml(String(item))}</li>`).join("")}</ul>`;
}

function renderMissingEvidence(items) {
  if (!items.length) {
    return '<p class="empty">No missing evidence flagged.</p>';
  }
  return `<table><thead><tr><th>check_name</th><th>details</th></tr></thead><tbody>
    ${items.map((item) => `<tr><td>${escapeHtml(item.check_name || "")}</td><td>${escapeHtml(item.details || "")}</td></tr>`).join("")}
  </tbody></table>`;
}

function renderPassedChecks(items) {
  if (!items.length) {
    return '<p class="empty">No passed checks listed.</p>';
  }
  return `<table><thead><tr><th>check_name</th><th>status</th><th>details</th></tr></thead><tbody>
    ${items.map((item) => `<tr><td>${escapeHtml(item.check_name || "")}</td><td>${escapeHtml(item.status || "")}</td><td>${escapeHtml(item.details || "")}</td></tr>`).join("")}
  </tbody></table>`;
}

async function renderReplay() {
  if (!state.replayItems.length) {
    document.getElementById("content").innerHTML = '<div class="panel empty">No replay artifacts found.</div>';
    return;
  }
  if (!state.selectedReplayId) {
    state.selectedReplayId = state.replayItems[0].replay_id;
  }

  document.getElementById("content").innerHTML = '<div class="panel">Loading replay artifact…</div>';
  try {
    const payload = await fetchJson(`/api/replay/${encodeURIComponent(state.selectedReplayId)}`);
    document.getElementById("content").innerHTML = `
      <div class="panel">
        <h2>Replay Artifact Viewer</h2>
        <select id="replay-select">${state.replayItems
          .map((item) => `<option value="${escapeHtml(item.replay_id)}" ${item.replay_id === state.selectedReplayId ? "selected" : ""}>${escapeHtml(item.replay_id)}</option>`)
          .join("")}</select>
        <p class="muted">${escapeHtml(payload.artifact_path || "")}</p>
      </div>
      <div class="panel"><h3>Evidence source</h3>${renderEvidenceSources(replaySources(payload))}</div>
      <div class="panel"><pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre></div>
    `;
    document.getElementById("replay-select").addEventListener("change", async (event) => {
      state.selectedReplayId = event.target.value;
      await renderReplay();
    });
  } catch (error) {
    document.getElementById("content").innerHTML = `<div class="panel error">Unable to load replay artifact: ${escapeHtml(error.message)}</div>`;
  }
}

function renderArtifactIntegrity(payload) {
  if (!payload || !Array.isArray(payload.entries)) {
    return '<p class="empty">Integrity unverified: no integrity metadata available.</p>';
  }
  if (!payload.entries.length) {
    return '<p class="empty">Integrity unverified: no artifacts detected.</p>';
  }
  const table = `<table><thead><tr><th>artifact</th><th>evidence</th><th>signing</th><th>verification metadata</th><th>path</th><th>timestamp</th></tr></thead><tbody>
    ${payload.entries.map((row) => `<tr>
      <td>${escapeHtml(String(row.artifact_type || 'unknown'))}</td>
      <td>${statusChip(row.evidence_state || 'integrity unverified')}</td>
      <td>${statusChip(row.signing_state || 'integrity unverified')}</td>
      <td>${statusChip(row.verification_state || 'integrity unverified')}</td>
      <td>${escapeHtml(String(row.path || 'n/a'))}</td>
      <td>${escapeHtml(String(row.timestamp || 'n/a'))}</td>
    </tr>`).join('')}
  </tbody></table>`;
  const legend = `<p class="muted">${escapeHtml(String(payload.legend || 'Integrity status is conservative and does not imply cryptographic attestation.'))}</p>`;
  return table + legend;
}

function launchGateIntegrity(report) {
  return {
    entries: [
      {
        artifact_type: 'launch_gate',
        evidence_state: report?.path ? 'file-backed evidence' : 'integrity unverified',
        signing_state: 'signing not implemented',
        verification_state: report?.path ? 'verification metadata present' : 'integrity unverified',
        path: report?.path || 'artifacts/logs/launch_gate/*.json',
        timestamp: report?.latest_artifact_timestamp || report?.artifact_timestamp || null,
      },
    ],
    legend: 'Launch-gate artifacts are file-backed; cryptographic signing is not implemented in this repository.',
  };
}

function renderConnectedEvidenceSummary(summary) {
  if (!summary) return '<p class="empty">No connected-evidence summary available.</p>';
  return `<div class="grid">
    ${metricCard('Replay exact links', summary.traces_with_replay_exact ?? 0)}
    ${metricCard('Eval exact links', summary.traces_with_eval_exact ?? 0)}
    ${metricCard('Eval inferred links', summary.traces_with_eval_inferred ?? 0)}
    ${metricCard('Verification inferred links', summary.traces_with_verification_inferred ?? 0)}
    ${metricCard('Launch-gate inferred links', summary.traces_with_launch_gate_inferred ?? 0)}
    ${metricCard('No confirmed links', summary.traces_with_no_confirmed_links ?? 0)}
  </div>`;
}

function renderTraceCrossLinks(crossLinks) {
  if (!crossLinks || !Object.keys(crossLinks).length) {
    return '<p class="empty">No artifact correlations available for this trace.</p>';
  }
  const rows = [
    ['replay', crossLinks.replay],
    ['eval', crossLinks.eval],
    ['verification', crossLinks.verification],
    ['launch_gate', crossLinks.launch_gate],
  ];
  return `<table><thead><tr><th>artifact type</th><th>correlation</th><th>reason</th><th>linked items</th></tr></thead><tbody>
    ${rows.map(([name, value]) => {
      const item = value || {};
      let linked = '-';
      if (item.artifact?.path) linked = `<code>${escapeHtml(String(item.artifact.path))}</code>`;
      if (Array.isArray(item.items) && item.items.length) {
        linked = `<ul>${item.items.map((r) => `<li>${escapeHtml(String(r.run_id || ''))} / ${escapeHtml(String(r.scenario_id || ''))} (${escapeHtml(String(r.correlation || ''))})</li>`).join('')}</ul>`;
      }
      if (item.related_links && (item.related_links.control_areas || item.related_links.eval_categories)) {
        const controls = (item.related_links.control_areas || []).join(', ');
        const categories = (item.related_links.eval_categories || []).join(', ');
        linked = `${linked}<div class="muted">controls: ${escapeHtml(controls || 'none')}</div><div class="muted">eval categories: ${escapeHtml(categories || 'none')}</div>`;
      }
      return `<tr><td>${escapeHtml(name)}</td><td>${statusChip(item.correlation || 'none')}</td><td>${escapeHtml(String(item.reason || ''))}</td><td>${linked}</td></tr>`;
    }).join('')}
  </tbody></table>`;
}

function renderLaunchGateRelatedLinks(links) {
  if (!links || links.correlation === 'none') {
    return '<p class="empty">No launch-gate control/eval links were found.</p>';
  }
  return `<p class="muted">${escapeHtml(String(links.reason || ''))}</p>
    <table><thead><tr><th>control areas</th><th>eval categories</th><th>correlation</th></tr></thead><tbody>
      <tr><td>${escapeHtml((links.control_areas || []).join(', ') || 'none')}</td><td>${escapeHtml((links.eval_categories || []).join(', ') || 'none')}</td><td>${statusChip(links.correlation || 'none')}</td></tr>
    </tbody></table>`;
}

function renderEvidenceSources(rows, options = {}) {
  const normalized = (rows || []).filter((row) => row && (row.path || row.type || row.logical_name));
  const mode = state.overview?.demo_mode || state.systemMap?.demo_mode ? "demo artifacts" : "runtime artifacts";
  if (!normalized.length) {
    return `<p class="empty">No evidence source metadata available. Mode: ${escapeHtml(mode)}</p>${options.includeLegend ? renderEvidenceLegend() : ""}`;
  }
  const table = `<table><thead><tr><th>type</th><th>path / logical source</th><th>timestamp</th><th>mode</th></tr></thead><tbody>
    ${normalized.map((row) => `<tr>
      <td>${escapeHtml(String(row.type || "unknown"))}</td>
      <td>${escapeHtml(String(row.path || row.logical_name || ""))}</td>
      <td>${escapeHtml(String(row.timestamp || "n/a"))}</td>
      <td>${escapeHtml(mode)}</td>
    </tr>`).join("")}
  </tbody></table>`;
  return `${table}${options.includeLegend ? renderEvidenceLegend() : ""}`;
}

function renderEvidenceLegend() {
  return `<div class="legend muted">Evidence types: audit JSONL (runtime timeline), replay artifact (replayable trace), eval summary JSON (run status), eval JSONL (scenario outcomes), launch-gate report (release readiness), verification summary (security guarantees), static boundary metadata (trust-zone map).</div>`;
}

function traceExplorerSources() {
  return [
    {
      type: "audit_jsonl",
      path: `${state.overview?.artifacts_root || "artifacts/logs"}/audit.jsonl`,
      timestamp: state.traces[0]?.started_at || null,
    },
  ];
}

function traceDetailSources(trace, explanation) {
  const sources = [
    {
      type: "audit_jsonl",
      path: `${state.overview?.artifacts_root || "artifacts/logs"}/audit.jsonl`,
      timestamp: explanation?.updated_at || null,
    },
  ];
  if (explanation?.replay?.replay_path) {
    sources.push({
      type: "replay_artifact",
      path: explanation.replay.replay_path,
      timestamp: explanation.replay.replay_timestamp || null,
    });
  }
  return sources;
}

function boundarySources() {
  return [
    {
      type: "static_boundary_metadata",
      path: "observability/web/static/security_boundaries.json",
      timestamp: null,
    },
  ];
}

function evalSources(run) {
  return [
    { type: "eval_summary_json", path: run.summary_path || null, timestamp: run.summary_timestamp || null },
    { type: "eval_jsonl", path: run.scenario_path || null, timestamp: run.scenario_timestamp || null },
    { type: "eval_baseline_catalog", path: run.catalog_path || null, timestamp: null },
  ];
}

function launchGateSources(report) {
  return [
    { type: "launch_gate_report", path: report.path || null, timestamp: report.latest_artifact_timestamp || report.artifact_timestamp || null },
    { type: "verification_summary", path: state.verification?.path || null, timestamp: state.verification?.artifact_timestamp || null },
  ];
}

function replaySources(payload) {
  return [
    { type: "replay_artifact", path: payload.artifact_path || null, timestamp: payload.timeline?.[payload.timeline.length - 1]?.created_at || null },
    { type: "audit_jsonl", path: `${state.overview?.artifacts_root || "artifacts/logs"}/audit.jsonl`, timestamp: null },
  ];
}

function metricCard(label, value) {
  return `<div class="panel"><div class="muted">${escapeHtml(String(label))}</div><div class="metric">${typeof value === "string" ? value : escapeHtml(String(value))}</div></div>`;
}

function statusChip(value) {
  const safe = escapeHtml(String(value));
  return `<span class="chip ${statusClass(value)}">${safe}</span>`;
}

function statusClass(value) {
  const v = String(value || "").toLowerCase();
  if (v.includes("deny") || v === "error" || v === "no_go") return "deny";
  if (v.includes("fallback") || v === "conditional_go") return "fallback";
  if (v.includes("allow") || v === "completed" || v === "go" || v === "ok") return "ok";
  return "";
}

function renderEventTypeChips(eventTypes) {
  if (!eventTypes.length) {
    return '<span class="empty">none</span>';
  }
  const ordered = eventTypes.slice().sort((a, b) => {
    const ai = PRIMARY_TIMELINE_ORDER.indexOf(a);
    const bi = PRIMARY_TIMELINE_ORDER.indexOf(b);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });
  return `<div class="chips">${ordered.map((type) => `<span class="chip ${statusClass(type)}">${escapeHtml(type)}</span>`).join("")}</div>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
