from atot.cleanup import CleanupOptions, cleanup_output
from atot.utils import read_json


def test_cleanup_compact_removes_rebuildable_audio_intermediates(tmp_path):
    output = tmp_path / "output"
    prepared = output / "prepared.wav"
    chunk_wav = output / "chunks" / "chunk_0000.wav"
    chunk_json = output / "chunks" / "chunk_0000.json"
    transcript = output / "transcript.readable.md"
    for path in (prepared, chunk_wav, chunk_json, transcript):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 3)

    result = cleanup_output(CleanupOptions(output_dir=output, profile="compact"))

    assert result["deleted_count"] == 2
    assert not prepared.exists()
    assert not chunk_wav.exists()
    assert chunk_json.exists()
    assert transcript.exists()
    assert read_json(output / "cleanup.last.json")["profile"] == "compact"


def test_cleanup_dry_run_keeps_files(tmp_path):
    output = tmp_path / "output"
    prepared = output / "prepared.wav"
    prepared.parent.mkdir(parents=True)
    prepared.write_bytes(b"x")

    result = cleanup_output(CleanupOptions(output_dir=output, profile="compact", dry_run=True))

    assert result["candidate_count"] == 1
    assert result["deleted_count"] == 0
    assert prepared.exists()
