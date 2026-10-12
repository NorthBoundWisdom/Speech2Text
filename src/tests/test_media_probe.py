from pathlib import Path

from atot.audio import normalize_media_probe


def test_normalize_media_probe_records_audio_and_video_streams():
    payload = {
        "format": {"format_name": "mov,mp4", "duration": "10.0"},
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
            },
        ],
    }

    result = normalize_media_probe(payload, path=Path("video.mp4"))

    assert result["container"] == "mov,mp4"
    assert result["selected_audio_stream"] == 1
    assert result["audio_codec"] == "aac"
    assert result["sample_rate"] == "48000"
    assert result["channels"] == 2
    assert result["video_streams"][0]["codec"] == "h264"
