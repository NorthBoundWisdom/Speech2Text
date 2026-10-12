from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import write_json_atomic


@dataclass(frozen=True)
class SearchHit:
    score: int
    episode: str
    path: str
    timestamp: str
    line: str

    def to_json(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "episode": self.episode,
            "path": self.path,
            "timestamp": self.timestamp,
            "line": self.line,
        }


_TIMESTAMP_RE = re.compile(r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?)")


def _transcript_files(root: Path) -> list[Path]:
    root = root.expanduser()
    if root.is_file():
        return [root]
    files = [*root.rglob("transcript.md"), *root.rglob("transcript.readable.md")]
    return sorted(set(files))


def _timestamp(line: str) -> str:
    match = _TIMESTAMP_RE.search(line)
    return match.group("time") if match else ""


def build_search_index(root: Path, index_path: Path) -> dict[str, Any]:
    documents: list[dict[str, Any]] = []
    for transcript in _transcript_files(root):
        text = transcript.read_text(encoding="utf-8")
        episode = transcript.parent.name
        for line_number, line in enumerate(text.splitlines(), start=1):
            clean = line.strip()
            if not clean:
                continue
            documents.append(
                {
                    "episode": episode,
                    "path": str(transcript),
                    "line_number": line_number,
                    "timestamp": _timestamp(clean),
                    "text": clean,
                    "tokens": _tokens(clean),
                }
            )
    payload = {
        "schema_version": 1,
        "root": str(root),
        "document_count": len(documents),
        "documents": documents,
    }
    write_json_atomic(index_path, payload)
    return payload


def search_index(query: str, index_path: Path, *, limit: int = 10) -> list[SearchHit]:
    import json

    with index_path.expanduser().open("r", encoding="utf-8") as f:
        payload = json.load(f)
    terms = _tokens(query)
    hits: list[SearchHit] = []
    for doc in payload.get("documents", []):
        if not isinstance(doc, dict):
            continue
        tokens = doc.get("tokens", [])
        text = str(doc.get("text", ""))
        score = sum(2 for term in terms if term in tokens) + sum(
            1 for term in terms if term and term in text.lower()
        )
        if score <= 0:
            continue
        hits.append(
            SearchHit(
                score=score,
                episode=str(doc.get("episode", "")),
                path=str(doc.get("path", "")),
                timestamp=str(doc.get("timestamp", "")),
                line=text,
            )
        )
    return sorted(hits, key=lambda item: (-item.score, item.episode, item.timestamp))[:limit]


def _tokens(text: str) -> list[str]:
    lowered = text.lower()
    ascii_terms = re.findall(r"[a-z0-9][a-z0-9_\-]{1,}", lowered)
    cjk_terms = re.findall(r"[\u4e00-\u9fff]{2,}", lowered)
    return ascii_terms + cjk_terms
