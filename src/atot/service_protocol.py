from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from .agent_summary import DocumentName

from .commands.diagnostics import doctor_payload, models_payload
from .config_v2 import (
    config_as_dict,
    inspect_config,
    load_atot_config,
    read_config_value,
    set_config_value,
)
from .redaction import is_sensitive_key, redact_sensitive
from .runtime_defaults import DEFAULT_CLOUD_CHUNK_MINUTES, DEFAULT_SUBSCRIPTION_LIMIT
from .service_contract import validate_service_request
from .workflow_service import WorkflowService


def handle_service_request(
    request: dict[str, Any], *, service: WorkflowService | None = None
) -> dict[str, Any]:
    if not isinstance(request, dict):
        return error_response(None, "Service request must be a JSON object.", "ValueError")
    service = service or WorkflowService()
    request_id = request.get("id")
    method = str(request.get("method") or "")
    params_payload = request.get("params")
    params: dict[str, Any] = params_payload if isinstance(params_payload, dict) else {}
    try:
        validate_service_request(method, params, allow_extra=False)
        result = dispatch_service_method(method, params, service)
        return {"id": request_id, "ok": True, "result": result}
    except Exception as exc:
        return error_response(request_id, str(exc), type(exc).__name__)


def error_response(request_id: Any, message: str, error_type: str) -> dict[str, Any]:
    return {"id": request_id, "ok": False, "error": {"message": message, "type": error_type}}


def dispatch_service_method(method: str, params: dict[str, Any], service: WorkflowService) -> Any:
    if method == "transcribe":
        return service.run_transcribe(
            _path(params["input"]),
            output_dir=_optional_path(params.get("output_dir")),
            job_dir=_optional_path(params.get("job_dir")),
            name=params.get("name"),
            backend=params.get("backend"),
            model=params.get("model"),
            language=params.get("language"),
            languages=params.get("languages"),
            profile=params.get("profile"),
            prompt_file=_optional_path(params.get("prompt_file")),
            glossary_file=_optional_path(params.get("glossary_file")),
            rule_packs=[str(item) for item in (params.get("rule_packs") or [])] or None,
            chunking=params.get("chunking"),
            chunk_length=_optional_float(params.get("chunk_length")),
            max_chunk_length=_optional_float(params.get("max_chunk_length")),
            silence_threshold=_optional_float(params.get("silence_threshold")),
            min_silence=_optional_float(params.get("min_silence")),
            overlap=_optional_float(params.get("overlap")),
            force=bool(params.get("force", False)),
            local_only=_optional_bool(params.get("local_only")),
            cloud_summary=_optional_bool(params.get("cloud_summary")),
        )
    if method == "import_xiaoyuzhou":
        return service.run_import_xiaoyuzhou(
            str(params["url"]),
            process_dir=_optional_path(params.get("process_dir")),
            group_name=params.get("group_name"),
            folder_name=params.get("folder_name"),
            audio_name=params.get("audio_name"),
            download=bool(params.get("download", True)),
            force=bool(params.get("force", False)),
            data_only=bool(params.get("data_only", False)),
            transcribe=bool(params.get("transcribe", True)),
            backend=params.get("backend"),
            model=params.get("model"),
            language=params.get("language"),
            languages=params.get("languages"),
            profile=params.get("profile"),
            local_only=_optional_bool(params.get("local_only")),
        )
    if method == "qa":
        return service.run_qa(
            _path(params["output"]), profile=str(params.get("profile") or "balanced")
        )
    if method == "repair":
        return service.run_repair(
            _path(params["output"]),
            plan_only=bool(params.get("plan_only", False)),
            local_only=_optional_bool(params.get("local_only")),
        )
    if method == "cloud_prepare":
        return service.run_cloud_prepare(
            _path(params["output"]),
            redact=params.get("redact"),
            chunk_minutes=float(params.get("chunk_minutes") or DEFAULT_CLOUD_CHUNK_MINUTES),
        )
    if method == "cloud_summarize":
        return service.run_cloud_summarize(
            _path(params["output"]),
            call_api=bool(params.get("call_api", False)),
            prompt_file=_optional_path(params.get("prompt_file")),
            mode=str(params.get("mode") or "auto"),
            from_readable=bool(params.get("from_readable", False)),
            stream_summary=bool(params.get("stream_summary", False)),
        )
    if method == "cloud_title":
        return service.run_cloud_title(
            _path(params["output"]),
            call_api=bool(params.get("call_api", False)),
            prompt_file=_optional_path(params.get("prompt_file")),
            force=bool(params.get("force", False)),
        )
    if method == "cloud_glossary_review":
        return service.run_cloud_glossary_review(
            _path(params["output"]),
            call_api=bool(params.get("call_api", False)),
            prompt_file=_optional_path(params.get("prompt_file")),
        )
    if method == "cloud_polish":
        return service.run_cloud_polish(
            _path(params["output"]),
            call_api=bool(params.get("call_api", False)),
            prompt_file=_optional_path(params.get("prompt_file")),
        )
    if method == "srt":
        return service.run_srt(
            [_path(item) for item in params.get("inputs", [])],
            languages=params.get("languages"),
            backend=str(params["backend"]) if params.get("backend") else None,
            output=_optional_path(params.get("output")),
            output_dir=_optional_path(params.get("output_dir")),
            overwrite=bool(params.get("overwrite", False)),
        )
    if method == "subscriptions":
        return service.run_subscriptions(
            **subscriptions_params([str(item) for item in params.get("arguments", [])])
        )
    if method == "library_status":
        return service.run_library_status()
    if method == "library_list_episodes":
        return service.run_library_list_episodes(
            query=str(params.get("query", "")),
            needs_summary=bool(params.get("needs_summary", False)),
            offset=int(params.get("offset", 0)),
            limit=int(params.get("limit", 20)),
        )
    if method == "library_read_episode":
        return service.run_library_read_episode(str(params["episode_id"]))
    if method == "library_read_document":
        return service.run_library_read_document(
            str(params["episode_id"]),
            cast(DocumentName, params.get("document", "transcript")),
            offset=int(params.get("offset", 0)),
            max_chars=int(params.get("max_chars", 8000)),
            expected_sha256=params.get("expected_sha256"),
        )
    if method == "library_write_summary":
        return service.run_library_write_summary(
            str(params["episode_id"]),
            str(params["markdown"]),
            transcript_sha256=str(params["transcript_sha256"]),
            summary_sha256=str(params["summary_sha256"]),
            overwrite=bool(params.get("overwrite", False)),
            generator=str(params.get("generator", "external-agent")),
        )
    if method == "library_delete_episode":
        return service.run_library_delete_episode(str(params["episode_id"]))
    if method == "status":
        return service.status(params.get("task_id"))
    if method == "config_list":
        return config_as_dict(load_atot_config())
    if method == "config_inspect":
        return inspect_config()
    if method == "config_get":
        key = str(params["key"])
        value = read_config_value(key)
        return {"key": key, "value": "***" if is_sensitive_key(key) and value else value}
    if method == "config_set":
        key = str(params["key"])
        path = set_config_value(key, params.get("value"))
        value = "***" if is_sensitive_key(key) and params.get("value") else params.get("value")
        return redact_sensitive({"path": str(path), "key": key, "value": value})
    if method == "models":
        return models_payload()
    if method == "doctor":
        return doctor_payload()
    raise ValueError(f"Unknown service method: {method}")


def subscriptions_params(arguments: list[str]) -> dict[str, Any]:
    if not arguments:
        raise ValueError("Missing subscriptions subcommand.")
    command = arguments[0]
    values = arguments[1:]
    if command == "add":
        url = values[0] if values else ""
        return {
            "command": "add",
            "url": url,
            "group_name": _flag_value(values, "--group-name") or "Default",
            "limit": _subscription_limit(values),
        }
    if command == "list":
        return {"command": "list"}
    if command == "refresh":
        return {
            "command": "refresh",
            "refresh_all": "--all" in values,
            "subscription_id": _flag_value(values, "--id"),
            "limit": _subscription_limit(values),
        }
    if command == "remove":
        subscription_id = next((item for item in values if not item.startswith("-")), "")
        return {"command": "remove", "subscription_id": subscription_id}
    raise ValueError(f"Unknown subscriptions subcommand: {command}")


def _flag_value(values: list[str], flag: str) -> str | None:
    try:
        index = values.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(values):
        return None
    return values[index + 1]


def _subscription_limit(values: list[str]) -> int | None:
    if "--full-history" in values:
        return None
    return int(_flag_value(values, "--limit") or DEFAULT_SUBSCRIPTION_LIMIT)


def _path(value: Any) -> Path:
    return Path(str(value)).expanduser()


def _optional_path(value: Any) -> Path | None:
    return None if value in {None, ""} else _path(value)


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)
