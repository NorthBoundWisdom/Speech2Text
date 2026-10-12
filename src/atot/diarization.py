from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .formats import segments_to_timestamped_markdown
from .utils import read_json, seconds_to_hms, write_json_atomic, write_text_atomic


@dataclass(frozen=True)
class DiarizeOptions:
    output_dir: Path
    mode: str = "inferred"


def _details_dir(output_dir: Path) -> Path:
    return output_dir


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def infer_speakers(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inferred: list[dict[str, Any]] = []
    current = "speaker_1"
    previous_end: float | None = None
    for index, segment in enumerate(segments):
        item = dict(segment)
        start = float(item.get("start", 0.0))
        text = str(item.get("text", ""))
        if previous_end is not None and start - previous_end >= 2.0 and index > 0:
            current = "speaker_2" if current == "speaker_1" else "speaker_1"
        if any(marker in text for marker in ("主持人", "主播")):
            current = "host_inferred"
        elif any(marker in text for marker in ("嘉宾", "老师")):
            current = "guest_inferred"
        item["speaker"] = current
        item["speaker_source"] = "text_inferred"
        item["speaker_confidence"] = "low"
        previous_end = float(item.get("end", start))
        inferred.append(item)
    return inferred


def speaker_markdown(segments: list[dict[str, Any]]) -> str:
    lines = ["# Speaker Transcript", ""]
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = seconds_to_hms(float(segment.get("start", 0.0)))
        speaker = str(segment.get("speaker") or "speaker_inferred")
        confidence = str(segment.get("speaker_confidence") or "low")
        lines.append(f"[{start}] **{speaker}** ({confidence}) {text}")
    return "\n".join(lines).strip() + "\n"


def run_diarization(options: DiarizeOptions) -> dict[str, Any]:
    if options.mode != "inferred":
        raise ValueError("Only --mode inferred is currently supported.")
    output_dir = options.output_dir.expanduser().resolve()
    details = _details_dir(output_dir)
    corrected = _read_json_object(details / "corrected.json")
    segments = corrected.get("segments", []) if isinstance(corrected.get("segments"), list) else []
    inferred = infer_speakers(segments)
    write_json_atomic(
        details / "speakers.inferred.json", {"mode": options.mode, "segments": inferred}
    )
    write_text_atomic(details / "transcript.speaker.md", speaker_markdown(inferred))
    write_text_atomic(
        details / "transcript.timestamped.md",
        segments_to_timestamped_markdown(inferred, title="Transcript"),
    )
    corrected["segments"] = inferred
    write_json_atomic(details / "corrected.json", corrected)
    run = _read_json_object(details / "run.json")
    run["diarization"] = {
        "enabled": True,
        "mode": options.mode,
        "source": "text_inferred",
        "confidence": "low",
        "output_files": ["speakers.inferred.json", "transcript.speaker.md"],
    }
    write_json_atomic(details / "run.json", run)
    return {
        "success": True,
        "mode": options.mode,
        "segment_count": len(inferred),
        "output_dir": str(output_dir),
    }
