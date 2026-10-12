from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable

import httpx

from ..config import load_app_config
from ..utils import read_text, write_json_atomic


@dataclass(frozen=True)
class CloudClientOptions:
    config_path: Path | None = None


@dataclass(frozen=True)
class ResolvedCloudOptions:
    api_base: str | None = None
    api_key: str | None = None
    model: str | None = None
    config_path: Path | None = None
    timeout: float = 120.0
    temperature: float | None = 1.0
    max_tokens: int | None = 8192


def resolve_cloud_options(options: CloudClientOptions) -> ResolvedCloudOptions:
    app_config = load_app_config(options.config_path).cloud
    api_base = (app_config.api_base or "").rstrip("/")
    api_key = app_config.api_key
    model = app_config.model
    timeout = app_config.timeout
    temperature = app_config.temperature
    max_tokens = app_config.max_tokens
    if not api_base:
        raise ValueError("Missing cloud API base. Open Settings or edit config.toml.")
    if not api_key:
        raise ValueError("Missing cloud API key. Open Settings or edit config.toml.")
    if not model:
        raise ValueError("Missing cloud model. Open Settings or edit config.toml.")
    return ResolvedCloudOptions(
        api_base=api_base,
        api_key=api_key,
        model=model,
        config_path=options.config_path,
        timeout=timeout,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def extract_responses_content(response_payload: dict[str, Any]) -> str:
    output_text = response_payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    output = response_payload.get("output")
    if not isinstance(output, list):
        raise ValueError("Cloud responses API response is missing output.")
    for item in output:
        if not isinstance(item, dict):
            continue
        content_items = item.get("content")
        if not isinstance(content_items, list):
            continue
        for content in content_items:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text
            if isinstance(text, dict):
                value = text.get("value")
                if isinstance(value, str) and value.strip():
                    return value
    incomplete = response_payload.get("incomplete_details")
    if isinstance(incomplete, dict) and incomplete.get("reason") == "max_output_tokens":
        raise ValueError("Cloud response reached token limit before producing final content.")
    raise ValueError("Cloud responses API response has no text content.")


def _build_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _build_responses_payload(
    *,
    model: str,
    system_prompt: str,
    user_content: str,
    temperature: float | None = 1.0,
    max_tokens: int | None = 8192,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "store": False,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_output_tokens"] = max_tokens
    return payload


def call_openai_compatible_chat(
    *,
    system_prompt: str,
    user_content: str,
    options: CloudClientOptions,
    audit_path: str | Path | None = None,
) -> str:
    resolved = resolve_cloud_options(options)
    payload = _build_responses_payload(
        model=str(resolved.model),
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=resolved.temperature,
        max_tokens=resolved.max_tokens,
    )
    url = f"{resolved.api_base}/responses"
    with httpx.Client(timeout=resolved.timeout) as client:
        response = client.post(
            url,
            headers=_build_headers(str(resolved.api_key)),
            json=payload,
        )
        response.raise_for_status()
        response_payload = response.json()
    if audit_path is not None:
        write_json_atomic(
            audit_path,
            {
                "api": "responses",
                "api_base": resolved.api_base,
                "model": resolved.model,
                "request": {**payload, "input": "[redacted in audit]"},
                "response": response_payload,
            },
        )
    return extract_responses_content(response_payload)


def _extract_responses_stream_delta(payload: dict[str, Any]) -> str:
    if payload.get("type") == "response.output_text.delta":
        delta = payload.get("delta")
        return delta if isinstance(delta, str) else ""
    delta = payload.get("delta")
    if isinstance(delta, str):
        return delta
    text = payload.get("text")
    if isinstance(text, str):
        return text
    return ""


def call_openai_compatible_chat_stream(
    *,
    system_prompt: str,
    user_content: str,
    options: CloudClientOptions,
    on_delta: Callable[[str], None],
    audit_path: str | Path | None = None,
) -> str:
    resolved = resolve_cloud_options(options)
    payload = _build_responses_payload(
        model=str(resolved.model),
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=resolved.temperature,
        max_tokens=resolved.max_tokens,
    )
    payload["stream"] = True
    url = f"{resolved.api_base}/responses"
    chunks: list[str] = []
    raw_events: list[dict[str, Any]] = []
    with httpx.Client(timeout=resolved.timeout) as client:
        with client.stream(
            "POST",
            url,
            headers=_build_headers(str(resolved.api_key)),
            json=payload,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    line = line.removeprefix("data:").strip()
                if line == "[DONE]":
                    break
                event = json.loads(line)
                raw_events.append(event)
                delta = _extract_responses_stream_delta(event)
                if delta:
                    chunks.append(delta)
                    on_delta(delta)
    content = "".join(chunks)
    if audit_path is not None:
        write_json_atomic(
            audit_path,
            {
                "api": "responses",
                "api_base": resolved.api_base,
                "model": resolved.model,
                "request": {**payload, "input": "[redacted in audit]"},
                "response": {"streamed": True, "content": content, "events": raw_events},
            },
        )
    if content.strip():
        return content
    raise ValueError("Cloud responses API response has no text content.")


def read_prompt_template(path: str | Path) -> str:
    text = read_text(path)
    if not text:
        raise FileNotFoundError(f"Prompt template is missing or empty: {path}")
    return text
