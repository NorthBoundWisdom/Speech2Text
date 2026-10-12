from pathlib import Path

from atot.audio import AudioError, ChunkSpec
from atot.context import build_prompt_context, write_context_files
from atot.pipeline import TranscribeOptions
from atot.pipeline.chunks import (
    _chunk_layout_fingerprint,
    _chunk_layout_matches,
    _resolve_chunking_plan,
    plan_and_materialize_chunks,
)
from atot.pipeline.identity import (
    _postprocess_fingerprint,
    _sha256_json,
    _transcription_fingerprint,
)
from atot.pipeline.runinfo import (
    _chunk_runtime_seconds,
    _chunk_status_counts,
    build_initial_run_info,
)
from atot.utils import read_json, write_json_atomic


def test_chunk_layout_manifest_requires_same_layout(tmp_path):
    options = TranscribeOptions(
        input_path=Path("episode.m4a"), chunk_length=10, overlap=1, sample_rate=16_000
    )
    chunks = [
        ChunkSpec(
            index=0,
            path=Path("chunks/chunk_0000.wav"),
            source_start=0.0,
            source_end=11.0,
            core_start=0.0,
            core_end=10.0,
        )
    ]
    layout = _chunk_layout_fingerprint(options=options, audio_duration=20.0, chunk_specs=chunks)
    manifest = tmp_path / "chunks_manifest.json"

    assert not _chunk_layout_matches(manifest, layout)

    manifest.write_text(f'{{"chunk_layout_sha256": "{_sha256_json(layout)}"}}', encoding="utf-8")
    assert _chunk_layout_matches(manifest, layout)
    write_json_atomic(manifest, {"chunk_layout": layout})
    assert not _chunk_layout_matches(manifest, layout)

    changed = _chunk_layout_fingerprint(
        options=TranscribeOptions(
            input_path=Path("episode.m4a"), chunk_length=12, overlap=1, sample_rate=16_000
        ),
        audio_duration=20.0,
        chunk_specs=chunks,
    )
    assert not _chunk_layout_matches(manifest, changed)


def test_auto_chunking_uses_fixed_for_short_audio_and_smart_for_long_audio():
    short = _resolve_chunking_plan(
        TranscribeOptions(input_path=Path("episode.m4a"), chunk_length=20 * 60),
        audio_duration=10 * 60,
    )
    long = _resolve_chunking_plan(
        TranscribeOptions(input_path=Path("episode.m4a"), chunk_length=20 * 60),
        audio_duration=60 * 60,
    )

    assert short["chunking"] == "fixed"
    assert short["fallback_reason"] == "short_audio_auto_fixed"
    assert long["chunking"] == "smart"
    assert long["chunk_length"] == 15 * 60
    assert long["max_chunk_length"] == 20 * 60


def test_plan_and_materialize_chunks_falls_back_to_fixed_when_auto_smart_detection_fails(tmp_path):
    options = TranscribeOptions(
        input_path=Path("episode.m4a"),
        chunking="auto",
        chunk_length=20 * 60,
        overlap=5,
    )
    prepared_wav = tmp_path / "prepared.wav"
    prepared_wav.write_bytes(b"prepared")
    chunks_dir = tmp_path / "chunks"
    planned_chunk = ChunkSpec(
        index=0,
        path=chunks_dir / "planned_0000.wav",
        source_start=0.0,
        source_end=20 * 60,
        core_start=0.0,
        core_end=20 * 60,
    )
    materialized_chunk = ChunkSpec(
        index=0,
        path=chunks_dir / "chunk_0000.wav",
        source_start=0.0,
        source_end=20 * 60,
        core_start=0.0,
        core_end=20 * 60,
    )

    def fail_detection(*_args, **_kwargs):
        raise AudioError("silence detector failed")

    def build_smart(*_args, **_kwargs):
        raise AssertionError("smart chunks should not be built after auto fallback")

    def compute_fixed(duration, *, chunks_dir, chunk_length, overlap):
        assert duration == 60 * 60
        assert chunk_length == options.chunk_length
        assert overlap == options.overlap
        assert chunks_dir == tmp_path / "chunks"
        return [planned_chunk]

    def materialize_fixed(prepared, chunks, *, chunk_length, overlap, overwrite, duration):
        assert prepared == prepared_wav
        assert chunks == tmp_path / "chunks"
        assert chunk_length == options.chunk_length
        assert overlap == options.overlap
        assert overwrite is True
        assert duration == 60 * 60
        return [materialized_chunk]

    result = plan_and_materialize_chunks(
        options=options,
        prepared_wav=prepared_wav,
        chunks_dir=chunks_dir,
        chunk_manifest_path=tmp_path / "chunks_manifest.json",
        audio_duration=60 * 60,
        force_prepare=False,
        detect_silences=fail_detection,
        build_smart=build_smart,
        compute_fixed=compute_fixed,
        materialize_fixed=materialize_fixed,
    )

    assert result.chunking_plan["chunking"] == "fixed"
    assert result.chunking_plan["fallback_reason"] == "smart_silence_detection_failed"
    assert result.silence_detection == {"error": "smart_silence_detection_failed"}
    assert result.planned_chunk_specs == [planned_chunk]
    assert result.chunk_specs == [materialized_chunk]
    assert result.chunk_layout["chunking"] == "fixed"
    assert result.chunk_layout["fallback_reason"] == "smart_silence_detection_failed"
    assert result.effective_chunk_length == options.chunk_length
    assert result.effective_max_chunk_length == options.chunk_length
    assert result.rewrite_chunks is True
    manifest = read_json(tmp_path / "chunks_manifest.json")
    assert manifest["chunk_layout_sha256"] == _sha256_json(result.chunk_layout)


def test_run_info_helpers_summarize_chunk_status_and_runtime():
    chunk_status = [
        {"status": "transcribed"},
        {"status": "transcribed_after_cache_mismatch"},
        {"status": "skipped_existing"},
        {"status": "skipped_existing"},
        {"status": "started"},
    ]
    chunk_payloads = [
        {"runtime_seconds": 1.25},
        {"runtime_seconds": "not numeric"},
        {"runtime_seconds": 0.75},
        {},
    ]

    assert _chunk_status_counts(chunk_status) == {
        "transcribed": 1,
        "transcribed_after_cache_mismatch": 1,
        "skipped_existing": 2,
    }
    assert _chunk_runtime_seconds(chunk_payloads) == 2.0


def test_build_initial_run_info_collects_context_chunk_and_fingerprint_metadata(tmp_path):
    audio = tmp_path / "episode.wav"
    audio.write_bytes(b"audio")
    (tmp_path / "主题.md").write_text("本期讨论 ChatGPT 和 AGI。", encoding="utf-8")
    context = build_prompt_context(
        audio, prompt_file=None, glossary_file=None, rule_packs=("tech_ai_zh",)
    )
    job_dir = tmp_path / "output"
    context_files = write_context_files(job_dir, context, glossary_file=None)
    options = TranscribeOptions(
        input_path=audio,
        chunking="fixed",
        chunk_length=60,
        max_chunk_length=60,
        overlap=5,
        rule_packs=("tech_ai_zh",),
    )
    chunk_layout = {
        "version": 2,
        "chunking": "fixed",
        "silence_threshold": None,
        "chunks": [],
    }
    transcription_fingerprint = _transcription_fingerprint(
        backend_name="mlx-whisper",
        model="mlx-community/whisper-large-v3-turbo",
        options=options,
        prompt=context.effective_prompt,
        chunk_layout_sha256=_sha256_json(chunk_layout),
    )
    postprocess_fingerprint = _postprocess_fingerprint(
        context.glossary, rule_packs=context.rule_pack_request
    )
    chunk_status = [
        {
            "index": 0,
            "status": "transcribed",
            "wav": "chunks/chunk_0000.wav",
            "json": "chunks/chunk_0000.json",
        }
    ]
    chunk_payloads = [{"runtime_seconds": 1.5}]

    run = build_initial_run_info(
        input_path=audio,
        input_file={"sha256": "a" * 64, "size": 5},
        media_probe={"available": True},
        prepared_audio={"sha256": "b" * 64, "sample_rate": 16_000},
        job_dir=job_dir,
        backend_name="mlx-whisper",
        backend_capabilities={"supports_prompt": True},
        options=options,
        context=context,
        context_files=context_files,
        review={"summary": {"rule_packs": ["tech_ai_zh"], "issue_count": 0}},
        quality_metrics={"score": 1.0},
        transcription_fingerprint=transcription_fingerprint,
        transcription_fingerprint_sha256=_sha256_json(transcription_fingerprint),
        postprocess_fingerprint=postprocess_fingerprint,
        postprocess_fingerprint_sha256=_sha256_json(postprocess_fingerprint),
        chunk_layout=chunk_layout,
        model_repo="mlx-community/whisper-large-v3-turbo",
        audio_duration=120.0,
        chunking_plan={"chunking": "fixed"},
        effective_chunk_length=60.0,
        effective_max_chunk_length=60.0,
        silence_detection=None,
        runtime_seconds=3.0,
        chunk_payloads=chunk_payloads,
        chunk_status=chunk_status,
    )

    assert run["schema_version"] == 2
    assert run["chunk_layout_sha256"] == _sha256_json(chunk_layout)
    assert run["chunk_status_counts"] == {
        "transcribed": 1,
        "transcribed_after_cache_mismatch": 0,
        "skipped_existing": 0,
    }
    assert run["chunk_runtime_seconds"] == 1.5
    assert run["speed_factor"] == 40.0
    assert run["chunks"] == chunk_status
    assert run["prompt"] == context.effective_prompt
    assert run["topic_prompt_summary_file"] == str(context_files.topic_prompt_summary_file)
    assert run["rule_pack_request"] == ["tech_ai_zh"]
    assert run["review"] == {"rule_packs": ["tech_ai_zh"], "issue_count": 0}
    assert run["quality_metrics"] == {"score": 1.0}
    assert run["qa"]["status"] == "fail"
