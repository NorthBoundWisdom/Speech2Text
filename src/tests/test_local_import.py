import hashlib
import json

import pytest

from atot.local_import import import_local_media


def test_import_local_media_copy_writes_metadata_and_fingerprint(tmp_path):
    source = tmp_path / "source clip.m4a"
    content = b"local-audio"
    source.write_bytes(content)

    result = import_local_media(
        source, mode="copy", process_dir=tmp_path / "process", group_name="Clips"
    )
    metadata = json.loads((result.episode_dir / "episode.json").read_text(encoding="utf-8"))

    assert result.mode == "copy"
    assert result.audio_path.exists()
    assert not result.audio_path.is_symlink()
    assert result.audio_path.read_bytes() == content
    assert metadata["source"] == "local"
    assert metadata["app_group"] == "Clips"
    assert metadata["app_status"] == "import"
    assert metadata["app_queue_status"] == "unread"
    assert metadata["import_mode"] == "copy"
    assert metadata["audio_path"] == str(result.audio_path)
    assert metadata["original_path"] == str(source.resolve())
    assert metadata["original_fingerprint"]["size_bytes"] == len(content)
    assert metadata["original_fingerprint"]["sha256"] == hashlib.sha256(content).hexdigest()


def test_import_local_media_reference_creates_symlink(tmp_path):
    source = tmp_path / "reference clip.wav"
    source.write_bytes(b"reference-audio")

    result = import_local_media(source, mode="reference", process_dir=tmp_path / "process")
    metadata = json.loads((result.episode_dir / "episode.json").read_text(encoding="utf-8"))

    assert result.mode == "reference"
    assert result.audio_path.is_symlink()
    assert result.audio_path.resolve() == source.resolve()
    assert metadata["import_mode"] == "reference"
    assert metadata["original_path"] == str(source.resolve())


def test_import_local_media_rejects_unknown_mode(tmp_path):
    source = tmp_path / "clip.m4a"
    source.write_bytes(b"audio")

    with pytest.raises(ValueError, match="mode must be copy or reference"):
        import_local_media(source, mode="move", process_dir=tmp_path / "process")
