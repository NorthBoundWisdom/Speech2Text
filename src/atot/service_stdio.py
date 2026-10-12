from __future__ import annotations

import json
import sys
from typing import Any

from .service_protocol import error_response, handle_service_request
from .workflow_service import WorkflowService


def serve_stdio(*, request_json: str | None = None, unwrap_result: bool = False) -> int:
    service = WorkflowService(event_sink=None)
    if request_json is not None:
        response = handle_service_request(json.loads(request_json), service=service)
        payload: Any = response.get("result") if unwrap_result and response.get("ok") else response
        # stdout protocol: callers parse this JSON payload.
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if response.get("ok") else 1

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            response = handle_service_request(json.loads(line), service=service)
        except json.JSONDecodeError as exc:
            response = error_response(None, str(exc), "JSONDecodeError")
        # stdout protocol: one compact JSON response per input line.
        print(json.dumps(response, ensure_ascii=False), flush=True)
    return 0
