from pathlib import Path

import pytest

from atot.audio import AudioError, compute_chunks, ffprobe_duration, prepare_audio


def test_compute_chunks_with_overlap():
    chunks = compute_chunks(95 * 60, chunks_dir=Path("chunks"), chunk_length=20 * 60, overlap=10)
    assert chunks[0].source_start == 0
    assert chunks[0].core_start == 0
    assert chunks[0].core_end == 1200
    assert chunks[1].source_start == 1190
    assert chunks[1].core_start == 1200
    assert chunks[-1].core_end == 95 * 60


def test_ffprobe_duration_surfaces_command_failure(monkeypatch, tmp_path):
    from atot import audio as audio_module

    class Completed:
        returncode = 1
        stdout = ""
        stderr = "invalid data"

    source = tmp_path / "episode.m4a"
    source.write_bytes(b"media")
    monkeypatch.setattr(audio_module, "optional_command", lambda name: "/bin/ffprobe")
    monkeypatch.setattr(audio_module, "run_command", lambda *args, **kwargs: Completed())

    with pytest.raises(AudioError, match="ffprobe"):
        ffprobe_duration(source)


def test_prepare_audio_rejects_directory_output(tmp_path):
    source = tmp_path / "episode.wav"
    source.write_bytes(b"media")
    output_dir = tmp_path / "prepared.wav"
    output_dir.mkdir()

    with pytest.raises(AudioError, match="directory"):
        prepare_audio(source, output_dir, overwrite=True)
