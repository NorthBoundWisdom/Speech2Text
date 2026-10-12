from __future__ import annotations

from copy import deepcopy
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .numeric import as_float
from .subtitles import segments_to_srt as subtitle_segments_to_srt
from .subtitles import segments_to_vtt as subtitle_segments_to_vtt
from .segments import canonicalize_segments
from .utils import compact_ws, seconds_to_hms
from .readable import compose_readable_transcript


def normalize_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return canonicalize_segments(segments, sort=True, enforce_monotonic=False, drop_empty=True)


def enforce_monotonic_timeline(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return canonicalize_segments(segments, sort=False, enforce_monotonic=True, drop_empty=True)


def _segment_metric(segment: dict[str, Any], key: str) -> float | None:
    value = segment.get(key)
    if value is None and isinstance(segment.get("raw"), dict):
        value = segment["raw"].get(key)
    return as_float(value)


def _merge_quality_score(segment: dict[str, Any]) -> float:
    score = min(len(compact_ws(str(segment.get("text", "")))), 120) / 1000.0
    avg_logprob = _segment_metric(segment, "avg_logprob")
    if avg_logprob is not None:
        score += avg_logprob
    no_speech_prob = _segment_metric(segment, "no_speech_prob")
    if no_speech_prob is not None:
        score -= no_speech_prob
    compression_ratio = _segment_metric(segment, "compression_ratio")
    if compression_ratio is not None:
        score -= max(0.0, compression_ratio - 1.0) / 4.0
    return score


def _text_similarity(left: str, right: str) -> float:
    left = compact_ws(left)
    right = compact_ws(right)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if len(left) >= 8 and len(right) >= 8 and (left in right or right in left):
        return 0.95
    return SequenceMatcher(None, left, right).ratio()


def _core_overlap_ratio(start: float, end: float, core_start: float, core_end: float) -> float:
    duration = max(0.001, end - start)
    overlap = max(0.0, min(end, core_end) - max(start, core_start))
    return overlap / duration


def merge_chunk_payloads_with_decisions(
    chunk_payloads: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge chunk-local MLX Whisper segments into global timeline segments.

    Overlapped audio is used for model context. During merge, segments are kept
    when at least half of their duration overlaps the non-overlapped core window,
    then near-duplicate boundary text is removed by timestamp and text similarity.
    """
    merged: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for payload in sorted(chunk_payloads, key=lambda p: int(p.get("chunk", {}).get("index", 0))):
        chunk = payload.get("chunk", {})
        result = payload.get("result", {})
        source_start = float(chunk.get("source_start", 0.0))
        core_start = float(chunk.get("core_start", source_start))
        core_end = float(chunk.get("core_end", chunk.get("source_end", source_start)))
        total_duration = float(payload.get("audio_duration", core_end))
        chunk_index = int(chunk.get("index", 0))
        is_first = core_start <= 0.001
        is_last = core_end >= total_duration - 0.001

        for local in result.get("segments", []) or []:
            text = compact_ws(str(local.get("text", "")))
            if not text:
                continue
            global_start = source_start + float(local.get("start", 0.0))
            global_end = source_start + float(local.get("end", global_start + 0.01))
            global_end = max(global_start + 0.01, global_end)
            overlap_ratio = _core_overlap_ratio(global_start, global_end, core_start, core_end)
            if overlap_ratio < 0.5:
                decisions.append(
                    {
                        "action": "discard_outside_core",
                        "chunk_index": chunk_index,
                        "start": round(global_start, 3),
                        "end": round(global_end, 3),
                        "core_start": round(core_start, 3),
                        "core_end": round(core_end, 3),
                        "overlap_ratio": round(overlap_ratio, 4),
                        "text": text,
                    }
                )
                continue
            item = deepcopy(local)
            item["start"] = global_start
            item["end"] = global_end
            item["text"] = text
            item["chunk_index"] = chunk_index
            if (not is_first and global_start < core_start) or (
                not is_last and global_end > core_end
            ):
                decisions.append(
                    {
                        "action": "keep_boundary_segment",
                        "chunk_index": chunk_index,
                        "start": round(global_start, 3),
                        "end": round(global_end, 3),
                        "core_start": round(core_start, 3),
                        "core_end": round(core_end, 3),
                        "overlap_ratio": round(overlap_ratio, 4),
                        "text": text,
                    }
                )
            merged.append(item)
    deduped = dedupe_segments(normalize_segments(merged), decisions=decisions)
    return enforce_monotonic_timeline(deduped), decisions


def merge_chunk_payloads(chunk_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged, _decisions = merge_chunk_payloads_with_decisions(chunk_payloads)
    return merged


def dedupe_segments(
    segments: list[dict[str, Any]],
    *,
    window_seconds: float = 1.0,
    decisions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    for seg in segments:
        text = compact_ws(str(seg.get("text", "")))
        if not text:
            continue
        if deduped:
            prev = deduped[-1]
            prev_start = float(prev.get("start", 0))
            prev_end = float(prev.get("end", 0))
            seg_start = float(seg.get("start", 0))
            seg_end = float(seg.get("end", 0))
            prev_text = compact_ws(str(prev.get("text", "")))
            same_text = compact_ws(str(prev.get("text", ""))) == text
            close = abs(prev_start - seg_start) <= window_seconds
            time_overlap = max(0.0, min(prev_end, seg_end) - max(prev_start, seg_start))
            similar_boundary_text = _text_similarity(prev_text, text) >= 0.86
            if similar_boundary_text and (close or time_overlap > 0.0):
                prev_score = _merge_quality_score(prev)
                seg_score = _merge_quality_score(seg)
                chosen = seg if seg_score > prev_score else prev
                dropped = prev if chosen is seg else seg
                if same_text:
                    chosen["start"] = min(prev_start, seg_start)
                    chosen["end"] = max(prev_end, seg_end)
                if chosen is seg:
                    deduped[-1] = seg
                if decisions is not None:
                    decisions.append(
                        {
                            "action": "dedupe_similar_boundary",
                            "kept_chunk_index": chosen.get("chunk_index"),
                            "dropped_chunk_index": dropped.get("chunk_index"),
                            "kept_start": round(float(chosen.get("start", 0.0)), 3),
                            "kept_end": round(float(chosen.get("end", 0.0)), 3),
                            "dropped_start": round(float(dropped.get("start", 0.0)), 3),
                            "dropped_end": round(float(dropped.get("end", 0.0)), 3),
                            "similarity": round(_text_similarity(prev_text, text), 4),
                            "kept_text": compact_ws(str(chosen.get("text", ""))),
                            "dropped_text": compact_ws(str(dropped.get("text", ""))),
                        }
                    )
                continue
            if same_text and close:
                prev["end"] = max(prev_end, seg_end)
                continue
            contained_by_previous_long_segment = (
                prev_end >= seg_end
                and prev_end - prev_start >= 15.0
                and seg_start >= prev_start
                and seg_start - prev_start <= 10.0
            )
            if contained_by_previous_long_segment and (len(text) <= 80 or text in prev_text):
                continue
        deduped.append(seg)
    for i, seg in enumerate(deduped):
        seg["id"] = i
    return deduped


def segments_to_txt(segments: list[dict[str, Any]]) -> str:
    lines = [compact_ws(str(s.get("text", ""))) for s in segments]
    return "\n".join(line for line in lines if line)


def segments_to_markdown(
    segments: list[dict[str, Any]],
    *,
    title: str = "Transcript",
    corrected: bool = True,
    model: str | None = None,
    input_path: str | None = None,
) -> str:
    lines: list[str] = [f"# {title}", ""]
    if input_path:
        lines.append(f"- Input: `{input_path}`")
    if model:
        lines.append(f"- Model: `{model}`")
    lines.append(f"- Transcript type: {'corrected' if corrected else 'raw'}")
    lines.append("")
    current_bucket: str | None = None
    for segment in segments:
        text = compact_ws(str(segment.get("text", "")))
        if not text:
            continue
        start = float(segment.get("start", 0.0))
        bucket = seconds_to_hms(start)
        # New heading roughly every 5 minutes, plus the first segment.
        bucket_seconds = int(start // 300) * 300
        heading = seconds_to_hms(bucket_seconds)
        if heading != current_bucket:
            current_bucket = heading
            lines.extend(["", f"## {heading}", ""])
        lines.append(f"**[{bucket}]** {text}")
    return "\n".join(lines).strip() + "\n"


def segments_to_timestamped_markdown(
    segments: list[dict[str, Any]],
    *,
    title: str = "Transcript",
) -> str:
    lines = [f"# {title}", ""]
    for segment in segments:
        text = compact_ws(str(segment.get("text", "")))
        if not text:
            continue
        start = seconds_to_hms(float(segment.get("start", 0.0)))
        end = seconds_to_hms(float(segment.get("end", 0.0)))
        lines.append(f"[{start} -> {end}] {text}")
    return "\n".join(lines).strip() + "\n"


def segments_to_readable_markdown(
    segments: list[dict[str, Any]],
    *,
    title: str = "Transcript",
    bucket_seconds: float = 180.0,
) -> str:
    return compose_readable_transcript(
        segments, title=title, bucket_seconds=bucket_seconds
    ).markdown


def segments_to_srt(segments: list[dict[str, Any]]) -> str:
    return subtitle_segments_to_srt(segments)


def segments_to_vtt(segments: list[dict[str, Any]]) -> str:
    return subtitle_segments_to_vtt(segments)


def collect_output_files(job_dir: str | Path) -> dict[str, str]:
    base = Path(job_dir)
    names = [
        "transcript.readable.md",
        "prepared.wav",
        "prepared.meta.json",
        "raw.json",
        "corrected.json",
        "transcript.raw.txt",
        "transcript.corrected.txt",
        "transcript.md",
        "transcript.timestamped.md",
        "transcript.speaker.md",
        "transcript.srt",
        "transcript.vtt",
        "speakers.inferred.json",
        "corrections.json",
        "entity_consistency.json",
        "merge_decisions.json",
        "readable_transformations.json",
        "chunks_manifest.json",
        "qa.json",
        "qa.md",
        "review.json",
        "review.md",
        "run.log",
        "events.jsonl",
        "episode_glossary.json",
        "glossary.effective.json",
        "run.json",
    ]
    return {name: str(base / name) for name in names if (base / name).exists()}
