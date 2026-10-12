from pathlib import Path

from atot import pipeline as pipeline_module
from atot.audio import ChunkSpec, prepare_audio_command
from atot.backends import ASRTranscribeOptions
from atot.pipeline import TranscribeOptions, run_transcription
from atot.pipeline.asr import (
    ASRChunkCacheDecision,
    _chunk_cache_decision,
)
from atot.pipeline.audio_cache import (
    PreparedAudioCacheDecision,
    prepared_audio_cache_decision,
    prepared_meta_matches,
    prepared_meta_payload,
)
from atot.pipeline.chunks import _payload_matches_chunk
from atot.pipeline.identity import (
    _payload_matches_fingerprint,
    _postprocess_fingerprint,
    _sha256_json,
    _transcription_fingerprint,
)
from atot.utils import read_json, write_json_atomic


def test_transcription_fingerprint_changes_with_model_and_prompt():
    base = TranscribeOptions(input_path=Path("episode.m4a"), model="large-v3-turbo")
    changed_model = TranscribeOptions(input_path=Path("episode.m4a"), model="large-v3")

    first = _transcription_fingerprint(
        backend_name="mlx-whisper",
        model="mlx-community/whisper-large-v3-turbo",
        options=base,
        prompt="术语：ChatGPT",
    )
    same = _transcription_fingerprint(
        backend_name="mlx-whisper",
        model="mlx-community/whisper-large-v3-turbo",
        options=base,
        prompt="术语：ChatGPT",
    )
    different = _transcription_fingerprint(
        backend_name="mlx-whisper",
        model="mlx-community/whisper-large-v3-mlx",
        options=changed_model,
        prompt="术语：ChatGPT",
    )

    assert first == same
    assert first["version"] == 2
    assert "decode_guard" in first
    assert "high_compression_segment" in first["decode_guard"]["retry_triggers"]
    assert first != different
    assert (
        first["prompt_sha256"]
        != _transcription_fingerprint(
            backend_name="mlx-whisper",
            model="mlx-community/whisper-large-v3-turbo",
            options=base,
            prompt="术语：Claude",
        )["prompt_sha256"]
    )
    assert first["chunk_layout_sha256"] is None
    assert first != _transcription_fingerprint(
        backend_name="mlx-whisper",
        model="mlx-community/whisper-large-v3-turbo",
        options=base,
        prompt="术语：ChatGPT",
        chunk_layout_sha256="different-layout",
    )


def test_postprocess_fingerprint_changes_with_correction_rules():
    first = _postprocess_fingerprint({"common_corrections": {"本课": "本科"}})
    second = _postprocess_fingerprint({"common_corrections": {"本课": "本壳"}})
    with_pack = _postprocess_fingerprint(
        {"common_corrections": {"本课": "本科"}}, rule_packs=("tech_ai_zh",)
    )

    assert first != second
    assert first["glossary_sha256"] != second["glossary_sha256"]
    assert first != with_pack
    assert with_pack["rule_set"]["request"] == ["tech_ai_zh"]


def test_prepared_meta_matches_input_sample_rate_and_prepare_command(tmp_path):
    meta_path = tmp_path / "prepared.meta.json"
    input_file = {"sha256": "a" * 64}
    prepared_audio = {"sha256": "b" * 64, "sample_rate": 16000}
    prepare_command = {
        "tool": "ffmpeg",
        "available": True,
        "args": ["ffmpeg", "-i", "input.wav", "prepared.wav"],
    }

    assert not prepared_meta_matches(
        meta_path,
        input_file=input_file,
        sample_rate=16000,
        prepare_command=prepare_command,
    )

    write_json_atomic(
        meta_path,
        prepared_meta_payload(
            input_file=input_file,
            prepared_audio=prepared_audio,
            prepare_command=prepare_command,
            sample_rate=16000,
        ),
    )

    assert prepared_meta_matches(
        meta_path,
        input_file=input_file,
        sample_rate=16000,
        prepare_command=prepare_command,
    )
    assert not prepared_meta_matches(
        meta_path,
        input_file={**input_file, "sha256": "c" * 64},
        sample_rate=16000,
        prepare_command=prepare_command,
    )
    assert not prepared_meta_matches(
        meta_path,
        input_file=input_file,
        sample_rate=8000,
        prepare_command=prepare_command,
    )


def test_prepared_audio_cache_decision_tracks_force_input_and_meta_mismatch(tmp_path):
    prepared_wav = tmp_path / "prepared.wav"
    meta_path = tmp_path / "prepared.meta.json"
    input_file = {"sha256": "a" * 64}
    prepared_audio = {"sha256": "b" * 64, "sample_rate": 16000}
    prepare_command = {
        "tool": "ffmpeg",
        "available": True,
        "args": ["ffmpeg", "-i", "input.wav", "prepared.wav"],
    }

    missing = prepared_audio_cache_decision(
        prepared_wav=prepared_wav,
        meta_path=meta_path,
        input_file=input_file,
        sample_rate=16000,
        prepare_command=prepare_command,
        force_prepare=False,
        input_changed=False,
    )
    assert missing == PreparedAudioCacheDecision(False, False, "cache_valid_or_missing")

    forced = prepared_audio_cache_decision(
        prepared_wav=prepared_wav,
        meta_path=meta_path,
        input_file=input_file,
        sample_rate=16000,
        prepare_command=prepare_command,
        force_prepare=True,
        input_changed=False,
    )
    assert forced == PreparedAudioCacheDecision(False, True, "force_prepare")

    write_json_atomic(
        meta_path,
        prepared_meta_payload(
            input_file=input_file,
            prepared_audio=prepared_audio,
            prepare_command=prepare_command,
            sample_rate=16000,
        ),
    )
    prepared_wav.write_bytes(b"prepared")

    valid = prepared_audio_cache_decision(
        prepared_wav=prepared_wav,
        meta_path=meta_path,
        input_file=input_file,
        sample_rate=16000,
        prepare_command=prepare_command,
        force_prepare=False,
        input_changed=False,
    )
    assert valid == PreparedAudioCacheDecision(True, False, "cache_valid_or_missing")

    changed_command = {
        **prepare_command,
        "args": ["ffmpeg", "-i", "input.wav", "-ar", "8000", "prepared.wav"],
    }
    mismatch = prepared_audio_cache_decision(
        prepared_wav=prepared_wav,
        meta_path=meta_path,
        input_file=input_file,
        sample_rate=16000,
        prepare_command=changed_command,
        force_prepare=False,
        input_changed=False,
    )
    assert mismatch == PreparedAudioCacheDecision(False, True, "prepared_meta_mismatch")


def test_prepare_audio_command_prefers_ffmpeg_for_video(monkeypatch, tmp_path):
    from atot import audio as audio_module

    monkeypatch.setattr(audio_module, "optional_command", lambda name: None)

    command = prepare_audio_command(tmp_path / "episode.mp4", tmp_path / "prepared.wav")

    assert command["tool"] == "ffmpeg"
    assert command["available"] is False
    assert command["args"][0] == "ffmpeg"


def test_correction_only_glossary_change_reuses_asr_cache_but_refreshes_postprocess(
    tmp_path, monkeypatch
):
    calls: list[str | None] = []

    class FakeBackend:
        name = "fake-asr"
        supports_prompt = True
        supports_word_timestamps = True
        supports_diarization = False

        def __init__(self, *, verbose: bool | None = None) -> None:
            self.verbose = verbose

        def transcribe(self, audio_path: Path, options: ASRTranscribeOptions):
            calls.append(options.prompt)
            return {"text": "本课", "segments": [{"start": 0.0, "end": 1.0, "text": "本课"}]}

    def fake_prepare(_input_path, output_path, *, sample_rate, overwrite):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"prepared")
        return Path(output_path)

    def fake_materialize(_prepared_wav, chunks_dir, *, chunk_length, overlap, overwrite, duration):
        chunk = Path(chunks_dir) / "chunk_0000.wav"
        chunk.parent.mkdir(parents=True, exist_ok=True)
        chunk.write_bytes(b"chunk")
        return [
            ChunkSpec(
                index=0,
                path=chunk,
                source_start=0.0,
                source_end=1.0,
                core_start=0.0,
                core_end=1.0,
            )
        ]

    monkeypatch.setattr(
        pipeline_module,
        "build_backend",
        lambda name, *, recording_json=None, verbose=None: FakeBackend(verbose=verbose),
    )
    monkeypatch.setattr(pipeline_module, "prepare_audio", fake_prepare)
    monkeypatch.setattr(
        pipeline_module,
        "prepare_audio_command",
        lambda input_path, output_path, *, sample_rate: {
            "tool": "ffmpeg",
            "available": True,
            "args": ["ffmpeg", "-i", str(input_path), "-ar", str(sample_rate), str(output_path)],
        },
    )
    monkeypatch.setattr(pipeline_module, "ffprobe_duration", lambda _path: 1.0)
    monkeypatch.setattr(pipeline_module, "materialize_chunks", fake_materialize)

    audio = tmp_path / "episode.wav"
    audio.write_bytes(b"audio")
    first_glossary = tmp_path / "first.json"
    second_glossary = tmp_path / "second.json"
    first_glossary.write_text('{"common_corrections": {"本课": "本科"}}', encoding="utf-8")
    second_glossary.write_text('{"common_corrections": {"本课": "本壳"}}', encoding="utf-8")

    first = run_transcription(
        TranscribeOptions(
            input_path=audio,
            output_dir=tmp_path / "out",
            backend="mlx-whisper",
            glossary_file=first_glossary,
        )
    )
    run_path = tmp_path / "out" / "episode" / "run.json"
    stale_run = read_json(run_path)
    stale_run["chunk_layout_sha256"] = "0" * 64
    write_json_atomic(run_path, stale_run)
    second = run_transcription(
        TranscribeOptions(
            input_path=audio,
            output_dir=tmp_path / "out",
            backend="mlx-whisper",
            glossary_file=second_glossary,
        )
    )

    assert len(calls) == 1
    assert first["chunk_status_counts"] == {
        "transcribed": 1,
        "transcribed_after_cache_mismatch": 0,
        "skipped_existing": 0,
    }
    assert second["chunk_status_counts"] == {
        "transcribed": 0,
        "transcribed_after_cache_mismatch": 0,
        "skipped_existing": 1,
    }
    assert first["transcription_fingerprint_sha256"] == second["transcription_fingerprint_sha256"]
    assert first["postprocess_fingerprint_sha256"] != second["postprocess_fingerprint_sha256"]
    assert first["prepared_audio"]["prepare_tool"] == "ffmpeg"
    assert "ffmpeg" in first["prepared_audio"]["prepare_command"]
    assert first["prepared_audio"]["ffmpeg_command"] == first["prepared_audio"]["prepare_command"]
    prepared_meta = read_json(tmp_path / "out" / "episode" / "prepared.meta.json")
    assert prepared_meta["input_file"]["sha256"] == first["input_file"]["sha256"]
    assert prepared_meta["prepare"]["sample_rate"] == 16_000
    assert prepared_meta["prepared_audio"]["sha256"] == first["prepared_audio"]["sha256"]
    assert second["qa"]["status"] == "pass"
    assert read_json(tmp_path / "out" / "episode" / "qa.json")["success"] is True
    assert (tmp_path / "out" / "episode" / "entity_consistency.json").exists()
    assert (tmp_path / "out" / "episode" / "merge_decisions.json").exists()
    assert (tmp_path / "out" / "episode" / "transcript.corrected.txt").read_text(
        encoding="utf-8"
    ).strip() == "本壳"


def test_pipeline_records_backend_resolved_model_for_faster_whisper(tmp_path, monkeypatch):
    model_dir = tmp_path / "model" / "faster-whisper-large-v3-turbo"
    model_dir.mkdir(parents=True)
    for name in (
        "config.json",
        "model.bin",
        "preprocessor_config.json",
        "tokenizer.json",
        "vocabulary.json",
    ):
        (model_dir / name).write_bytes(b"model")
    monkeypatch.setattr("atot.models.MODEL_DIR", tmp_path / "model")
    monkeypatch.setattr("atot.models.LOCAL_MODELS_DIR", tmp_path / "model")

    seen_models: list[str] = []

    class FakeBackend:
        name = "faster-whisper"
        supports_prompt = True
        supports_word_timestamps = True
        supports_diarization = False

        def transcribe(self, audio_path: Path, options: ASRTranscribeOptions):
            seen_models.append(options.model)
            return {"text": "你好", "segments": [{"start": 0.0, "end": 1.0, "text": "你好"}]}

    def fake_prepare(_input_path, output_path, *, sample_rate, overwrite):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"prepared")
        return Path(output_path)

    def fake_materialize(_prepared_wav, chunks_dir, *, chunk_length, overlap, overwrite, duration):
        chunk = Path(chunks_dir) / "chunk_0000.wav"
        chunk.parent.mkdir(parents=True, exist_ok=True)
        chunk.write_bytes(b"chunk")
        return [
            ChunkSpec(
                index=0,
                path=chunk,
                source_start=0.0,
                source_end=1.0,
                core_start=0.0,
                core_end=1.0,
            )
        ]

    monkeypatch.setattr(
        pipeline_module,
        "build_backend",
        lambda name, *, recording_json=None, verbose=None: FakeBackend(),
    )
    monkeypatch.setattr(pipeline_module, "prepare_audio", fake_prepare)
    monkeypatch.setattr(
        pipeline_module,
        "prepare_audio_command",
        lambda input_path, output_path, *, sample_rate: {
            "tool": "ffmpeg",
            "available": True,
            "args": ["ffmpeg", "-i", str(input_path), "-ar", str(sample_rate), str(output_path)],
        },
    )
    monkeypatch.setattr(pipeline_module, "ffprobe_duration", lambda _path: 1.0)
    monkeypatch.setattr(pipeline_module, "materialize_chunks", fake_materialize)

    audio = tmp_path / "episode.wav"
    audio.write_bytes(b"audio")

    run = run_transcription(
        TranscribeOptions(
            input_path=audio,
            output_dir=tmp_path / "out",
            backend="faster-whisper",
            model="large-v3-turbo",
        )
    )
    chunk_payload = read_json(tmp_path / "out" / "episode" / "chunks" / "chunk_0000.json")

    assert seen_models == [str(model_dir)]
    assert run["model"] == str(model_dir)
    assert run["model_source"] == "local"
    assert run["model_alias_or_input"] == "large-v3-turbo"
    assert run["transcription_fingerprint"]["model"] == str(model_dir)
    assert chunk_payload["model"] == str(model_dir)


def test_payload_matches_fingerprint_requires_same_hash():
    options = TranscribeOptions(input_path=Path("episode.m4a"))
    fingerprint = _transcription_fingerprint(
        backend_name="mlx-whisper",
        model="mlx-community/whisper-large-v3-turbo",
        options=options,
        prompt=None,
    )
    payload = {"transcription_fingerprint_sha256": _sha256_json(fingerprint)}

    assert _payload_matches_fingerprint(payload, fingerprint)
    assert not _payload_matches_fingerprint({}, fingerprint)
    assert not _payload_matches_fingerprint({"transcription_fingerprint": fingerprint}, fingerprint)
    assert not _payload_matches_fingerprint(
        payload,
        _transcription_fingerprint(
            backend_name="mlx-whisper",
            model="mlx-community/whisper-large-v3-mlx",
            options=options,
            prompt=None,
        ),
    )


def test_payload_matches_chunk_requires_same_chunk_spec():
    expected = ChunkSpec(
        index=0,
        path=Path("chunks/chunk_0000.wav"),
        source_start=0.0,
        source_end=10.0,
        core_start=0.0,
        core_end=10.0,
    )
    payload = {"chunk": expected.to_json()}

    assert _payload_matches_chunk(payload, expected)
    assert not _payload_matches_chunk(
        {
            "chunk": ChunkSpec(
                index=0,
                path=Path("chunks/chunk_0000.wav"),
                source_start=0.0,
                source_end=12.0,
                core_start=0.0,
                core_end=12.0,
            ).to_json()
        },
        expected,
    )
    assert not _payload_matches_chunk({}, expected)
    assert not _payload_matches_chunk({"chunk": {"index": 0, "source_start": "bad"}}, expected)


def test_chunk_cache_decision_tracks_missing_matching_mismatch_and_force(tmp_path):
    options = TranscribeOptions(input_path=Path("episode.m4a"))
    spec = ChunkSpec(
        index=0,
        path=Path("chunks/chunk_0000.wav"),
        source_start=0.0,
        source_end=10.0,
        core_start=0.0,
        core_end=10.0,
    )
    fingerprint = _transcription_fingerprint(
        backend_name="mlx-whisper",
        model="mlx-community/whisper-large-v3-turbo",
        options=options,
        prompt=None,
    )
    json_path = tmp_path / "chunk_0000.json"

    assert _chunk_cache_decision(json_path, spec, fingerprint) == ASRChunkCacheDecision(
        payload={},
        status="missing_or_forced",
        should_transcribe=True,
    )

    payload = {
        "success": True,
        "transcription_fingerprint_sha256": _sha256_json(fingerprint),
        "chunk": spec.to_json(),
        "result": {"segments": []},
    }
    write_json_atomic(json_path, payload)

    matching = _chunk_cache_decision(json_path, spec, fingerprint)
    assert matching == ASRChunkCacheDecision(
        payload=payload, status="skipped_existing", should_transcribe=False
    )

    changed_spec = ChunkSpec(
        index=0,
        path=Path("chunks/chunk_0000.wav"),
        source_start=0.0,
        source_end=12.0,
        core_start=0.0,
        core_end=12.0,
    )
    assert _chunk_cache_decision(json_path, changed_spec, fingerprint) == ASRChunkCacheDecision(
        payload={},
        status="cache_mismatch",
        should_transcribe=True,
    )

    changed_fingerprint = _transcription_fingerprint(
        backend_name="mlx-whisper",
        model="mlx-community/whisper-large-v3-mlx",
        options=options,
        prompt=None,
    )
    assert _chunk_cache_decision(json_path, spec, changed_fingerprint) == ASRChunkCacheDecision(
        payload={},
        status="cache_mismatch",
        should_transcribe=True,
    )
    assert _chunk_cache_decision(
        json_path, spec, fingerprint, force_transcribe=True
    ) == ASRChunkCacheDecision(
        payload={},
        status="missing_or_forced",
        should_transcribe=True,
    )
