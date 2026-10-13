from __future__ import annotations

from pathlib import Path

from atot import cli
from atot.commands import srt as srt_commands
from atot import transcribe_options as transcribe_options_module
from atot.config import AppConfig, LocalConfig, TranslationConfig
from atot.paths import PathContext
from atot.subtitles import SubtitleCue, validate_srt_text
from atot.translation import SubtitleTranslation
from atot.utils import read_json, write_json_atomic, write_text_atomic


SRT_TEXT = "1\n00:00:00,000 --> 00:00:01,000\n你好\n"


def _patch_srt_runtime(
    monkeypatch, data_root: Path, *, translation: bool = False, backend: str = "local"
) -> None:
    config = AppConfig(
        local=LocalConfig(),
        translation=TranslationConfig(enabled=translation, backend=backend, target_language="zh"),
    )
    context = PathContext(
        data_root=data_root,
        cache_dir=data_root / "cache",
        materials_dir=data_root / "materials",
        work_dir=data_root / "work",
        process_dir=data_root / "materials",
        tools_dir=data_root / "cache" / "tools",
        model_dir=data_root / "model",
        env_dir=data_root / "env",
        output_dir=data_root / "work",
    )
    monkeypatch.setattr(srt_commands, "load_app_config", lambda **kwargs: config)
    monkeypatch.setattr(transcribe_options_module, "load_app_config", lambda **kwargs: config)
    monkeypatch.setattr(srt_commands, "path_context", lambda: context)
    monkeypatch.setattr(transcribe_options_module, "path_context", lambda: context)


def _fake_run_factory(seen: list):
    def fake_run(options):
        seen.append(options)
        job_dir = Path(options.job_dir)
        segment = {"id": 0, "start": 0.0, "end": 1.0, "text": "hello"}
        write_text_atomic(job_dir / "transcript.srt", SRT_TEXT)
        write_json_atomic(
            job_dir / "corrected.json",
            {"segments": [segment], "text": "hello", "language": options.language},
        )
        write_json_atomic(job_dir / "run.json", {"success": True})
        return {
            "success": True,
            "job_dir": str(job_dir),
            "language": options.language,
            "qa": {"status": "pass"},
            "output_files": {"transcript.srt": str(job_dir / "transcript.srt")},
        }

    return fake_run


def test_srt_writes_next_to_source_and_uses_cache(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"media")
    seen = []
    _patch_srt_runtime(monkeypatch, data_root)
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    rc = cli.main(["exec", "srt", str(source), "--backend", "fake"])

    assert rc == 0
    assert source.with_suffix(".srt").read_text(encoding="utf-8") == SRT_TEXT
    assert len(seen) == 1
    assert seen[0].job_dir.parent == data_root / "cache" / "srt"
    assert seen[0].output_dir == data_root / "cache" / "srt"
    assert seen[0].local_only is True
    assert not (data_root / "materials").exists()
    assert not (data_root / "work").exists()
    metadata = read_json(Path(seen[0].job_dir) / "srt_export.json")
    assert metadata["requested_languages"] == []
    assert metadata["asr_language"] is None


def test_srt_refuses_existing_output_without_overwrite(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    target = source.with_suffix(".srt")
    source.write_bytes(b"media")
    target.write_text("existing\n", encoding="utf-8")
    seen = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    rc = cli.main(["exec", "srt", str(source), "--backend", "fake"])

    assert rc == 1
    assert target.read_text(encoding="utf-8") == "existing\n"
    assert seen == []


def test_srt_overwrite_replaces_existing_output(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    target = source.with_suffix(".srt")
    source.write_bytes(b"media")
    target.write_text("existing\n", encoding="utf-8")
    seen = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    rc = cli.main(["exec", "srt", str(source), "--backend", "fake", "--overwrite"])

    assert rc == 0
    assert target.read_text(encoding="utf-8") == SRT_TEXT
    assert len(seen) == 1


def test_srt_repeated_language_enables_auto_detection(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"media")
    seen = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    rc = cli.main(
        ["exec", "srt", str(source), "--language", "zh", "--language", "en", "--backend", "fake"]
    )

    assert rc == 0
    assert seen[0].language is None
    metadata = read_json(Path(seen[0].job_dir) / "srt_export.json")
    assert metadata["requested_languages"] == ["zh", "en"]
    assert metadata["asr_language"] is None


def test_srt_auto_language_enables_auto_detection(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"media")
    seen = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    rc = cli.main(["exec", "srt", str(source), "--language", "auto", "--backend", "fake"])

    assert rc == 0
    assert seen[0].language is None
    metadata = read_json(Path(seen[0].job_dir) / "srt_export.json")
    assert metadata["requested_languages"] == []


def test_srt_jp_language_alias_passes_japanese_code(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"media")
    seen = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    rc = cli.main(["exec", "srt", str(source), "--language", "jp", "--backend", "fake"])

    assert rc == 0
    assert seen[0].language == "ja"
    metadata = read_json(Path(seen[0].job_dir) / "srt_export.json")
    assert metadata["requested_languages"] == ["ja"]
    assert metadata["asr_language"] == "ja"


def test_srt_output_path_is_single_input_only(tmp_path):
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"media")
    second.write_bytes(b"media")

    rc = cli.main(["exec", "srt", str(first), str(second), "--output", str(tmp_path / "out.srt")])

    assert rc == 1


def test_srt_target_language_writes_translated_output_and_metadata(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"media")
    seen = []
    translations = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data", translation=True, backend="local")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    def fake_translate(cues, *, source_language, target_language, model_alias):
        translations.append(
            {
                "source_language": source_language,
                "target_language": target_language,
                "cue_texts": [cue.text for cue in cues],
                "model_alias": model_alias,
            }
        )
        return SubtitleTranslation(
            cues=[
                SubtitleCue(index=cue.index, start=cue.start, end=cue.end, text="你好")
                for cue in cues
            ],
            metadata={
                "model": model_alias,
                "device": "fake",
                "runtime_seconds": 0.01,
                "cue_count": len(cues),
            },
        )

    monkeypatch.setattr(srt_commands, "translate_subtitle_cues", fake_translate)

    rc = cli.main(["exec", "srt", str(source), "--language", "en", "--backend", "fake"])

    assert rc == 0
    target = source.with_suffix(".zh.srt")
    text = target.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,000" in text
    assert "你好" in text
    assert validate_srt_text(text) == []
    assert translations == [
        {
            "source_language": "en",
            "target_language": "zh",
            "cue_texts": ["hello"],
            "model_alias": "nllb-200-distilled-600m",
        }
    ]
    metadata = read_json(Path(seen[0].job_dir) / "srt_export.json")
    assert metadata["target_language"] == "zh"
    assert metadata["source_language"] == "en"
    assert metadata["translation"]["device"] == "fake"
    assert (Path(seen[0].job_dir) / "transcript.zh.srt").exists()
    assert (Path(seen[0].job_dir) / "translation.zh.json").exists()


def test_srt_cloud_translation_backend_writes_translated_output_and_metadata(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"media")
    seen = []
    translations = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data", translation=True, backend="cloud")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    def fake_cloud_translate(cues, *, source_language, target_language, audit_dir):
        translations.append(
            {
                "source_language": source_language,
                "target_language": target_language,
                "cue_texts": [cue.text for cue in cues],
                "audit_dir": audit_dir.name,
            }
        )
        return SubtitleTranslation(
            cues=[
                SubtitleCue(index=cue.index, start=cue.start, end=cue.end, text="云端你好")
                for cue in cues
            ],
            metadata={
                "backend": "cloud",
                "model": "cloud-model",
                "api": "responses",
                "runtime_seconds": 0.01,
                "cue_count": len(cues),
            },
        )

    monkeypatch.setattr(srt_commands, "translate_subtitle_cues_cloud", fake_cloud_translate)

    rc = cli.main(
        [
            "exec",
            "srt",
            str(source),
            "--language",
            "en",
            "--backend",
            "fake",
        ]
    )

    assert rc == 0
    target = source.with_suffix(".zh.srt")
    text = target.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,000" in text
    assert "云端你好" in text
    assert validate_srt_text(text) == []
    assert translations == [
        {
            "source_language": "en",
            "target_language": "zh",
            "cue_texts": ["hello"],
            "audit_dir": Path(seen[0].job_dir).name,
        }
    ]
    metadata = read_json(Path(seen[0].job_dir) / "srt_export.json")
    assert metadata["translation"]["backend"] == "cloud"
    assert metadata["translation"]["translation_model"] == "cloud-model"


def test_srt_translation_drops_default_chinese_context_for_english_source(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"media")
    seen = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data", translation=True, backend="local")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))
    monkeypatch.setattr(
        srt_commands,
        "translate_subtitle_cues",
        lambda cues, **kwargs: SubtitleTranslation(
            cues=[
                SubtitleCue(index=cue.index, start=cue.start, end=cue.end, text="你好")
                for cue in cues
            ],
            metadata={"model": "fake", "device": "fake"},
        ),
    )

    rc = cli.main(["exec", "srt", str(source), "--language", "en", "--backend", "fake"])

    assert rc == 0
    assert seen[0].prompt_file is None
    assert seen[0].glossary_file is None


def test_srt_translation_keeps_default_chinese_context_for_chinese_source(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"media")
    seen = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data", translation=True, backend="local")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    rc = cli.main(["exec", "srt", str(source), "--language", "zh", "--backend", "fake"])

    assert rc == 0
    assert seen[0].prompt_file is not None
    assert seen[0].glossary_file is not None


def test_srt_target_language_output_dir_uses_language_suffix(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    output_dir = tmp_path / "subs"
    source.write_bytes(b"media")
    seen = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data", translation=True, backend="local")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    rc = cli.main(
        [
            "exec",
            "srt",
            str(source),
            "--language",
            "zh",
            "--output-dir",
            str(output_dir),
            "--backend",
            "fake",
        ]
    )

    assert rc == 0
    assert (output_dir / "episode.zh.srt").exists()


def test_srt_target_language_refuses_existing_without_overwrite(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    target = source.with_suffix(".zh.srt")
    source.write_bytes(b"media")
    target.write_text("existing\n", encoding="utf-8")
    seen = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data", translation=True, backend="local")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))

    rc = cli.main(["exec", "srt", str(source), "--backend", "fake"])

    assert rc == 1
    assert target.read_text(encoding="utf-8") == "existing\n"
    assert seen == []


def test_srt_translation_mismatched_cue_count_fails(monkeypatch, tmp_path):
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"media")
    seen = []
    _patch_srt_runtime(monkeypatch, tmp_path / "data", translation=True, backend="local")
    monkeypatch.setattr(srt_commands, "run_transcription", _fake_run_factory(seen))
    monkeypatch.setattr(
        srt_commands,
        "translate_subtitle_cues",
        lambda *_args, **_kwargs: SubtitleTranslation(cues=[], metadata={"model": "fake"}),
    )

    rc = cli.main(["exec", "srt", str(source), "--language", "en", "--backend", "fake"])

    assert rc == 1
    assert not source.with_suffix(".zh.srt").exists()
