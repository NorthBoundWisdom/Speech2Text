from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..backend_promotion import validate_backend_promotion
from ..backends import (
    ASRError,
    ASRTranscribeOptions,
    backend_names,
    build_backend,
    doctor_backend,
    get_backend_spec,
)
from ..models import resolve_model


def cmd_backends(args: argparse.Namespace) -> int:
    if args.backends_command == "list":
        rows = [get_backend_spec(name).to_json() for name in backend_names()]
        if args.json_output:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for row in rows:
                marker = "yes" if row["transcribable"] else "no"
                print(f"{row['name']:<14} {row['status']:<10} transcribe={marker}  {row['notes']}")
        return 0
    if args.backends_command == "doctor":
        payload = doctor_backend(args.backend)
        if args.json_output:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            doctor = payload["doctor"]
            print(f"backend: {payload['name']}")
            print(f"status: {payload['status']}")
            print(f"transcribable: {payload['transcribable']}")
            print(f"doctor: {'ok' if doctor.get('success') else 'failed'}")
            for item in doctor.get("diagnostics", []):
                print(f"- {item}")
        return 0 if payload["doctor"].get("success") else 1
    if args.backends_command == "transcribe-smoke":
        return _cmd_transcribe_smoke(args)
    raise ASRError(f"Unknown backends command: {args.backends_command}")


def cmd_validate_backend_promotion(args: argparse.Namespace) -> int:
    errors = validate_backend_promotion(
        args.gate_summary,
        args.semantic_review,
        min_audio_count=args.min_audio_count,
        min_content_type_count=args.min_content_types,
        min_gold_fixture_count=args.min_gold_fixtures,
    )
    payload = {
        "success": not errors,
        "errors": errors,
        "gate_summary": str(args.gate_summary),
        "semantic_review": str(args.semantic_review),
    }
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif errors:
        for error in errors:
            print(f"ERROR: {error}")
    else:
        print("backend promotion evidence: ok")
    return 0 if not errors else 1


def _cmd_transcribe_smoke(args: argparse.Namespace) -> int:
    model = resolve_model(args.model)
    backend = build_backend(args.backend, recording_json=args.recording_json, verbose=False)
    result = backend.transcribe(
        Path(args.audio),
        ASRTranscribeOptions(
            model=model,
            language=args.language,
            word_timestamps=args.word_timestamps,
        ),
    )
    text = str(result.get("text", "")).strip()
    payload = {
        "success": bool(text or result.get("segments")),
        "backend": backend.name,
        "model": model,
        "text_preview": text[:120],
        "segment_count": len(result.get("segments", []))
        if isinstance(result.get("segments"), list)
        else 0,
    }
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"backend: {payload['backend']}")
        print(f"success: {payload['success']}")
        print(f"segments: {payload['segment_count']}")
        if payload["text_preview"]:
            print(f"text: {payload['text_preview']}")
    return 0 if payload["success"] else 1
