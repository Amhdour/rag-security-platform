# Dashboard phased improvement log

This file tracks reviewer-facing dashboard improvements in explicit phases.

## Phase 1 — Observability layer inspection and real-gap summary

Grounding files reviewed:
- `observability/api.py`
- `observability/service.py`
- `observability/trace_normalization.py`
- `observability/web/index.html`
- `observability/web/static/app.js`
- `observability/web/static/security_boundaries.json`
- `tests/unit/test_observability_dashboard_api.py`
- `tests/unit/test_dashboard_observational_guards.py`

### Confirmed strengths (implemented today)
- Dashboard HTTP API is read-only (`GET` endpoints; mutating verbs return `405`).
- Localhost-first bind posture with explicit opt-in for remote bind.
- Trace explorer already supports status/final outcome, decision class, actor/tenant, event type, replay/partial/security filters, plus sort options.
- Trace detail already includes stage grouping, decision reasons, evidence used, replay links, and compact raw event inspection.
- Overview already surfaces evidence sources, connection summary, and conservative integrity states.
- Existing tests already assert redaction preservation and dashboard non-mutation on key paths.

### Real gaps to address in follow-on phases
1. **Cross-artifact correlation confidence is under-specified in UI text.**
   - Backend emits `confirmed`/`inferred`/`reason`, but reviewer-facing wording can be made more explicit where correlations are inferred vs deterministic.
2. **Filter date comparison uses string ordering.**
   - Current date range filtering compares timestamp strings directly; malformed or mixed formats may be surprising.
3. **Evidence-source labeling is uneven between views.**
   - Overview and key detail panels have labels, but consistency across every major panel should be normalized.
4. **Boundary map linkage depth varies by entry.**
   - Metadata includes doc/control/evidence paths, but some rows are richer than others; consistency checks can be tightened.
5. **Integrity messaging exists but can be easier to scan in detail pages.**
   - Integrity state is present; small UX simplifications can reduce reviewer ambiguity.

### Constraints reaffirmed for next phases
- Keep dashboard read-only.
- Preserve enforcement behavior and policy engine semantics.
- Do not invent relationships; label inferred links explicitly.
- Preserve redaction and avoid surfacing unsafe raw payloads.
