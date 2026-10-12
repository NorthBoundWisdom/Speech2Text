from __future__ import annotations

from pathlib import Path

from atot.output_audit import OutputAuditOptions, audit_markdown, audit_outputs
from atot.utils import write_json_atomic


def _write_run_bundle(
    root: Path, batch: str, episode: str, *, qa_status: str, empty_segments: int
) -> None:
    job_dir = root / batch / episode
    details = job_dir
    write_json_atomic(
        details / "run.json",
        {
            "success": True,
            "created_at": "2026-05-31T00:00:00+08:00",
            "job_dir": str(job_dir),
            "backend": "mlx-whisper",
            "model_alias_or_input": "large-v3-turbo",
            "runtime_seconds": 12.5,
            "audio_duration": 120.0,
            "speed_factor": 9.6,
            "peak_rss_mb": 2048.0,
            "review": {"issue_count": 1, "segment_issue_count": 2},
            "qa": {
                "status": qa_status,
                "issue_count": 4,
                "blocking_issue_count": 3 if qa_status != "pass" else 0,
                "warning_count": 1,
            },
            "quality_metrics": {
                "corrected_char_count": 1000,
                "correction_count": 5,
                "empty_corrected_segment_count": empty_segments,
                "max_repeated_token_run": 7,
                "top_token_ratio": 0.12,
            },
        },
    )
    write_json_atomic(
        details / "qa.json",
        {
            "success": qa_status == "pass",
            "summary": {
                "issue_count": 4,
                "blocking_issue_count": 3 if qa_status != "pass" else 0,
                "warning_count": 1,
            },
            "issues": [
                {"type": "empty_segment_text", "severity": "blocker"},
                {"type": "repeated_phrase", "severity": "warning"},
            ],
        },
    )
    write_json_atomic(
        details / "review.json",
        {
            "summary": {"issue_count": 1, "segment_issue_count": 2},
            "issues": [{"type": "possible_glossary_near_miss", "severity": "medium"}],
        },
    )


def test_audit_outputs_summarizes_runs_and_writes_report(tmp_path: Path) -> None:
    output_root = tmp_path / "output"
    _write_run_bundle(output_root, "0527", "episode-a", qa_status="fail", empty_segments=12)
    _write_run_bundle(output_root, "0528", "episode-b", qa_status="pass", empty_segments=0)
    report_path = tmp_path / "audit.md"

    audit = audit_outputs(
        OutputAuditOptions(output_root=output_root, output_path=report_path, limit=5)
    )

    assert audit["summary"]["run_count"] == 2
    assert audit["summary"]["qa_fail_count"] == 1
    assert audit["summary"]["empty_segment_run_count"] == 1
    assert audit["summary"]["top_qa_issue_types"][0]["type"] == "empty_segment_text"
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "# Output Library Audit" in report
    assert "`0527/episode-a`" in report


def test_audit_markdown_renders_review_and_qa_counts(tmp_path: Path) -> None:
    output_root = tmp_path / "output"
    _write_run_bundle(output_root, "0527", "episode-a", qa_status="fail", empty_segments=2)

    audit = audit_outputs(OutputAuditOptions(output_root=output_root))
    markdown = audit_markdown(audit["rows"], audit["summary"], limit=10)

    assert "## Top QA Issues" in markdown
    assert "## Top Review Issues" in markdown
    assert "| Output | Model | QA |" in markdown
    assert "large-v3-turbo" in markdown
