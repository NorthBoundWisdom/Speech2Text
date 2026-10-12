from atot.postprocess import PostprocessOptions, run_postprocess
from atot.utils import read_json, write_json_atomic, write_text_atomic


def test_run_postprocess_rewrites_corrected_outputs_without_chunk_json(tmp_path):
    output = tmp_path / "output"
    details = output
    glossary = tmp_path / "glossary.json"
    write_json_atomic(glossary, {"common_corrections": {"本课": "本科"}})
    write_json_atomic(
        details / "raw.json",
        {
            "input_path": str(tmp_path / "episode.m4a"),
            "model": "large-v3-turbo",
            "language": "zh",
            "audio_duration": 1.0,
            "chunks": [{"index": 0, "core_start": 0.0, "core_end": 1.0}],
            "segments": [{"start": 0.0, "end": 1.0, "text": "我是本课,你好"}],
            "text": "我是本课,你好",
        },
    )
    write_json_atomic(
        details / "run.json", {"success": True, "job_dir": str(output), "input_path": "episode.m4a"}
    )
    write_text_atomic(output / "transcript.srt", "1\n00:00:00,000 --> 00:00:01,000\n旧文本\n")

    run = run_postprocess(PostprocessOptions(output_dir=output, glossary_file=glossary))

    assert "我是本科，你好" in (details / "transcript.corrected.txt").read_text(encoding="utf-8")
    assert (output / "transcript.readable.md").exists()
    assert (details / "transcript.timestamped.md").exists()
    assert read_json(details / "qa.json")["success"] is True
    assert run["postprocess_fingerprint_sha256"]
