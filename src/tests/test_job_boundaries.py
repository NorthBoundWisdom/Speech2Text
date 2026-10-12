from pathlib import Path

from atot.job import build_job_layout, resolve_job_dir
from atot.paths import DEFAULT_OUTPUT_DIR, PROCESS_DIR


def test_job_dir_for_process_audio_uses_data_output_root():
    input_path = PROCESS_DIR / "0527" / "topic" / "episode.m4a"

    assert (
        resolve_job_dir(input_path, DEFAULT_OUTPUT_DIR, None)
        == DEFAULT_OUTPUT_DIR / "0527" / "topic"
    )


def test_job_dir_for_external_audio_uses_fallback_output():
    input_path = Path("/tmp/audio files/test episode.m4a")

    assert resolve_job_dir(input_path, Path("output"), None) == Path("output") / "test-episode"


def test_job_layout_for_external_audio_has_stable_subpaths(tmp_path):
    input_path = tmp_path / "test episode.m4a"
    layout = build_job_layout(input_path, tmp_path / "out", None)

    assert layout.job_dir == tmp_path / "out" / "test-episode"
    assert layout.details_dir == layout.job_dir
    assert layout.chunks_dir == layout.job_dir / "chunks"
    assert layout.prepared_wav == layout.job_dir / "prepared.wav"
