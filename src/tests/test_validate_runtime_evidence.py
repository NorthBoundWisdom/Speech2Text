from copy import deepcopy
from pathlib import Path
import wave

from atot.segments import segment_digest
from atot.utils import read_json, write_json_atomic, write_text_atomic
from scripts.validate_output_bundle import REQUIRED_FILES
from scripts.validate_runtime_evidence import RuntimeEvidenceOptions, validate_runtime_evidence


def _write_wav(path: Path, *, seconds: int = 1, rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * seconds * rate)


def _write_output_bundle(tmp_path: Path) -> Path:
    output = (tmp_path / "output").resolve()
    details = output
    fixture = read_json(Path("src/tests/fixtures/run.sample.json"))
    run = deepcopy(fixture)
    run["job_dir"] = str(output)
    run["audio_duration"] = 95.0 * 60.0
    run["output_files"] = {name: str(output / name) for name in sorted(REQUIRED_FILES)}
    run["cloud"] = {"prepared": True, "audio_uploaded": False, "outputs": []}

    segments = [{"start": 0.0, "end": 1.0, "text": "你好世界"}]
    write_json_atomic(details / "raw.json", {"segments": segments, "text": "你好世界"})
    write_json_atomic(details / "corrected.json", {"segments": segments, "text": "你好世界"})
    write_text_atomic(details / "transcript.raw.txt", "你好世界\n")
    write_text_atomic(details / "transcript.corrected.txt", "你好世界\n")
    write_text_atomic(output / "transcript.readable.md", "# Transcript\n\n你好世界\n")
    write_text_atomic(details / "transcript.md", "# Transcript\n\n你好世界\n")
    write_text_atomic(details / "transcript.timestamped.md", "[00:00:00] 你好世界\n")
    write_text_atomic(details / "transcript.srt", "1\n00:00:00,000 --> 00:00:01,000\n你好世界\n")
    write_text_atomic(
        details / "transcript.vtt", "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n你好世界\n"
    )
    write_json_atomic(details / "corrections.json", {"corrections": []})
    write_json_atomic(details / "chunks_manifest.json", {"chunks": []})
    write_json_atomic(details / "prepared.meta.json", {"schema_version": 1})
    _write_wav(details / "prepared.wav")
    write_json_atomic(details / "qa.json", {"success": True})
    write_text_atomic(details / "qa.md", "# QA\n\nPASS\n")
    write_json_atomic(details / "review.json", {"summary": {}})
    write_text_atomic(details / "review.md", "# Review\n")
    write_json_atomic(details / "glossary.effective.json", {})
    write_text_atomic(details / "run.log", "success=true\n")
    write_json_atomic(details / "run.json", run)
    return output


def _write_repair_artifacts(output: Path) -> None:
    repair = output / "repair"
    windows = repair / "windows"
    window = {"type": "rerun_window", "start": 0.0, "end": 5.0, "reasons": ["large_timing_gap"]}
    before_segment = {"start": 0.0, "end": 1.0, "text": "旧文本"}
    segment = {"start": 0.0, "end": 1.0, "text": "修复后的文本"}
    before_digest = segment_digest([before_segment])
    after_digest = segment_digest([segment])
    write_json_atomic(
        repair / "repair_plan.json", {"strategy": "bad-segments", "windows": [window]}
    )
    write_json_atomic(
        windows / "repair_0001.raw.json", {"window": window, "result": {"segments": [segment]}}
    )
    write_json_atomic(windows / "repair_0001.segments.json", {"segments": [segment]})
    write_json_atomic(
        windows / "repair_0001.corrected.json",
        {"window": window, "segments": [segment], "corrections": []},
    )
    _write_wav(windows / "repair_0001.wav")
    write_json_atomic(repair / "replacement_segments.json", {"segments": [segment]})
    write_json_atomic(
        repair / "pre_repair_snapshot_001.json",
        {
            "repair_id": 1,
            "segment_count": 1,
            "segment_digest": before_digest,
            "text_preview": "旧文本",
        },
    )
    write_json_atomic(
        repair / "post_repair_snapshot_001.json",
        {
            "repair_id": 1,
            "segment_count": 1,
            "segment_digest": after_digest,
            "text_preview": "修复后的文本",
        },
    )
    write_json_atomic(
        repair / "repair_run_001.json",
        {
            "success": True,
            "repair_id": 1,
            "strategy": "bad-segments",
            "windows": [window],
            "replacement_segment_count": 1,
            "pre_segment_digest": before_digest,
            "post_segment_digest": after_digest,
        },
    )
    write_json_atomic(
        repair / "repair_decision_001.json",
        {
            "success": True,
            "repair_id": 1,
            "status": "applied",
            "applied_window_count": 1,
            "rejected_window_count": 0,
            "window_decisions": [],
        },
    )
    write_text_atomic(repair / "diff_001.md", "### Before\n\n旧\n\n### After\n\n新\n")
    run = read_json(output / "run.json")
    run["repair"] = {"applied": True, "repair_run_ids": ["repair_run_001.json"]}
    write_json_atomic(output / "run.json", run)


def _write_cloud_artifacts(output: Path, *, with_api: bool = True) -> None:
    input_dir = output / "cloud" / "input"
    prompt_path = input_dir / "prompts" / "summarize.prompt.md"
    chunk_path = input_dir / "chunks" / "text_chunk_0001.md"
    files = {
        "transcript.for_cloud.md": "# Transcript\n\n你好世界\n",
        "segments.for_cloud.json": '{"segments":[{"start":0,"end":1,"text":"你好世界"}]}\n',
        "qa.for_cloud.json": '{"success":true}\n',
        "qa.for_cloud.md": "# QA\n\nPASS\n",
        "glossary.for_cloud.json": "{}\n",
        "run_summary.json": "{}\n",
    }
    for name, text in files.items():
        write_text_atomic(input_dir / name, text)
    write_text_atomic(prompt_path, "只基于文本总结\n")
    write_text_atomic(chunk_path, "# Text Chunk 0001\n\nRange: 00:00:00 -> 00:00:01\n")
    input_files = sorted(
        [*files, "manifest.json", "prompts/summarize.prompt.md", "chunks/text_chunk_0001.md"]
    )
    write_json_atomic(
        input_dir / "manifest.json",
        {
            "contains_audio": False,
            "contains_video": False,
            "input_files": input_files,
            "text_chunks": ["chunks/text_chunk_0001.md"],
            "prompt_templates": ["prompts/summarize.prompt.md"],
        },
    )

    cloud = output / "cloud"
    output_files = sorted(
        [
            "manifest.json",
            "summary.md",
            "chapters.json",
            "chapters.md",
            "shownotes.md",
            "title_candidates.json",
            "title_candidates.md",
            "social_copy.md",
            "terms.json",
            "terms.md",
            "uncertainty_report.md",
            "fact_or_term_uncertainties.md",
            "glossary_suggestions.json",
            "transcript.polish_suggestions.json",
        ]
    )
    for name in output_files:
        if name == "manifest.json":
            continue
        if not name.endswith(".json"):
            write_text_atomic(cloud / name, "# Cloud Output\n")
    write_json_atomic(
        cloud / "chapters.json",
        {
            "chapters": [
                {
                    "start": "00:00:00",
                    "end": "00:00:01",
                    "title": "开场",
                    "summary": "你好世界",
                    "source_chunks": ["chunks/text_chunk_0001.md"],
                    "source_segment_ids": ["segment_000001"],
                }
            ]
        },
    )
    write_json_atomic(
        cloud / "title_candidates.json", {"candidates": [{"title": "示例标题", "source": "test"}]}
    )
    write_json_atomic(
        cloud / "terms.json", {"terms": [{"term": "你好世界", "sources": ["test"], "count": 1}]}
    )
    write_json_atomic(
        cloud / "glossary_suggestions.json", {"suggestions": [], "needs_human_confirmation": []}
    )
    write_json_atomic(cloud / "transcript.polish_suggestions.json", {"patches": []})
    write_json_atomic(
        cloud / "manifest.json",
        {
            "contains_audio": False,
            "contains_video": False,
            "output_files": output_files,
        },
    )
    if with_api:
        write_json_atomic(
            cloud / "summarize.api_run.json",
            {
                "api_base": "https://example.test/v1",
                "model": "text-model",
                "request": {"input": "[redacted in audit]"},
                "response": {"output_text": "ok"},
            },
        )


def _write_gold_report(tmp_path: Path) -> Path:
    rows = []
    for sample in ("ai.wav", "coffee.wav", "casual.wav"):
        for condition in (False, True):
            rows.append(
                {
                    "sample": f"tests/gold/{sample}",
                    "job_dir": f"output/benchmark/{sample}-{condition}",
                    "model": "large-v3-turbo",
                    "model_input": "large-v3-turbo",
                    "condition_on_previous_text": condition,
                    "cer": 0.01,
                    "term_hit_rate": 1.0,
                    "qa_success": True,
                    "srt_pass": True,
                    "runtime_seconds": 1.0,
                    "peak_rss_mb": 100.0,
                }
            )
    path = tmp_path / "report.json"
    write_json_atomic(
        path,
        {
            "success": True,
            "gate_failures": [],
            "condition_on_previous_text_values": [False, True],
            "results": rows,
        },
    )
    return path


def test_validate_runtime_evidence_accepts_complete_evidence(tmp_path):
    output = _write_output_bundle(tmp_path)
    _write_repair_artifacts(output)
    _write_cloud_artifacts(output)
    gold_report = _write_gold_report(tmp_path)

    errors = validate_runtime_evidence(
        RuntimeEvidenceOptions(
            long_output=output,
            gold_report=gold_report,
            repair_output=output,
            cloud_output=output,
            require_cloud_api=True,
        )
    )

    assert errors == []


def test_validate_runtime_evidence_rejects_short_long_run(tmp_path):
    output = _write_output_bundle(tmp_path)
    run = read_json(output / "run.json")
    run["audio_duration"] = 60.0
    write_json_atomic(output / "run.json", run)

    errors = validate_runtime_evidence(RuntimeEvidenceOptions(long_output=output))

    assert any("below required" in error for error in errors)


def test_validate_runtime_evidence_rejects_gold_report_without_matrix(tmp_path):
    report = tmp_path / "report.json"
    write_json_atomic(
        report,
        {
            "success": True,
            "gate_failures": [],
            "condition_on_previous_text_values": [True],
            "results": [{"sample": "tests/gold/one.wav", "cer": 0.0}],
        },
    )

    errors = validate_runtime_evidence(RuntimeEvidenceOptions(gold_report=report))

    assert any("at least 3 distinct gold samples" in error for error in errors)
    assert any("must include both false and true" in error for error in errors)


def test_validate_runtime_evidence_requires_cloud_api_audit_when_requested(tmp_path):
    output = _write_output_bundle(tmp_path)
    _write_cloud_artifacts(output, with_api=False)

    errors = validate_runtime_evidence(
        RuntimeEvidenceOptions(cloud_output=output, require_cloud_api=True)
    )

    assert any("no cloud API audit files found" in error for error in errors)
