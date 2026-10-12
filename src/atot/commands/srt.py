from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from ..config import load_app_config
from ..languages import normalize_language_hint
from ..paths import DEFAULT_GLOSSARY_FILE, DEFAULT_PROMPT_FILE, path_context
from ..platform_defaults import default_asr_backend
from ..pipeline import run_transcription
from ..runinfo import now_iso
from ..runtime_defaults import (
    DEFAULT_COMPRESSION_RATIO_THRESHOLD,
    DEFAULT_LOGPROB_THRESHOLD,
    DEFAULT_NO_SPEECH_THRESHOLD,
    DEFAULT_SAMPLE_RATE,
)
from ..subtitles import cues_to_srt, segments_to_cues, validate_srt_text
from ..translation import (
    DEFAULT_TRANSLATION_MODEL_ALIAS,
    SubtitleTranslation,
    normalize_target_language,
    translate_subtitle_cues,
    translate_subtitle_cues_cloud,
)
from ..transcribe_options import transcribe_options_from_values
from ..utils import ensure_dir, read_json, slugify, write_json_atomic, write_text_atomic


@dataclass
class SrtExportOptions:
    inputs: list[Path]
    output: Path | None = None
    output_dir: Path | None = None
    overwrite: bool = False
    language: list[str] | None = None
    backend: str = field(default_factory=default_asr_backend)
    recording_json: Path | None = None
    sample_rate: int = DEFAULT_SAMPLE_RATE
    force_prepare: bool = False
    force_chunks: bool = False
    force: bool = False
    chunking: str = "auto"
    chunk_length: float = 1200.0
    max_chunk_length: float | None = None
    silence_threshold: float | None = None
    min_silence: float = 0.5
    local_only: bool = True
    temperature: float = 0.0
    no_speech_threshold: float = DEFAULT_NO_SPEECH_THRESHOLD
    logprob_threshold: float = DEFAULT_LOGPROB_THRESHOLD
    compression_ratio_threshold: float = DEFAULT_COMPRESSION_RATIO_THRESHOLD
    hallucination_silence_threshold: float | None = None
    condition_on_previous_text: bool = True
    prompt_file: Path | None = DEFAULT_PROMPT_FILE
    glossary_file: Path | None = DEFAULT_GLOSSARY_FILE
    rule_pack: list[str] | None = None
    overlap: float = 10.0
    word_timestamps: bool = False
    verbose: bool = False
    json_output: bool = False


def requested_languages_from_args(values: list[str] | None) -> tuple[str | None, list[str]]:
    requested = [item.strip() for item in (values or ["zh"]) if item and item.strip()]
    if not requested:
        requested = ["zh"]
    requested = list(dict.fromkeys(requested))
    normalized = [normalize_language_hint(item) for item in requested]
    unique_normalized = [item for item in dict.fromkeys(normalized) if item is not None]
    if None in normalized or len(unique_normalized) > 1:
        return None, requested
    return unique_normalized[0], requested


def srt_job_dir(input_path: Path) -> Path:
    resolved = input_path.expanduser().resolve()
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
    return path_context().cache_dir / "srt" / f"{slugify(resolved.stem)}-{digest}"


def srt_destination(
    input_path: Path,
    *,
    output: Path | None = None,
    output_dir: Path | None = None,
    target_language: str | None = None,
) -> Path:
    source = input_path.expanduser()
    if output is not None:
        return output.expanduser()
    suffix = f".{target_language}.srt" if target_language else ".srt"
    if output_dir is not None:
        return output_dir.expanduser() / f"{source.stem}{suffix}"
    return source.with_suffix(suffix)


def cmd_srt(args: argparse.Namespace) -> int:
    payload = run_srt_export(args)
    if not args.json_output:
        for result in payload["results"]:
            if result.get("success"):
                print(f"SRT: {result.get('srt_path')}")
            else:
                print(f"Skipped: {result.get('input_path')} ({result.get('error')})")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["success"] else 1


def run_srt_export(args: argparse.Namespace | SrtExportOptions) -> dict[str, Any]:
    inputs: list[Path] = list(args.inputs)
    config = load_app_config(include_api_key=False)
    target_language = (
        normalize_target_language(config.translation.target_language)
        if config.translation.enabled
        else None
    )
    if args.output is not None and len(inputs) != 1:
        raise ValueError("--output can only be used with a single input.")
    destinations = [
        srt_destination(
            item,
            output=args.output if len(inputs) == 1 else None,
            output_dir=args.output_dir,
            target_language=target_language,
        )
        for item in inputs
    ]
    resolved_destinations = [item.expanduser().resolve() for item in destinations]
    if len(set(resolved_destinations)) != len(resolved_destinations):
        raise ValueError("Multiple inputs resolve to the same SRT destination.")

    results: list[dict[str, Any]] = []
    for input_path, destination in zip(inputs, destinations, strict=True):
        result = export_srt_for_input(input_path, destination, args=args)
        results.append(result)

    success = all(bool(item.get("success")) for item in results)
    return {"success": success, "results": results}


def export_srt_for_input(
    input_path: Path, destination: Path, *, args: argparse.Namespace | SrtExportOptions
) -> dict[str, Any]:
    source = input_path.expanduser().resolve()
    target = destination.expanduser().resolve()
    asr_language, requested_languages = requested_languages_from_args(
        getattr(args, "language", None)
    )
    config = load_app_config(include_api_key=False)
    target_language = (
        normalize_target_language(config.translation.target_language)
        if config.translation.enabled
        else None
    )
    job_dir = srt_job_dir(source)

    if target.exists() and not getattr(args, "overwrite", False):
        return {
            "success": False,
            "status": "exists",
            "input_path": str(source),
            "srt_path": str(target),
            "job_dir": str(job_dir),
            "requested_languages": requested_languages,
            "asr_language": asr_language,
            "target_language": target_language,
            "error": "SRT already exists. Use --overwrite to replace it.",
        }

    runtime_args = argparse.Namespace(**vars(args))
    runtime_args.job_dir = job_dir
    runtime_args.language = asr_language
    runtime_args.local_only = True
    runtime_args.no_cloud_summary = True
    remove_default_chinese_context_for_translation(
        runtime_args,
        requested_languages=requested_languages,
        asr_language=asr_language,
        target_language=target_language,
    )
    opts = transcribe_options_from_values(
        runtime_args,
        input_path=source,
        output_dir=path_context().cache_dir / "srt",
        force_all=True,
    )
    run = run_transcription(opts)
    generated_srt = Path(str(run.get("job_dir", job_dir))) / "transcript.srt"
    if not generated_srt.exists():
        raise FileNotFoundError(f"Expected SRT was not produced: {generated_srt}")

    translation_metadata: dict[str, Any] | None = None
    source_language: str | None = None
    if target_language:
        translated = export_translated_srt(
            job_dir=Path(str(run.get("job_dir", job_dir))),
            run=run,
            requested_languages=requested_languages,
            asr_language=asr_language,
            target_language=target_language,
            translation_backend=config.translation.backend,
        )
        text = translated["text"]
        translation_metadata = translated["metadata"]
        source_language = str(translation_metadata.get("source_language") or "")
    else:
        text = generated_srt.read_text(encoding="utf-8")
    write_text_atomic(target, text)
    metadata = {
        "created_at": now_iso(),
        "input_path": str(source),
        "srt_path": str(target),
        "job_dir": str(job_dir),
        "requested_languages": requested_languages,
        "asr_language": asr_language,
        "source_language": source_language,
        "target_language": target_language,
        "translation": translation_metadata,
        "run_json": str(Path(str(run.get("job_dir", job_dir))) / "run.json"),
    }
    write_json_atomic(ensure_dir(job_dir) / "srt_export.json", metadata)
    return {
        "success": True,
        "status": "exported",
        **metadata,
        "qa": run.get("qa", {}),
    }


def export_translated_srt(
    *,
    job_dir: Path,
    run: dict[str, Any],
    requested_languages: list[str],
    asr_language: str | None,
    target_language: str,
    translation_backend: str = "local",
) -> dict[str, Any]:
    details = job_dir
    corrected_path = details / "corrected.json"
    corrected = read_json(corrected_path)
    segments = corrected.get("segments") if isinstance(corrected, dict) else None
    if not isinstance(segments, list):
        raise ValueError(f"Expected corrected segments in {corrected_path}")
    cues = segments_to_cues(segments, max_chars=140, wrap_text=False)
    source_language = infer_translation_source_language(
        job_dir=job_dir,
        run=run,
        requested_languages=requested_languages,
        asr_language=asr_language,
    )
    if translation_backend == "cloud":
        translation = translate_subtitle_cues_cloud(
            cues,
            source_language=source_language,
            target_language=target_language,
            audit_dir=details,
        )
    elif translation_backend == "local":
        translation = translate_subtitle_cues(
            cues,
            source_language=source_language,
            target_language=target_language,
            model_alias=DEFAULT_TRANSLATION_MODEL_ALIAS,
        )
    else:
        raise ValueError(f"Unsupported translation backend: {translation_backend}")
    if not isinstance(translation, SubtitleTranslation):
        raise TypeError("translate_subtitle_cues must return SubtitleTranslation.")
    if len(translation.cues) != len(cues):
        raise RuntimeError(
            f"Translation returned {len(translation.cues)} cues for {len(cues)} source cues."
        )
    text = cues_to_srt(translation.cues)
    issues = validate_srt_text(text)
    blockers = [item for item in issues if item.get("severity") == "blocker"]
    if blockers:
        raise ValueError(f"Translated SRT failed validation: {blockers[0].get('message')}")
    write_text_atomic(details / f"transcript.{target_language}.srt", text)
    metadata = {
        **translation.metadata,
        "backend": translation.metadata.get("backend", translation_backend),
        "source_language": source_language,
        "target_language": target_language,
        "translation_model": translation.metadata.get("model", DEFAULT_TRANSLATION_MODEL_ALIAS),
        "cue_count": len(cues),
    }
    write_json_atomic(details / f"translation.{target_language}.json", metadata)
    return {"text": text, "metadata": metadata}


def infer_translation_source_language(
    *,
    job_dir: Path,
    run: dict[str, Any],
    requested_languages: list[str],
    asr_language: str | None,
) -> str:
    for value in [
        run.get("detected_language") if isinstance(run, dict) else None,
        run.get("language") if isinstance(run, dict) else None,
        asr_language,
        _detected_language_from_chunk_payloads(job_dir),
    ]:
        normalized = normalize_language_hint(str(value)) if value else None
        if normalized:
            return normalized
    normalized_requested: list[str] = []
    for item in requested_languages:
        normalized = normalize_language_hint(item)
        if normalized is not None:
            normalized_requested.append(normalized)
    unique = list(dict.fromkeys(normalized_requested))
    if len(unique) == 1:
        return unique[0]
    raise ValueError(
        "Could not determine source language for local subtitle translation. "
        "Pass one explicit --language value, or use --language auto only when ASR reports a detected language."
    )


def _detected_language_from_chunk_payloads(job_dir: Path) -> str | None:
    counts: dict[str, int] = {}
    for path in sorted((job_dir / "chunks").glob("*.json")):
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        result = payload.get("result") if isinstance(payload, dict) else None
        if not isinstance(result, dict):
            continue
        language = (
            normalize_language_hint(str(result.get("language"))) if result.get("language") else None
        )
        if language:
            counts[language] = counts.get(language, 0) + 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def remove_default_chinese_context_for_translation(
    args: argparse.Namespace,
    *,
    requested_languages: list[str],
    asr_language: str | None,
    target_language: str | None,
) -> None:
    if target_language != "zh" or _translation_source_is_chinese(requested_languages, asr_language):
        return
    if _same_path(getattr(args, "prompt_file", None), DEFAULT_PROMPT_FILE):
        args.prompt_file = None
    if _same_path(getattr(args, "glossary_file", None), DEFAULT_GLOSSARY_FILE):
        args.glossary_file = None


def _translation_source_is_chinese(
    requested_languages: list[str], asr_language: str | None
) -> bool:
    if asr_language == "zh":
        return True
    normalized = [normalize_language_hint(item) for item in requested_languages]
    return normalized == ["zh"]


def _same_path(left: Path | None, right: Path) -> bool:
    if left is None:
        return False
    return left.expanduser() == right.expanduser()
