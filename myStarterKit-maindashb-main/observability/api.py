"""Minimal read-only HTTP API server for dashboard and artifact data consumption."""

from __future__ import annotations

import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from observability.service import DashboardService


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _resolve_dashboard_host(requested_host: str | None = None) -> str:
    host = requested_host or os.environ.get("DASHBOARD_HOST", "127.0.0.1")
    allow_remote = os.environ.get("DASHBOARD_ALLOW_REMOTE", "").lower() in {"1", "true", "yes", "on"}
    if host not in _LOOPBACK_HOSTS and not allow_remote:
        return "127.0.0.1"
    return host


def _dashboard_security_banner(*, host: str, artifacts_root: str | Path) -> str:
    remote = "remote-enabled" if host not in _LOOPBACK_HOSTS else "localhost-only"
    return (
        f"dashboard api listening on http://{host}:8080 (artifacts_root={artifacts_root}; "
        f"mode={remote}; read_only=true; no_tool_execution=true; no_policy_mutation=true)"
    )


class DashboardApiHandler(BaseHTTPRequestHandler):
    """Serve read-only dashboard endpoints and static UI assets."""

    service: DashboardService | None = None
    web_root: Path | None = None

    def do_GET(self) -> None:  # noqa: N802
        service = self.service
        if service is None:
            self._send_json(500, {"error": "service_unavailable"})
            return

        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}

        try:
            if path == "/" or path.startswith("/ui"):
                self._send_static("index.html")
                return
            if path.startswith("/static/"):
                requested = path.removeprefix("/static/")
                self._send_static(f"static/{requested}")
                return

            if path == "/api/overview":
                self._send_json(200, service.get_overview())
                return
            if path == "/api/traces":
                self._send_json(200, {"items": service.list_traces(filters=query)})
                return
            if path.startswith("/api/traces/"):
                trace_id = _extract_resource_id(path, prefix="/api/traces/")
                if not trace_id:
                    self._send_json(400, {"error": "invalid_trace_id"})
                    return
                payload = service.get_trace(trace_id)
                if payload is None:
                    self._send_json(404, {"error": "not_found", "resource": "trace"})
                else:
                    self._send_json(200, payload)
                return
            if path == "/api/replay":
                self._send_json(200, {"items": service.list_replay_artifacts()})
                return
            if path.startswith("/api/replay/"):
                replay_id = _extract_resource_id(path, prefix="/api/replay/")
                if not replay_id:
                    self._send_json(400, {"error": "invalid_replay_id"})
                    return
                payload = service.get_replay_artifact(replay_id)
                if payload is None:
                    self._send_json(404, {"error": "not_found", "resource": "replay"})
                else:
                    self._send_json(200, payload)
                return
            if path == "/api/evals":
                self._send_json(200, {"items": service.list_eval_runs()})
                return
            if path.startswith("/api/evals/"):
                run_id = _extract_resource_id(path, prefix="/api/evals/")
                if not run_id:
                    self._send_json(400, {"error": "invalid_eval_id"})
                    return
                payload = service.get_eval_run(run_id)
                if payload is None:
                    self._send_json(404, {"error": "not_found", "resource": "eval"})
                else:
                    self._send_json(200, payload)
                return
            if path == "/api/verification/latest":
                payload = service.get_latest_verification()
                if payload is None:
                    self._send_json(404, {"error": "not_found", "resource": "verification"})
                else:
                    self._send_json(200, payload)
                return
            if path == "/api/launch-gate/latest":
                payload = service.get_latest_launch_gate()
                if payload is None:
                    self._send_json(404, {"error": "not_found", "resource": "launch_gate"})
                else:
                    self._send_json(200, payload)
                return
            if path == "/api/system-map":
                self._send_json(200, service.get_system_map())
                return

            self._send_json(404, {"error": "not_found"})
        except Exception as exc:
            print(f"dashboard api error: {exc.__class__.__name__}: {exc}")
            traceback.print_exc()
            self._send_json(500, {"error": "internal_error"})

    def do_POST(self) -> None:  # noqa: N802
        self._send_json(405, {"error": "method_not_allowed", "read_only": True})

    def do_PUT(self) -> None:  # noqa: N802
        self._send_json(405, {"error": "method_not_allowed", "read_only": True})

    def do_PATCH(self) -> None:  # noqa: N802
        self._send_json(405, {"error": "method_not_allowed", "read_only": True})

    def do_DELETE(self) -> None:  # noqa: N802
        self._send_json(405, {"error": "method_not_allowed", "read_only": True})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, status_code: int, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_static(self, relative_path: str) -> None:
        web_root = self.web_root
        if web_root is None:
            self._send_json(500, {"error": "static_unavailable"})
            return

        normalized = Path(unquote(relative_path)).as_posix().lstrip("/")
        if normalized in {"", "."}:
            normalized = "index.html"
        if ".." in Path(normalized).parts:
            self._send_json(400, {"error": "invalid_static_path"})
            return

        full_path = web_root / normalized
        if not full_path.is_file():
            self._send_json(404, {"error": "not_found", "resource": "static"})
            return

        content = full_path.read_bytes()
        content_type = _content_type_for(full_path.suffix)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def _extract_resource_id(path: str, *, prefix: str) -> str | None:
    if not path.startswith(prefix):
        return None
    raw = path.removeprefix(prefix).strip("/")
    return unquote(raw) if raw else None


def _content_type_for(suffix: str) -> str:
    if suffix == ".html":
        return "text/html; charset=utf-8"
    if suffix == ".css":
        return "text/css; charset=utf-8"
    if suffix == ".js":
        return "application/javascript; charset=utf-8"
    if suffix == ".json":
        return "application/json; charset=utf-8"
    return "application/octet-stream"


def create_server(*, host: str = "127.0.0.1", port: int = 8080, repo_root: str | Path = ".", artifacts_root: str | Path | None = None) -> ThreadingHTTPServer:
    """Build a configured HTTP server instance for the dashboard API."""

    resolved_repo_root = Path(repo_root)
    resolved_artifacts_root = (
        artifacts_root
        or os.environ.get("DASHBOARD_ARTIFACTS_ROOT")
        or os.environ.get("INTEGRATION_ADAPTER_ARTIFACTS_ROOT")
        or os.environ.get("INTEGRATION_ARTIFACTS_ROOT", "artifacts/logs")
    )
    resolved_host = _resolve_dashboard_host(host)
    service = DashboardService(resolved_repo_root, artifacts_root=resolved_artifacts_root)

    class _ConfiguredHandler(DashboardApiHandler):
        pass

    _ConfiguredHandler.service = service
    _ConfiguredHandler.web_root = resolved_repo_root / "observability" / "web"
    return ThreadingHTTPServer((resolved_host, port), _ConfiguredHandler)


def main() -> None:
    artifacts_root = (
        os.environ.get("DASHBOARD_ARTIFACTS_ROOT")
        or os.environ.get("INTEGRATION_ADAPTER_ARTIFACTS_ROOT")
        or os.environ.get("INTEGRATION_ARTIFACTS_ROOT", "artifacts/logs")
    )
    host = _resolve_dashboard_host(None)
    server = create_server(host=host, artifacts_root=artifacts_root)
    print(_dashboard_security_banner(host=host, artifacts_root=artifacts_root))
    if host not in _LOOPBACK_HOSTS:
        print("warning: dashboard exposed beyond localhost; deploy behind authenticated reverse proxy")
    server.serve_forever()


if __name__ == "__main__":
    main()
