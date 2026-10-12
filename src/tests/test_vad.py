from atot import vad as vad_module
from atot.vad import (
    Silence,
    assess_silence_points,
    build_smart_chunks,
    choose_chunk_boundaries,
    choose_dynamic_silence_threshold,
    detect_silences_for_chunking,
)


def test_choose_chunk_boundaries_prefers_nearby_silence_before_max():
    boundaries = choose_chunk_boundaries(
        3600.0,
        target_chunk_length=1200.0,
        max_chunk_length=1500.0,
        silences=[Silence(1198.0, 1202.0), Silence(2500.0, 2502.0)],
    )

    assert boundaries == [0.0, 1200.0, 2501.0, 3600.0]


def test_build_smart_chunks_adds_overlap_context():
    chunks = build_smart_chunks(
        100.0,
        chunks_dir="chunks",
        target_chunk_length=40.0,
        max_chunk_length=50.0,
        overlap=5.0,
        silences=[Silence(38.0, 42.0)],
    )

    assert len(chunks) == 3
    assert chunks[0].core_start == 0.0
    assert chunks[0].core_end == 40.0
    assert chunks[1].source_start == 35.0
    assert chunks[1].core_start == 40.0


def test_choose_dynamic_silence_threshold_uses_loudness_distribution(monkeypatch):
    monkeypatch.setattr(
        vad_module, "sample_wav_rms_dbfs", lambda _path: [-56.0, -54.0, -52.0, -24.0, -22.0]
    )

    plan = choose_dynamic_silence_threshold("episode.wav")

    assert plan["source"] == "dynamic_rms"
    assert -45.0 <= plan["threshold"] <= -25.0


def test_detect_silences_for_chunking_falls_back_when_dynamic_is_too_sparse(monkeypatch):
    monkeypatch.setattr(
        vad_module,
        "choose_dynamic_silence_threshold",
        lambda _path: {"threshold": -42.0, "source": "dynamic_rms"},
    )
    calls = []

    def fake_detect(_path, *, silence_threshold, min_silence):
        calls.append((silence_threshold, min_silence))
        if silence_threshold == -42.0:
            return []
        return [Silence(60.0, 61.0)]

    monkeypatch.setattr(vad_module, "detect_silences_ffmpeg", fake_detect)

    silences, metadata = detect_silences_for_chunking(
        "episode.wav", duration=180.0, min_silence=0.5
    )

    assert silences == [Silence(60.0, 61.0)]
    assert calls == [(-42.0, 0.5), (-30.0, 0.5)]
    assert metadata["source"] == "fallback_default"
    assert metadata["fallback_reason"]["status"] == "too_sparse"


def test_assess_silence_points_flags_dense_or_sparse_layouts():
    assert assess_silence_points([], duration=3600.0)["status"] == "too_sparse"
    dense = [Silence(float(index), float(index) + 0.8) for index in range(1000)]

    assert assess_silence_points(dense, duration=3600.0)["status"] == "too_dense"
