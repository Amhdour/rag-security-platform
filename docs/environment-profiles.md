# Adapter Environment Profiles

This document defines adapter execution profiles used to keep runs honest, repeatable, and deployment-context aware.

## Profile overview

| Profile | Allowed source modes | Critical freshness threshold | Warning freshness threshold | Logging verbosity | Synthetic fallback |
|---|---|---:|---:|---|---|
| `demo` | `synthetic`, `fixture_backed`, `file_backed`, `db_backed`, `live` | 7 days | 14 days | debug | allowed |
| `dev` | `synthetic`, `fixture_backed`, `file_backed`, `db_backed`, `live` | 2 days | 4 days | info | allowed |
| `ci` | `synthetic`, `fixture_backed`, `file_backed`, `db_backed` | 1 day | 2 days | info | allowed |
| `prod_like` | `live`, `db_backed`, `file_backed` | 1 hour | 6 hours | warn | blocked |

**Implemented:** Profile policies are enforced by adapter code in `integration-adapter/integration_adapter/env_profiles.py`.

## Safeguards

**Implemented:** The adapter blocks unsafe profile combinations:

1. `prod_like` + `--demo` / forced demo mode is blocked.
2. `prod_like` + synthetic runtime evidence is blocked.
3. `prod_like` + zero runtime-event rows is blocked.
4. `prod_like` + fallback usage is blocked.
5. `prod_like` + stale or missing critical evidence is blocked.

**Implemented:** Profile freshness thresholds are applied as defaults for launch-gate freshness checks by setting:
- `INTEGRATION_ADAPTER_MAX_CRITICAL_EVIDENCE_AGE_SECONDS`
- `INTEGRATION_ADAPTER_MAX_WARNING_EVIDENCE_AGE_SECONDS`

## Commands

Validate profile/configuration:

```bash
cd integration-adapter
python -m integration_adapter.validate_config --profile dev
python -m integration_adapter.validate_config --profile prod_like --strict-sources
```

Run evidence pipeline with a profile:

```bash
cd integration-adapter
python -m integration_adapter.evidence_pipeline --demo --profile demo
python -m integration_adapter.evidence_pipeline --profile prod_like
```

CI-friendly smoke run:

```bash
cd integration-adapter
python -m integration_adapter.ci_smoke --profile ci
```

## Honesty boundaries

- **Implemented:** `prod_like` is a stricter execution profile, not proof of production deployment.
- **Unconfirmed:** canonical runtime hook not validated in this workspace.
- **Demo-only:** `demo` profile permits synthetic fallbacks and should not be used as production enforcement evidence.
