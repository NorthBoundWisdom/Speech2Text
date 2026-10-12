from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
import secrets
import sys
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from .redaction import redact_sensitive
from .runtime_defaults import MAX_SERVICE_HTTP_REQUEST_BYTES
from .service_protocol import handle_service_request
from .workflow_service import WorkflowService


MAX_HTTP_REQUEST_BYTES = MAX_SERVICE_HTTP_REQUEST_BYTES


def create_http_server(host: str, port: int, *, token: str) -> ThreadingHTTPServer:
    address = "127.0.0.1" if host == "localhost" else host
    try:
        loopback = ipaddress.ip_address(address).is_loopback
    except ValueError as exc:
        raise ValueError("HTTP service requires a literal loopback address.") from exc
    if not loopback:
        raise ValueError("HTTP service may only bind to loopback. Use stdio for remote clients.")
    if len(token) < 32 or not token.isascii() or any(char.isspace() for char in token):
        raise ValueError("Set ATOT_HTTP_TOKEN to a random ASCII token of at least 32 characters.")

    class Handler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(10)

        def authorize(self) -> bool:
            if any(len(self.headers.get_all(name, [])) > 1 for name in ("Host", "Origin", "Authorization", "Content-Length", "Content-Type")):
                json_response(self, {"error": "Duplicate request headers are not allowed."}, status=400)
                return False
            authority = f"[{address}]" if ":" in address else address
            allowed_hosts = {f"{authority}:{cast(ThreadingHTTPServer, self.server).server_port}"}
            if address == "127.0.0.1":
                allowed_hosts.add(f"localhost:{cast(ThreadingHTTPServer, self.server).server_port}")
            if self.headers.get("Host") not in allowed_hosts or self.headers.get("Origin") is not None:
                json_response(self, {"error": "HTTP Host or Origin is not allowed."}, status=403)
                return False
            supplied = self.headers.get("Authorization", "")
            if not secrets.compare_digest(supplied.encode(), f"Bearer {token}".encode()):
                json_response(self, {"error": "Bearer authentication required."}, status=401)
                return False
            return True

        def do_GET(self) -> None:  # noqa: N802
            if not self.authorize():
                return
            parsed = urlparse(self.path)
            if parsed.path == "/status":
                query = parse_qs(parsed.query)
                try:
                    payload = WorkflowService().status(query.get("task_id", [None])[0])
                    json_response(self, payload)
                except (ValueError, FileNotFoundError) as exc:
                    json_response(self, {"error": str(exc)}, status=400)
                return
            json_response(self, {"error": "not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            if not self.authorize():
                return
            if self.path != "/request":
                json_response(self, {"error": "not found"}, status=404)
                return
            try:
                request = read_json_request(self)
                json_response(self, handle_service_request(request))
            except (ValueError, json.JSONDecodeError) as exc:
                json_response(
                    self,
                    {"ok": False, "error": {"message": str(exc), "type": type(exc).__name__}},
                    status=400,
                )

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    if ":" in address:
        import socket

        class IPv6Server(ThreadingHTTPServer):
            address_family = socket.AF_INET6

        return IPv6Server((address, port), Handler)
    return ThreadingHTTPServer((address, port), Handler)


def serve_http(host: str, port: int) -> None:
    server = create_http_server(host, port, token=os.environ.get("ATOT_HTTP_TOKEN", ""))
    print(f"Audio2Text service: http://{host}:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def read_json_request(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    header = handler.headers.get("Content-Length")
    if header is None:
        raise ValueError("Missing Content-Length header.")
    try:
        length = int(header)
    except ValueError as exc:
        raise ValueError("Content-Length must be an integer.") from exc
    if length < 0:
        raise ValueError("Content-Length must be non-negative.")
    if length > MAX_HTTP_REQUEST_BYTES:
        raise ValueError(f"Request body is too large. Limit is {MAX_HTTP_REQUEST_BYTES} bytes.")
    if handler.headers.get("Transfer-Encoding") is not None:
        raise ValueError("Transfer-Encoding is not supported.")
    if handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise ValueError("Content-Type must be application/json.")
    body = handler.rfile.read(length)
    if len(body) != length:
        raise ValueError("Incomplete request body.")
    if not body:
        raise ValueError("Request body must not be empty.")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Request body must be valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Service request must be a JSON object.")
    return payload


def json_response(handler: BaseHTTPRequestHandler, payload: Any, *, status: int = 200) -> None:
    body = json.dumps(redact_sensitive(payload), ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(body)
