from dataclasses import replace
from pathlib import Path

import pytest

from atot import cli
from atot.config_v2 import (
    AtotConfig,
    AtotLibraryConfig,
    AtotLocalConfig,
    load_atot_config,
    set_config_value,
)
from atot.languages import resolve_languages, output_language_instruction
from atot.pipeline import TranscribeOptions
from atot.pipeline.identity import _transcription_fingerprint
from atot.service_protocol import handle_service_request
from atot.task_store import TaskStore
from atot.workflow_service import WorkflowService


def test_language_defaults_migration_and_legacy_setter(tmp_path):
    path = tmp_path / "config.toml"
    config = load_atot_config(path, include_api_key=False)
    assert config.local.requested_languages == []
    assert config.summary.language == "zh"
    path.write_text('[local]\nlanguage = "jp"\nbackend = "recording"\n')
    assert load_atot_config(path, include_api_key=False).local.requested_languages == ["ja"]
    set_config_value("local.languages", ["zh", "en", "zh"], path=path)
    set_config_value("summary.language", "en", path=path)
    config = load_atot_config(path, include_api_key=False)
    assert config.local.requested_languages == ["zh", "en"]
    assert config.local.backend == "recording"
    assert config.summary.language == "en"
    assert "language" not in config.raw["local"]
    set_config_value("local.language", "auto", path=path)
    assert load_atot_config(path, include_api_key=False).local.requested_languages == []
    assert load_atot_config(
        path, overrides=['local.language="ja"'], include_api_key=False
    ).local.requested_languages == ["ja"]


@pytest.mark.parametrize(
    "values,expected",
    [
        ([], (None, [])),
        (["zh"], ("zh", ["zh"])),
        (["zh", "en", "zh"], (None, ["zh", "en"])),
        (["jp"], ("ja", ["ja"])),
        (["en", "auto"], (None, [])),
    ],
)
def test_language_resolution(values, expected):
    assert resolve_languages(values) == expected


def test_invalid_language_config_fails_explicitly(tmp_path):
    path = tmp_path / "config.toml"
    for text in [
        '[local]\nlanguages = "en"',
        '[summary]\nlanguage = "auto"',
        '[local]\nlanguages = ["unknown"]',
    ]:
        path.write_text(text)
        with pytest.raises(ValueError):
            load_atot_config(path, include_api_key=False)


@pytest.mark.parametrize(
    "languages,hint", [([], None), (["en"], "en"), (["zh"], "zh"), (["zh", "en"], None)]
)
def test_workflow_forwards_effective_and_requested_languages(
    monkeypatch, tmp_path, languages, hint
):
    config = AtotConfig(
        path=tmp_path / "config.toml",
        local=AtotLocalConfig(languages=languages),
        library=AtotLibraryConfig(storage="local", local_root=str(tmp_path / "library")),
    )
    service = WorkflowService(config=config, task_store=TaskStore(tmp_path / "tasks"))
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")
    captured = []

    def capture(options):
        captured.append(options)
        raise RuntimeError("captured without ASR")

    monkeypatch.setattr("atot.workflow_service.run_transcription", capture)
    with pytest.raises(RuntimeError, match="captured"):
        service.run_transcribe(source, local_only=True)
    options = captured[0]
    assert options.language == hint
    assert options.requested_languages == tuple(languages)
    assert (options.prompt_file is not None) == (hint == "zh")
    assert (options.glossary_file is not None) == (hint == "zh")
    with pytest.raises(ValueError, match="not both"):
        service.run_transcribe(source, language="zh", languages=[])


def test_service_empty_array_overrides_saved_language(tmp_path):
    seen = []

    class Service:
        def run_srt(self, inputs, **kwargs):
            seen.append(kwargs)
            return {"success": True}

    response = handle_service_request(
        {"method": "srt", "params": {"inputs": ["episode.wav"], "languages": []}}, service=Service()
    )
    assert response["ok"] is True
    assert seen[0]["languages"] == []


def test_cli_repeatable_languages_reach_workflow(monkeypatch, tmp_path):
    seen = []

    class Service:
        def run_transcribe(self, source, **kwargs):
            seen.append(kwargs)
            return {"success": True}

    (tmp_path / "episode.wav").write_bytes(b"audio")
    monkeypatch.setattr(cli, "_service", lambda *a, **k: Service())
    assert (
        cli.main(
            [
                "exec",
                "transcribe",
                str(tmp_path / "episode.wav"),
                "--language",
                "zh",
                "--language",
                "en",
                "--json",
            ]
        )
        == 0
    )
    assert seen[0]["languages"] == ["zh", "en"]


def test_requested_language_hints_invalidate_asr_cache():
    base = TranscribeOptions(input_path=Path("episode.wav"), language=None)

    def fingerprint(options):
        return _transcription_fingerprint(
            backend_name="recording", model="test", options=options, prompt=None
        )

    assert fingerprint(base) != fingerprint(replace(base, requested_languages=("zh", "en")))
    assert "overrides conflicting language" in output_language_instruction("en")
