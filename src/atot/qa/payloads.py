from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..json_io import read_json_if_exists
from ..segment_validation import segments_from_payload


@dataclass(frozen=True)
class QAPayloads:
    raw: Any | None
    corrected: Any | None
    run: Any | None
    review: Any | None
    manifest: Any | None
    glossary: Any | None
    corrections: Any | None
    raw_segments: list[dict[str, Any]]
    corrected_segments: list[dict[str, Any]]

    @property
    def segments(self) -> list[dict[str, Any]]:
        return self.corrected_segments or self.raw_segments


def load_qa_payloads(details: Path) -> QAPayloads:
    raw = read_json_if_exists(details / "raw.json")
    corrected = read_json_if_exists(details / "corrected.json")
    return QAPayloads(
        raw=raw,
        corrected=corrected,
        run=read_json_if_exists(details / "run.json"),
        review=read_json_if_exists(details / "review.json"),
        manifest=read_json_if_exists(details / "chunks_manifest.json"),
        glossary=read_json_if_exists(details / "glossary.effective.json"),
        corrections=read_json_if_exists(details / "corrections.json"),
        raw_segments=segments_from_payload(raw),
        corrected_segments=segments_from_payload(corrected),
    )
