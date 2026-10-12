from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audio import AudioError, ffprobe_duration
from .backends import ASRTranscribeOptions, MlxWhisperBackend
from .corrections import load_glossary, make_prompt
from .models import DEFAULT_BENCHMARK_MODELS, model_source, resolve_model, short_model_name
from .paths import DEFAULT_OUTPUT_DIR
from .runinfo import machine_info, now_iso, peak_rss_mb
from .utils import ensure_dir, read_text, write_json_atomic, write_text_atomic

DEFAULT_TROUBLE_SPOTS = (
    "某种程度上的生存焦虑",
    "physical 的生存焦虑",
    "生物竞赛",
    "本科",
    "西电",
    "软件工程",
    "计算机科学",
)


@dataclass
class BenchmarkOptions:
    sample_path: Path
    output_dir: Path = DEFAULT_OUTPUT_DIR / "benchmark"
    models: tuple[str, ...] = DEFAULT_BENCHMARK_MODELS
    language: str | None = "zh"
    prompt_file: Path | None = None
    glossary_file: Path | None = None
    repeat: int = 1
    word_timestamps: bool = False
    verbose: bool | None = False


def _model_download_size_bytes(repo: str) -> int | None:
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return None
    try:
        info = HfApi().model_info(repo, files_metadata=True)
    except Exception:  # pragma: no cover - third-party/network exception types vary.
        return None
    total = 0
    seen = False
    for sibling in getattr(info, "siblings", []) or []:
        size = getattr(sibling, "size", None)
        if isinstance(size, int):
            total += size
            seen = True
    return total if seen else None


def _quality_hits(
    text: str, trouble_spots: tuple[str, ...] = DEFAULT_TROUBLE_SPOTS
) -> dict[str, bool]:
    return {spot: spot in text for spot in trouble_spots}


def run_benchmark(options: BenchmarkOptions) -> dict[str, Any]:
    out_dir = ensure_dir(options.output_dir)
    prompt = make_prompt(read_text(options.prompt_file), load_glossary(options.glossary_file))
    backend = MlxWhisperBackend(verbose=options.verbose)
    try:
        sample_duration = ffprobe_duration(options.sample_path)
    except AudioError:
        sample_duration = None

    rows: list[dict[str, Any]] = []
    for model in options.models:
        repo = resolve_model(model)
        model_dir = ensure_dir(out_dir / short_model_name(repo))
        repetitions: list[dict[str, Any]] = []
        final_text = ""
        final_result: dict[str, Any] = {}
        for i in range(max(1, options.repeat)):
            started = time.perf_counter()
            result = backend.transcribe(
                options.sample_path,
                ASRTranscribeOptions(
                    model=repo,
                    language=options.language,
                    prompt=prompt,
                    word_timestamps=options.word_timestamps,
                    temperature=0.0,
                ),
            )
            elapsed = time.perf_counter() - started
            final_result = result
            final_text = str(result.get("text", ""))
            repetitions.append(
                {
                    "repeat_index": i,
                    "runtime_seconds": elapsed,
                    "speed_factor": sample_duration / elapsed
                    if sample_duration and elapsed > 0
                    else None,
                    "peak_rss_mb": peak_rss_mb(),
                }
            )
        write_text_atomic(model_dir / "transcript.txt", final_text)
        write_json_atomic(model_dir / "result.json", final_result)
        rows.append(
            {
                "model_input": model,
                "model": repo,
                "model_source": model_source(repo),
                "backend": backend.name,
                "backend_capabilities": {
                    "supports_prompt": backend.supports_prompt,
                    "supports_word_timestamps": backend.supports_word_timestamps,
                    "supports_diarization": backend.supports_diarization,
                },
                "download_size_bytes": _model_download_size_bytes(repo),
                "repetitions": repetitions,
                "quality_hits": _quality_hits(final_text),
                "transcript_path": str(model_dir / "transcript.txt"),
                "result_json_path": str(model_dir / "result.json"),
            }
        )

    summary = {
        "created_at": now_iso(),
        "sample_path": str(options.sample_path),
        "sample_duration": sample_duration,
        "backend": backend.name,
        "backend_capabilities": {
            "supports_prompt": backend.supports_prompt,
            "supports_word_timestamps": backend.supports_word_timestamps,
            "supports_diarization": backend.supports_diarization,
        },
        "language": options.language,
        "prompt_file": str(options.prompt_file or ""),
        "glossary_file": str(options.glossary_file or ""),
        "repeat": options.repeat,
        "machine_info": machine_info(),
        "trouble_spots": list(DEFAULT_TROUBLE_SPOTS),
        "results": rows,
    }
    write_json_atomic(out_dir / "benchmark.json", summary)
    write_text_atomic(out_dir / "benchmark.md", benchmark_markdown(summary))
    return summary


def _bytes_to_gb(size: int | None) -> str:
    if size is None:
        return ""
    return f"{size / (1024**3):.2f} GB"


def benchmark_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# SonaFolio Model Benchmark",
        "",
        f"- Sample: `{summary.get('sample_path', '')}`",
        f"- Language: `{summary.get('language', '')}`",
        f"- Created: {summary.get('created_at', '')}",
        "",
        "| Model | Download size | First run | Cached/last run | Trouble-spot hits | Transcript |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("results", []):
        reps = row.get("repetitions", []) or []
        first = reps[0].get("runtime_seconds") if reps else None
        last = reps[-1].get("runtime_seconds") if reps else None
        hits = row.get("quality_hits", {}) or {}
        hit_count = sum(1 for v in hits.values() if v)
        lines.append(
            "| {model} | {size} | {first} | {last} | {hit_count}/{total} | `{path}` |".format(
                model=row.get("model", ""),
                size=_bytes_to_gb(row.get("download_size_bytes")),
                first=f"{first:.2f}s" if isinstance(first, (int, float)) else "",
                last=f"{last:.2f}s" if isinstance(last, (int, float)) else "",
                hit_count=hit_count,
                total=len(hits),
                path=row.get("transcript_path", ""),
            )
        )
    lines.append("")
    lines.append("## Trouble spots")
    lines.append("")
    for row in summary.get("results", []):
        lines.append(f"### {row.get('model', '')}")
        hits = row.get("quality_hits", {}) or {}
        for spot, ok in hits.items():
            lines.append(f"- [{'x' if ok else ' '}] {spot}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
