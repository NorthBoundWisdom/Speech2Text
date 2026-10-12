from __future__ import annotations

from pathlib import Path
from typing import Any

from atot.context import PromptContext
from atot.corrections import apply_corrections_to_segments
from atot.formats import (
    dedupe_segments,
    enforce_monotonic_timeline,
    normalize_segments,
    segments_to_txt,
)
from atot.quality import build_quality_metrics
from atot.review import build_review, review_to_markdown
from atot.numeric import as_float, as_int
from atot.utils import read_text, write_json_atomic, write_text_atomic

from .metrics import (
    MAX_ABSOLUTE_TOP_TOKEN_RATIO,
    MAX_CANDIDATE_CHAR_RATIO,
    MAX_RELATIVE_TOP_TOKEN_RATIO_MULTIPLIER,
    MIN_CANDIDATE_CHAR_RATIO,
    format_float,
    guardrail_failures,
    summary_metrics,
)


def write_candidate_outputs(
    *,
    audio: Path,
    candidate_name: str,
    candidate_text: str,
    candidate_segments: list[dict[str, Any]],
    output_dir: Path,
    command: list[str],
    runtime_seconds: float,
    peak_rss_mb: float | None,
    returncode: int,
    timed_out: bool,
    stdout: str,
    stderr: str,
    context: PromptContext,
) -> dict[str, Any]:
    raw_segments = candidate_segments or [
        {"start": 0.0, "end": 0.01, "text": candidate_text, "_timing_source": "text_fallback"}
    ]
    raw_segments = enforce_monotonic_timeline(dedupe_segments(normalize_segments(raw_segments)))
    corrected_segments, corrections = apply_corrections_to_segments(raw_segments, context.glossary)
    corrected_segments = enforce_monotonic_timeline(
        dedupe_segments(normalize_segments(corrected_segments))
    )
    review = build_review(corrected_segments, context.glossary)
    quality_metrics = build_quality_metrics(
        raw_segments=raw_segments,
        corrected_segments=corrected_segments,
        corrections=corrections,
        review=review,
    )
    files = {
        "raw": output_dir / "candidate.raw.txt",
        "raw_segments": output_dir / "candidate.raw.segments.json",
        "corrected": output_dir / "candidate.corrected.txt",
        "corrected_segments": output_dir / "candidate.corrected.segments.json",
        "review": output_dir / "candidate.review.md",
        "run": output_dir / "candidate.run.json",
        "stdout": output_dir / "candidate.stdout.txt",
        "stderr": output_dir / "candidate.stderr.txt",
    }
    write_text_atomic(files["raw"], candidate_text)
    write_json_atomic(files["raw_segments"], raw_segments)
    write_text_atomic(files["corrected"], segments_to_txt(corrected_segments))
    write_json_atomic(files["corrected_segments"], corrected_segments)
    write_text_atomic(files["review"], review_to_markdown(review))
    write_text_atomic(files["stdout"], stdout)
    write_text_atomic(files["stderr"], stderr)
    run = {
        "success": returncode == 0 and not timed_out,
        "candidate": candidate_name,
        "audio": str(audio),
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "runtime_seconds": runtime_seconds,
        "peak_rss_mb": peak_rss_mb,
        "review": review.get("summary", {}),
        "quality_metrics": quality_metrics,
        "output_files": {key: str(path) for key, path in files.items()},
    }
    write_json_atomic(files["run"], run)
    return run


def refresh_candidate_outputs(
    *,
    output_dir: Path,
    existing_run: dict[str, Any],
    raw_segments: list[dict[str, Any]],
    context: PromptContext,
) -> dict[str, Any]:
    audio = Path(str(existing_run.get("audio") or "audio"))
    candidate_name = str(existing_run.get("candidate") or output_dir.name)
    output_files = (
        existing_run.get("output_files", {})
        if isinstance(existing_run.get("output_files"), dict)
        else {}
    )
    stdout = read_text(_output_file_path(output_files, "stdout", output_dir)) or ""
    stderr = read_text(_output_file_path(output_files, "stderr", output_dir)) or ""
    candidate_text = read_text(_output_file_path(output_files, "raw", output_dir)) or "".join(
        str(segment.get("text", "")) for segment in raw_segments
    )
    return write_candidate_outputs(
        audio=audio,
        candidate_name=candidate_name,
        candidate_text=candidate_text,
        candidate_segments=raw_segments,
        output_dir=output_dir,
        command=[str(item) for item in existing_run.get("command", [])]
        if isinstance(existing_run.get("command"), list)
        else [],
        runtime_seconds=as_float(existing_run.get("runtime_seconds")) or 0.0,
        peak_rss_mb=as_float(existing_run.get("peak_rss_mb")),
        returncode=as_int(existing_run.get("returncode")) or 0,
        timed_out=bool(existing_run.get("timed_out", False)),
        stdout=stdout,
        stderr=stderr,
        context=context,
    )


def _output_file_path(output_files: dict[str, Any], key: str, output_dir: Path) -> Path | None:
    raw_path = output_files.get(key)
    if not raw_path:
        return None
    path = Path(str(raw_path))
    return path if path.is_absolute() else output_dir / path


def comparison_markdown(
    *,
    audio: Path,
    baseline_run: dict[str, Any],
    candidate_run: dict[str, Any],
) -> str:
    baseline_review = (
        baseline_run.get("review", {}) if isinstance(baseline_run.get("review"), dict) else {}
    )
    baseline_quality = (
        baseline_run.get("quality_metrics", {})
        if isinstance(baseline_run.get("quality_metrics"), dict)
        else {}
    )
    candidate_review = (
        candidate_run.get("review", {}) if isinstance(candidate_run.get("review"), dict) else {}
    )
    candidate_quality = (
        candidate_run.get("quality_metrics", {})
        if isinstance(candidate_run.get("quality_metrics"), dict)
        else {}
    )
    baseline_timing = (
        baseline_quality.get("timing", {})
        if isinstance(baseline_quality.get("timing"), dict)
        else {}
    )
    candidate_timing = (
        candidate_quality.get("timing", {})
        if isinstance(candidate_quality.get("timing"), dict)
        else {}
    )
    baseline_chars = int(baseline_quality.get("corrected_char_count", 0) or 0)
    candidate_chars = int(candidate_quality.get("corrected_char_count", 0) or 0)
    candidate_char_ratio = candidate_chars / baseline_chars if baseline_chars > 0 else 0.0
    baseline_top_token_ratio = float(baseline_quality.get("top_token_ratio", 0.0) or 0.0)
    candidate_top_token_ratio = float(candidate_quality.get("top_token_ratio", 0.0) or 0.0)
    top_token_ratio_bound = max(
        MAX_ABSOLUTE_TOP_TOKEN_RATIO,
        baseline_top_token_ratio * MAX_RELATIVE_TOP_TOKEN_RATIO_MULTIPLIER,
    )
    candidate_success = bool(candidate_run.get("success"))
    candidate_timed_out = bool(candidate_run.get("timed_out"))
    baseline_summary = summary_metrics(baseline_run, default_success=True)
    candidate_summary = summary_metrics(candidate_run, default_success=False)
    failures = guardrail_failures(
        baseline=baseline_summary,
        candidate=candidate_summary,
        corrected_char_ratio=candidate_char_ratio,
        top_token_ratio_bound=top_token_ratio_bound,
    )
    notes = []
    if failures:
        rendered_failures = ", ".join(f"`{code}`" for code in failures)
        notes.append(f"- Metric guardrail failures: {rendered_failures}.")
    if candidate_timed_out:
        notes.append(
            "- Candidate command timed out; quality metrics for that row are diagnostic only."
        )
    if not candidate_success:
        notes.append(
            f"- Candidate command failed with return code `{candidate_run.get('returncode', 'n/a')}`; "
            "quality metrics for that row are diagnostic only."
        )
    if baseline_chars <= 0:
        notes.append(
            "- Baseline produced no corrected text; same-audio ratio checks are not meaningful."
        )
    if int(candidate_quality.get("corrected_char_count", 0) or 0) == 0:
        notes.append(
            "- Candidate produced no corrected text; do not interpret zero review issues as a quality pass."
        )
    elif baseline_chars > 0 and not (
        MIN_CANDIDATE_CHAR_RATIO <= candidate_char_ratio <= MAX_CANDIDATE_CHAR_RATIO
    ):
        notes.append(
            "- Candidate corrected-text length is outside the same-audio baseline ratio bounds; "
            "do not treat it as a quality pass without review."
        )
    if not bool(candidate_timing.get("srt_vtt_compatible", False)):
        notes.append(
            "- Candidate segments are not SRT/VTT-compatible; timestamp quality must be fixed or reviewed."
        )
    if int(candidate_review.get("issue_count", 0) or 0) > int(
        baseline_review.get("issue_count", 0) or 0
    ):
        notes.append("- Candidate review issue count is higher than the baseline.")
    if int(candidate_review.get("segment_issue_count", 0) or 0) > int(
        baseline_review.get("segment_issue_count", 0) or 0
    ):
        notes.append("- Candidate review segment issue count is higher than the baseline.")
    if int(candidate_quality.get("correction_count", 0) or 0) > int(
        baseline_quality.get("correction_count", 0) or 0
    ):
        notes.append("- Candidate correction count is higher than the baseline.")
    if int(candidate_quality.get("max_repeated_token_run", 0) or 0) > int(
        baseline_quality.get("max_repeated_token_run", 0) or 0
    ):
        notes.append("- Candidate repeated-token run is higher than the baseline.")
    if candidate_top_token_ratio > top_token_ratio_bound:
        notes.append(
            "- Candidate top-token ratio is too high relative to the baseline; check for repetitive or low-diversity output."
        )
    lines = [
        "# ASR Candidate Comparison",
        "",
        f"- Audio: `{audio}`",
        f"- Candidate: `{candidate_run.get('candidate')}`",
        "",
        "| Run | Status | Return code | Runtime s | Peak RSS MB | Corrected chars | Baseline ratio | Empty segments | Review issues | Segment issues | Corrections | Max repeated token run | Top token ratio | SRT/VTT timestamps |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        "| Audio2Text baseline | "
        + " | ".join(
            [
                "ok",
                str(baseline_run.get("returncode", 0)),
                f"{float(baseline_run.get('runtime_seconds', 0.0)):.2f}",
                format_float(baseline_run.get("peak_rss_mb")),
                str(baseline_quality.get("corrected_char_count", "n/a")),
                "1.00",
                str(baseline_quality.get("empty_corrected_segment_count", "n/a")),
                str(baseline_review.get("issue_count", "n/a")),
                str(baseline_review.get("segment_issue_count", "n/a")),
                str(baseline_quality.get("correction_count", "n/a")),
                str(baseline_quality.get("max_repeated_token_run", "n/a")),
                str(baseline_quality.get("top_token_ratio", "n/a")),
                "yes" if bool(baseline_timing.get("srt_vtt_compatible", False)) else "no",
            ]
        )
        + " |",
        "| Candidate | "
        + " | ".join(
            [
                "ok" if candidate_success else "failed",
                str(candidate_run.get("returncode", "n/a")),
                f"{float(candidate_run.get('runtime_seconds', 0.0)):.2f}",
                format_float(candidate_run.get("peak_rss_mb")),
                str(candidate_quality.get("corrected_char_count", "n/a")),
                f"{candidate_char_ratio:.2f}",
                str(candidate_quality.get("empty_corrected_segment_count", "n/a")),
                str(candidate_review.get("issue_count", "n/a")),
                str(candidate_review.get("segment_issue_count", "n/a")),
                str(candidate_quality.get("correction_count", "n/a")),
                str(candidate_quality.get("max_repeated_token_run", "n/a")),
                str(candidate_quality.get("top_token_ratio", "n/a")),
                "yes" if bool(candidate_timing.get("srt_vtt_compatible", False)) else "no",
            ]
        )
        + " |",
        "",
        *(["## Notes", "", *notes, ""] if notes else []),
        "Promotion guardrail: a candidate should pass the metric guardrail on the same samples before it is considered for production. Metric pass is necessary but not sufficient; semantic transcript quality still requires review.",
    ]
    return "\n".join(lines) + "\n"
