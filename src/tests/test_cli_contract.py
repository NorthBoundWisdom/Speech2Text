from __future__ import annotations

import json
from io import BytesIO

import pytest

from atot import cli
from atot.config import load_app_config
from atot.config_v2 import load_atot_config, parse_config_overrides, read_config_value
from atot.redaction import redact_sensitive
from atot.service import _read_json_request, handle_service_request
from atot.task_store import TaskStore
from atot.tui import parse_slash_command
from atot.utils import write_json_atomic, write_text_atomic
from atot.workflow_service import WorkflowService


def test_top_level_help_exposes_v2_surface(capsys):
    rc = cli.main(["--help"])

    output = capsys.readouterr().out
    assert rc == 0
    assert "exec" in output
    assert "resume" in output
    assert "config" in output
    assert "serve" in output
    assert "mcp" in output


def test_mcp_is_a_command_instead_of_an_interactive_prompt(capsys):
    assert not cli._looks_like_interactive_prompt(["mcp"])
    assert cli.main(["mcp", "--help"]) == 0
    assert "MCP" in capsys.readouterr().out


def test_old_top_level_transcribe_is_removed(capsys):
    rc = cli.main(["transcribe", "episode.wav"])

    assert rc != 0
    assert "No such command" in capsys.readouterr().err


def test_config_overrides_parse_toml_values(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('[local]\nasr_model = "large-v3-turbo"\n', encoding="utf-8")

    config = load_atot_config(
        config_path,
        overrides=[
            'local.language="ja"',
            "workflow.chunk_length=900",
            "workflow.local_only=true",
            'library.storage="local"',
            'library.local_root="/tmp/audio2text-library"',
        ],
    )

    assert parse_config_overrides(["workflow.chunk_length=900"]) == [("workflow.chunk_length", 900)]
    assert config.local.language == "ja"
    assert config.workflow.chunk_length == 900
    assert config.workflow.local_only is True
    assert config.library.storage == "local"
    assert config.library.local_root == "/tmp/audio2text-library"


def test_config_overrides_accept_windows_path_strings():
    overrides = parse_config_overrides([r'library.local_root="C:\Users\me\Audio2TextLibrary"'])

    assert overrides == [("library.local_root", r"C:\Users\me\Audio2TextLibrary")]


def test_config_overrides_reject_invalid_key_and_empty_value():
    with pytest.raises(ValueError, match="Top-level key"):
        parse_config_overrides(["unknown.value=1"])
    with pytest.raises(ValueError, match="dotted identifiers"):
        parse_config_overrides(['local={language="zh"}'])
    with pytest.raises(ValueError, match="dotted identifiers"):
        parse_config_overrides(['local..language="zh"'])
    with pytest.raises(ValueError, match="empty value"):
        parse_config_overrides(["local.language="])
    with pytest.raises(ValueError, match="Invalid TOML"):
        parse_config_overrides(['local.language="unterminated'])


def test_config_get_allows_top_level_sections(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('[local]\nlanguage = "ja"\n', encoding="utf-8")

    assert read_config_value("local", path=config_path) == {"language": "ja"}


def test_config_v2_keeps_v1_shared_defaults_compatible(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
        [local]
        asr_model = "large-v3-turbo"
        asr_profile = "balanced_zh_podcast"

        [cloud]
        timeout = 123.5
        max_tokens = 4096
        """,
        encoding="utf-8",
    )

    app_config = load_app_config(config_path)
    modern = load_atot_config(config_path)

    assert modern.local.asr_model == app_config.local.asr_model
    assert modern.local.asr_profile == app_config.local.asr_profile
    assert modern.cloud.timeout == app_config.cloud.timeout
    assert modern.cloud.max_tokens == app_config.cloud.max_tokens


def test_prompt_mode_accepts_leading_config_override(monkeypatch):
    captured = {}

    def fake_run_tui(prompt, *, config_overrides):
        captured["prompt"] = prompt
        captured["config_overrides"] = config_overrides
        return 0

    monkeypatch.setattr("atot.tui.run_tui", fake_run_tui)

    rc = cli.main(["-c", 'local.language="en"', "导入这一集"])

    assert rc == 0
    assert captured == {
        "prompt": "导入这一集",
        "config_overrides": ['local.language="en"'],
    }


def test_library_status_uses_configured_local_root(tmp_path, capsys):
    library_root = tmp_path / "Audio2TextLibrary"

    rc = cli.main(
        [
            "-c",
            'library.storage="local"',
            "-c",
            f'library.local_root="{library_root}"',
            "exec",
            "library",
            "status",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["library_root"] == str(library_root)


def test_task_store_persists_required_event_shape(tmp_path):
    store = TaskStore(tmp_path)
    task = store.create_task("transcribe", "episode")
    store.append(task, "task.stage", stage="transcribe")
    store.append(task, "task.progress", completed=1, total=2)
    store.append(task, "task.finished", success=True)

    events = store.events(task.task_id)
    assert [event["event"] for event in events] == [
        "task.created",
        "task.stage",
        "task.progress",
        "task.finished",
    ]
    assert store.status(task.task_id)["last_event"]["event"] == "task.finished"


def test_service_status_request_uses_shared_task_store(tmp_path):
    store = TaskStore(tmp_path)
    task = store.create_task("qa", "output")
    service = WorkflowService(task_store=store)

    response = handle_service_request(
        {"id": "1", "method": "status", "params": {"task_id": task.task_id}},
        service=service,
    )

    assert response["ok"] is True
    assert response["result"]["task"]["task_id"] == task.task_id


def test_service_redacts_sensitive_config_values(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("atot.config_v2.config_path", lambda: config_path)
    service = WorkflowService()

    response = handle_service_request(
        {
            "id": "1",
            "method": "config_set",
            "params": {"key": "cloud.api_key", "value": "sk-secret"},
        },
        service=service,
    )

    assert response["ok"] is True
    assert response["result"]["path"] == str(config_path)
    assert response["result"]["value"] == "***"
    assert "sk-secret" not in config_path.read_text(encoding="utf-8")
    assert load_atot_config(config_path).cloud.api_key == "sk-secret"


def test_redact_sensitive_handles_nested_payloads():
    payload = {
        "events": [
            {"authorization": "Bearer secret"},
            {"nested": {"api_key": "sk-secret", "keep": "visible"}},
        ]
    }

    assert redact_sensitive(payload) == {
        "events": [
            {"authorization": "***"},
            {"nested": {"api_key": "***", "keep": "visible"}},
        ]
    }


def test_workflow_service_event_sink_receives_redacted_payload(tmp_path):
    captured = []
    service = WorkflowService(task_store=TaskStore(tmp_path), event_sink=captured.append)
    task = service.task_store.create_task("config", "sensitive")

    service._emit(
        task,
        "task.output",
        output={"api_key": "sk-secret", "nested": {"authorization": "Bearer secret"}},
    )

    assert captured[0]["output"] == {"api_key": "***", "nested": {"authorization": "***"}}
    stored = service.task_store.events(task.task_id)[-1]
    assert stored["output"]["api_key"] == "sk-secret"


class _Request:
    def __init__(self, headers, body: bytes) -> None:
        self.headers = {"Content-Type": "application/json", **headers}
        self.rfile = BytesIO(body)


def test_http_service_request_reader_rejects_bad_content_length():
    with pytest.raises(ValueError, match="Missing Content-Length"):
        _read_json_request(_Request({}, b"{}"))
    with pytest.raises(ValueError, match="integer"):
        _read_json_request(_Request({"Content-Length": "abc"}, b"{}"))
    with pytest.raises(ValueError, match="too large"):
        _read_json_request(_Request({"Content-Length": str(1024 * 1024 + 1)}, b"{}"))


def test_http_service_request_reader_requires_json_object():
    with pytest.raises(ValueError, match="must not be empty"):
        _read_json_request(_Request({"Content-Length": "0"}, b""))
    with pytest.raises(ValueError, match="JSON object"):
        _read_json_request(_Request({"Content-Length": "2"}, b"[]"))
    with pytest.raises(ValueError, match="valid JSON"):
        _read_json_request(_Request({"Content-Length": "1"}, b"{"))


def test_service_module_keeps_compat_reexports():
    from atot import service, service_http, service_protocol, service_stdio

    assert service.handle_service_request is service_protocol.handle_service_request
    assert service.serve_http is service_http.serve_http
    assert service.serve_stdio is service_stdio.serve_stdio
    assert service._read_json_request is service_http.read_json_request


def test_force_and_overwrite_help_text_keeps_public_semantics(capsys, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert cli.main(["exec", "transcribe", "--help"]) == 0
    from rich.text import Text
    transcribe_help = Text.from_ansi(capsys.readouterr().out).plain
    assert "--force" in transcribe_help
    assert all(word in transcribe_help for word in ("Rebuild", "existing", "transcribe", "artifacts"))

    assert cli.main(["exec", "srt", "--help"]) == 0
    srt_help = Text.from_ansi(capsys.readouterr().out).plain
    assert "--overwrite" in srt_help
    assert all(word in srt_help for word in ("Replace", "existing", "SRT", "files"))


def test_slash_command_parser_accepts_documented_commands():
    command = parse_slash_command('/transcribe "episode file.m4a"')

    assert command.name == "transcribe"
    assert command.args == ["episode file.m4a"]


def test_exec_srt_v2_routes_to_existing_srt_pipeline(monkeypatch, tmp_path):
    from atot.commands import srt as srt_commands

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"media")

    def fake_export(input_path, destination, *, args):
        write_text_atomic(destination, "1\n00:00:00,000 --> 00:00:01,000\n你好\n")
        write_json_atomic(
            tmp_path / "seen.json", {"backend": args.backend, "language": args.language}
        )
        return {"success": True, "srt_path": str(destination), "input_path": str(input_path)}

    monkeypatch.setattr(srt_commands, "export_srt_for_input", fake_export)

    rc = cli.main(["exec", "srt", str(source), "--backend", "fake"])

    assert rc == 0
    assert source.with_suffix(".srt").exists()
    assert (tmp_path / "seen.json").exists()


def test_error_message_redacts_tokens_even_without_sensitive_field_name():
    secret = 'sk-' + 'A' * 32
    payload = redact_sensitive({'error': {'message': f'bad credential: {secret} Bearer test-token'}})
    assert secret not in payload['error']['message']
    assert 'test-token' not in payload['error']['message']
