import json

import httpx
import pytest

from atot.cloud.client import (
    CloudClientOptions,
    _build_headers,
    _build_responses_payload,
    call_openai_compatible_chat,
    extract_responses_content,
    resolve_cloud_options,
)


def test_resolve_cloud_options_reads_app_config(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "config.toml").write_text(
        """
[cloud]
api_base = "https://example.test/v1"
api_key = "secret-key"
model = "gpt-4o-mini"
model_options = ["gpt-4o-mini", "gpt-5.5"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    config_path = data_root / "config.toml"

    resolved = resolve_cloud_options(CloudClientOptions(config_path=config_path))

    assert resolved.api_base == "https://example.test/v1"
    assert resolved.api_key == "secret-key"
    assert resolved.model == "gpt-4o-mini"


def test_resolve_cloud_options_ignores_removed_cloud_switches(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "config.toml").write_text(
        """
[cloud]
api_base = "https://v2.example.test/v1"
api_key = "v2-secret"
model = "gpt-v2"
auth_mode = "api-key"
wire_api = "chat_completions"
model_options = ["gpt-v2", "gpt-next"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    resolved = resolve_cloud_options(CloudClientOptions(config_path=data_root / "config.toml"))

    assert resolved.api_base == "https://v2.example.test/v1"
    assert resolved.api_key == "v2-secret"
    assert resolved.model == "gpt-v2"
    assert not hasattr(resolved, "auth_mode")
    assert not hasattr(resolved, "wire_api")


def test_resolve_cloud_options_ignores_environment_when_config_is_set(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "config.toml").write_text(
        """
[cloud]
api_base = "https://example.test/v1"
api_key = "secret-key"
model = "gpt-4o-mini"
model_options = ["gpt-4o-mini", "gpt-5.5"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    config_path = data_root / "config.toml"
    monkeypatch.setenv("ATOT_CLOUD_API_BASE", "https://env.test/v1")
    monkeypatch.setenv("ATOT_CLOUD_API_KEY", "env-key")
    monkeypatch.setenv("ATOT_CLOUD_MODEL", "env-model")
    monkeypatch.setenv("ATOT_CLOUD_AUTH_MODE", "bearer")
    monkeypatch.setenv("ATOT_CLOUD_WIRE_API", "chat_completions")

    resolved = resolve_cloud_options(CloudClientOptions(config_path=config_path))

    assert resolved.api_base == "https://example.test/v1"
    assert resolved.api_key == "secret-key"
    assert resolved.model == "gpt-4o-mini"


def test_resolve_cloud_options_ignores_top_level_provider_config(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
model_provider = "OpenAI"
model = "unused-model"

[model_providers.OpenAI]
name = "OpenAI"
base_url = "https://unused.example.test/v1"
api_key = "unused-key"
auth_mode = "api-key"
wire_api = "responses"
model_options = ["unused-model"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing cloud API base"):
        resolve_cloud_options(CloudClientOptions(config_path=config_path))


def test_build_headers_uses_bearer_only():
    assert _build_headers("secret") == {
        "Authorization": "Bearer secret",
        "Content-Type": "application/json",
    }


def test_build_responses_payload_uses_max_output_tokens():
    payload = _build_responses_payload(
        model="gpt-5.2-chat-latest",
        system_prompt="sys",
        user_content="user",
        temperature=0.5,
        max_tokens=321,
    )

    assert payload["model"] == "gpt-5.2-chat-latest"
    assert payload["max_output_tokens"] == 321
    assert payload["temperature"] == 0.5
    assert payload["store"] is False
    assert payload["input"][0]["role"] == "system"
    assert payload["input"][1]["role"] == "user"


def test_call_openai_compatible_chat_posts_responses_api_with_bearer(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[cloud]
api_base = "https://example.test/v1"
api_key = "secret-key"
model = "gpt-test"
timeout = 12
temperature = 0.25
max_tokens = 64
""".strip()
        + "\n",
        encoding="utf-8",
    )
    requests = []
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url == "https://example.test/v1/responses"
        assert request.headers["Authorization"] == "Bearer secret-key"
        assert "api-key" not in request.headers
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "gpt-test"
        assert payload["max_output_tokens"] == 64
        assert payload["store"] is False
        assert "input" in payload
        assert "messages" not in payload
        return httpx.Response(200, json={"output_text": "ok"})

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout
            self.transport = httpx.MockTransport(handler)
            self.client = original_client(transport=self.transport)

        def __enter__(self):
            assert self.timeout == 12
            return self

        def __exit__(self, exc_type, exc, tb):
            self.client.close()

        def post(self, *args, **kwargs):
            return self.client.post(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", FakeClient)

    result = call_openai_compatible_chat(
        system_prompt="sys",
        user_content="user",
        options=CloudClientOptions(config_path=config_path),
    )

    assert result == "ok"
    assert len(requests) == 1


def test_call_openai_compatible_chat_records_responses_api_in_audit(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[cloud]
api_base = "https://example.test/v1"
api_key = "secret-key"
model = "gpt-test"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    audit_path = tmp_path / "summarize.api_run.json"
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://example.test/v1/responses"
        return httpx.Response(200, json={"output_text": "ok"})

    class FakeClient:
        def __init__(self, *, timeout):
            self.client = original_client(transport=httpx.MockTransport(handler))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.client.close()

        def post(self, *args, **kwargs):
            return self.client.post(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", FakeClient)

    assert (
        call_openai_compatible_chat(
            system_prompt="sys",
            user_content="user",
            options=CloudClientOptions(config_path=config_path),
            audit_path=audit_path,
        )
        == "ok"
    )

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["api"] == "responses"
    assert audit["request"]["input"] == "[redacted in audit]"
    assert "messages" not in audit["request"]


def test_call_openai_compatible_chat_raises_when_responses_has_no_text_without_fallback(
    tmp_path,
    monkeypatch,
):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[cloud]
api_base = "https://example.test/v1"
api_key = "secret-key"
model = "gpt-test"
timeout = 12
temperature = 0.25
max_tokens = 64
""".strip()
        + "\n",
        encoding="utf-8",
    )
    audit_path = tmp_path / "chunk.api_run.json"
    requests = []
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content.decode("utf-8"))
        assert request.url == "https://example.test/v1/responses"
        assert request.headers["Authorization"] == "Bearer secret-key"
        assert payload["max_output_tokens"] == 64
        assert "input" in payload
        assert "messages" not in payload
        return httpx.Response(200, json={"status": "completed", "output": []})

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout
            self.transport = httpx.MockTransport(handler)
            self.client = original_client(transport=self.transport)

        def __enter__(self):
            assert self.timeout == 12
            return self

        def __exit__(self, exc_type, exc, tb):
            self.client.close()

        def post(self, *args, **kwargs):
            return self.client.post(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", FakeClient)

    with pytest.raises(ValueError, match="Cloud responses API response has no text content"):
        call_openai_compatible_chat(
            system_prompt="sys",
            user_content="user",
            options=CloudClientOptions(config_path=config_path),
            audit_path=audit_path,
        )

    assert [str(request.url) for request in requests] == [
        "https://example.test/v1/responses",
    ]
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["api"] == "responses"
    assert audit["request"]["input"] == "[redacted in audit]"
    assert "messages" not in audit["request"]
    assert audit["response"]["output"] == []
    assert "attempts" not in audit
    assert "fallback_from" not in audit
    assert "secret-key" not in json.dumps(audit, ensure_ascii=False)


def test_extract_responses_content_reads_output_text():
    payload = {"output_text": "hello"}

    assert extract_responses_content(payload) == "hello"


def test_extract_responses_content_reads_nested_text():
    payload = {
        "output": [
            {
                "content": [
                    {
                        "type": "output_text",
                        "text": "hello from nested",
                    }
                ]
            }
        ]
    }

    assert extract_responses_content(payload) == "hello from nested"


def test_extract_responses_content_reads_nested_text_value():
    payload = {
        "output": [
            {
                "content": [
                    {
                        "type": "output_text",
                        "text": {"value": "hello from value"},
                    }
                ]
            }
        ]
    }

    assert extract_responses_content(payload) == "hello from value"
