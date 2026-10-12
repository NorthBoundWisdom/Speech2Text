from atot.gold import (
    GoldBenchmarkOptions,
    character_error_rate,
    gold_report_to_markdown,
    run_gold_benchmark,
)
from atot.utils import write_json_atomic, write_text_atomic


def test_character_error_rate():
    assert character_error_rate("你好世界", "你好") == 1.0
    assert character_error_rate("你好", "你好") == 0.0
    assert character_error_rate("anything", "") is None


def test_run_gold_benchmark_writes_report(tmp_path):
    sample = tmp_path / "sample.wav"
    sample.write_bytes(b"not-real-audio")
    write_text_atomic(tmp_path / "sample.ref.txt", "你好世界")
    write_json_atomic(tmp_path / "sample.terms.json", {"terms": ["世界"]})

    def fake_transcriber(options):
        job_dir = options.output_dir / options.name
        details = job_dir
        segments = [{"start": 0.0, "end": 1.0, "text": "你好世界"}]
        write_json_atomic(details / "raw.json", {"segments": segments})
        write_json_atomic(details / "corrected.json", {"segments": segments, "text": "你好世界"})
        write_json_atomic(details / "review.json", {"summary": {"segment_issue_count": 0}})
        write_json_atomic(details / "chunks_manifest.json", {"chunk_layout_sha256": "abc"})
        write_text_atomic(job_dir / "transcript.corrected.txt", "你好世界")
        write_text_atomic(
            job_dir / "transcript.srt", "1\n00:00:00,000 --> 00:00:01,000\n你好世界\n"
        )
        return {
            "job_dir": str(job_dir),
            "model_alias_or_input": options.model,
            "runtime_seconds": 1.0,
            "peak_rss_mb": 123.4,
            "output_files": {"transcript.corrected.txt": str(job_dir / "transcript.corrected.txt")},
        }

    report = run_gold_benchmark(
        GoldBenchmarkOptions(samples=(sample,), output_dir=tmp_path / "bench", model="tiny"),
        transcriber=fake_transcriber,
    )

    assert report["results"][0]["cer"] == 0.0
    assert report["results"][0]["term_hit_rate"] == 1.0
    assert report["results"][0]["qa_success"] is True
    assert report["results"][0]["srt_pass"] is True
    assert report["results"][0]["peak_rss_mb"] == 123.4


def test_run_gold_benchmark_supports_model_and_condition_matrix(tmp_path):
    sample = tmp_path / "sample.wav"
    sample.write_bytes(b"not-real-audio")
    write_text_atomic(tmp_path / "sample.ref.txt", "你好世界")
    seen = []

    def fake_transcriber(options):
        seen.append((options.model, options.condition_on_previous_text, options.name))
        job_dir = options.output_dir / options.name
        details = job_dir
        segments = [{"start": 0.0, "end": 1.0, "text": "你好世界"}]
        write_json_atomic(details / "raw.json", {"segments": segments})
        write_json_atomic(details / "corrected.json", {"segments": segments, "text": "你好世界"})
        write_json_atomic(details / "review.json", {"summary": {"segment_issue_count": 0}})
        write_json_atomic(details / "chunks_manifest.json", {"chunk_layout_sha256": "abc"})
        write_text_atomic(job_dir / "transcript.corrected.txt", "你好世界")
        write_text_atomic(
            job_dir / "transcript.srt", "1\n00:00:00,000 --> 00:00:01,000\n你好世界\n"
        )
        return {
            "job_dir": str(job_dir),
            "model_alias_or_input": options.model,
            "runtime_seconds": 1.0,
            "peak_rss_mb": 123.4,
            "output_files": {"transcript.corrected.txt": str(job_dir / "transcript.corrected.txt")},
        }

    report = run_gold_benchmark(
        GoldBenchmarkOptions(
            samples=(sample,),
            output_dir=tmp_path / "bench",
            models=("large-v3-turbo", "large-v3-4bit"),
            condition_on_previous_text_values=(True, False),
        ),
        transcriber=fake_transcriber,
    )

    assert len(report["results"]) == 4
    assert seen == [
        ("large-v3-turbo", True, "sample__large-v3-turbo__prev-on"),
        ("large-v3-turbo", False, "sample__large-v3-turbo__prev-off"),
        ("large-v3-4bit", True, "sample__large-v3-4bit__prev-on"),
        ("large-v3-4bit", False, "sample__large-v3-4bit__prev-off"),
    ]
    markdown = gold_report_to_markdown(report)
    assert "## Matrix Summary" in markdown
    assert (
        "| large-v3-turbo | on | 1 | 0.0 | n/a | 1/1 | 1/1 | 0 | 0 | 0 | 123.40 | 1.00s |"
        in markdown
    )


def test_gold_benchmark_acceptance_gate_reports_failures(tmp_path):
    sample = tmp_path / "sample.wav"
    sample.write_bytes(b"not-real-audio")
    write_text_atomic(tmp_path / "sample.ref.txt", "你好世界")
    write_json_atomic(tmp_path / "sample.terms.json", {"terms": ["世界"]})

    def fake_transcriber(options):
        job_dir = options.output_dir / options.name
        details = job_dir
        segments = [{"start": 0.0, "end": 1.0, "text": "你好"}]
        write_json_atomic(details / "raw.json", {"segments": segments})
        write_json_atomic(details / "corrected.json", {"segments": segments, "text": "你好"})
        write_json_atomic(details / "review.json", {"summary": {"segment_issue_count": 0}})
        write_json_atomic(details / "chunks_manifest.json", {"chunk_layout_sha256": "abc"})
        write_text_atomic(job_dir / "transcript.corrected.txt", "你好")
        write_text_atomic(job_dir / "transcript.srt", "1\n00:00:00,000 --> 00:00:01,000\n你好\n")
        return {
            "job_dir": str(job_dir),
            "model_alias_or_input": options.model,
            "runtime_seconds": 1.0,
        }

    report = run_gold_benchmark(
        GoldBenchmarkOptions(
            samples=(sample,),
            output_dir=tmp_path / "bench",
            model="tiny",
            max_cer=0.1,
            min_term_hit_rate=1.0,
            require_qa_pass=True,
            require_srt_pass=True,
        ),
        transcriber=fake_transcriber,
    )

    assert report["success"] is False
    assert {failure["metric"] for failure in report["gate_failures"]} == {
        "max_cer",
        "min_term_hit_rate",
    }
    markdown = gold_report_to_markdown(report)
    assert "## Acceptance Gate" in markdown
    assert "Status: FAIL" in markdown
