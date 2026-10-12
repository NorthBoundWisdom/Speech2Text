from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

from .validation_contracts import CLOUD_BUNDLE_CONTRACT
from .validators_common import read_json_file, safe_relative_path as _safe_relative_path


MEDIA_SUFFIXES = set(CLOUD_BUNDLE_CONTRACT.media_suffixes)
TEXT_SUFFIXES = set(CLOUD_BUNDLE_CONTRACT.text_suffixes)
LOCAL_ONLY_NAMES = set(CLOUD_BUNDLE_CONTRACT.local_only_names)
REQUIRED_CLOUD_INPUT_FILES = set(CLOUD_BUNDLE_CONTRACT.required_input_files)


def _manifest_file_list(manifest: dict[str, Any], key: str) -> list[str] | None:
    value = manifest.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return value


def _validate_path_list(
    *,
    base_dir: Path,
    manifest_path: Path,
    paths: list[str] | None,
    key: str,
    errors: list[str],
) -> set[str]:
    if paths is None:
        errors.append(f"{manifest_path}: `{key}` must be a list of relative paths")
        return set()
    seen: set[str] = set()
    for item in paths:
        path = _safe_relative_path(base_dir, item)
        if path is None:
            errors.append(f"{manifest_path}: `{key}` contains unsafe path `{item}`")
            continue
        if item in seen:
            errors.append(f"{manifest_path}: `{key}` contains duplicate path `{item}`")
        seen.add(item)
        if path.name in LOCAL_ONLY_NAMES:
            errors.append(f"{manifest_path}: local-only file `{item}` must not be listed")
        if path.suffix.lower() in MEDIA_SUFFIXES:
            errors.append(f"{manifest_path}: media file `{item}` must not be listed")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            errors.append(f"{manifest_path}: `{item}` must be a text or JSON file")
        if not path.is_file():
            errors.append(f"{manifest_path}: listed file `{item}` does not exist")
    return seen


def _validate_text_only_flags(
    manifest: dict[str, Any], manifest_path: Path, errors: list[str]
) -> None:
    if manifest.get("contains_audio") is not False:
        errors.append(f"{manifest_path}: `contains_audio` must be false")
    if manifest.get("contains_video") is not False:
        errors.append(f"{manifest_path}: `contains_video` must be false")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_input_file_manifest(
    *,
    base_dir: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    listed: set[str],
    errors: list[str],
) -> None:
    rows = manifest.get("input_file_manifest")
    if rows is None:
        return
    if not isinstance(rows, list):
        errors.append(f"{manifest_path}: `input_file_manifest` must be a list")
        return
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{manifest_path}: input_file_manifest[{index}] must be an object")
            continue
        rel = row.get("path")
        path = _safe_relative_path(base_dir, rel) if isinstance(rel, str) else None
        if not isinstance(rel, str) or path is None:
            errors.append(
                f"{manifest_path}: input_file_manifest[{index}].path must be a safe relative path"
            )
            continue
        if rel in seen:
            errors.append(f"{manifest_path}: input_file_manifest contains duplicate path `{rel}`")
        seen.add(rel)
        if rel not in listed:
            errors.append(
                f"{manifest_path}: input_file_manifest path `{rel}` is not included in input_files"
            )
        if not path.is_file():
            errors.append(f"{manifest_path}: input_file_manifest path `{rel}` does not exist")
            continue
        size = row.get("size_bytes")
        if not isinstance(size, int) or size < 0:
            errors.append(f"{manifest_path}: input_file_manifest `{rel}` has invalid size_bytes")
        elif size != path.stat().st_size:
            errors.append(
                f"{manifest_path}: input_file_manifest `{rel}` size_bytes does not match file"
            )
        expected_hash = row.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(
            r"[a-fA-F0-9]{64}", expected_hash
        ):
            errors.append(f"{manifest_path}: input_file_manifest `{rel}` has invalid sha256")
        elif _sha256_file(path).lower() != expected_hash.lower():
            errors.append(
                f"{manifest_path}: input_file_manifest `{rel}` sha256 does not match file"
            )

    expected_rows = {item for item in listed if item != "manifest.json"}
    for rel in sorted(expected_rows - seen):
        errors.append(f"{manifest_path}: input_file_manifest missing file `{rel}`")


def _validate_source_file_manifest(
    *,
    input_dir: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    errors: list[str],
) -> None:
    rows = manifest.get("source_file_manifest")
    if rows is None:
        return
    if not isinstance(rows, list):
        errors.append(f"{manifest_path}: `source_file_manifest` must be a list")
        return
    output_dir = (
        input_dir.parent.parent
        if input_dir.name == "input" and input_dir.parent.name == "cloud"
        else input_dir
    )
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{manifest_path}: source_file_manifest[{index}] must be an object")
            continue
        rel = row.get("path")
        path = _safe_relative_path(output_dir, rel) if isinstance(rel, str) else None
        if not isinstance(rel, str) or path is None:
            errors.append(
                f"{manifest_path}: source_file_manifest[{index}].path must be a safe relative path"
            )
            continue
        if rel in seen:
            errors.append(f"{manifest_path}: source_file_manifest contains duplicate path `{rel}`")
        seen.add(rel)
        if not path.is_file():
            errors.append(f"{manifest_path}: source_file_manifest source `{rel}` does not exist")
            continue
        size = row.get("size_bytes")
        if not isinstance(size, int) or size < 0:
            errors.append(f"{manifest_path}: source_file_manifest `{rel}` has invalid size_bytes")
        elif size != path.stat().st_size:
            errors.append(
                f"{manifest_path}: source_file_manifest `{rel}` size_bytes does not match source file"
            )
        expected_hash = row.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(
            r"[a-fA-F0-9]{64}", expected_hash
        ):
            errors.append(f"{manifest_path}: source_file_manifest `{rel}` has invalid sha256")
        elif _sha256_file(path).lower() != expected_hash.lower():
            errors.append(
                f"{manifest_path}: source_file_manifest `{rel}` sha256 does not match source file"
            )


def _find_input_dir(path: Path) -> Path:
    if path.name == "input" and (path / "manifest.json").exists():
        return path
    if (path / "cloud" / "input" / "manifest.json").exists():
        return path / "cloud" / "input"
    if (path / "input" / "manifest.json").exists():
        return path / "input"
    return path


def _find_cloud_dir(path: Path) -> Path:
    if path.name == "cloud" and (path / "manifest.json").exists():
        return path
    if (path / "cloud" / "manifest.json").exists():
        return path / "cloud"
    return path


def validate_cloud_input(input_dir: Path) -> list[str]:
    """Validate a text-only cloud input package."""
    errors: list[str] = []
    input_dir = _find_input_dir(input_dir)
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"missing cloud input manifest: {manifest_path}"]
    manifest = read_json_file(manifest_path)
    if not isinstance(manifest, dict):
        return [f"{manifest_path}: manifest must be an object"]

    _validate_text_only_flags(manifest, manifest_path, errors)
    input_files = _manifest_file_list(manifest, "input_files")
    listed = _validate_path_list(
        base_dir=input_dir,
        manifest_path=manifest_path,
        paths=input_files,
        key="input_files",
        errors=errors,
    )
    for item in sorted(REQUIRED_CLOUD_INPUT_FILES - listed):
        errors.append(f"{manifest_path}: missing required input file `{item}`")

    for key in ("text_chunks", "prompt_templates"):
        nested_paths = _manifest_file_list(manifest, key)
        nested_listed = _validate_path_list(
            base_dir=input_dir,
            manifest_path=manifest_path,
            paths=nested_paths,
            key=key,
            errors=errors,
        )
        for item in sorted(nested_listed - listed):
            errors.append(
                f"{manifest_path}: `{key}` path `{item}` is not included in `input_files`"
            )

    actual_safe_files = {
        str(path.relative_to(input_dir))
        for path in input_dir.rglob("*")
        if path.is_file()
        and path.name not in LOCAL_ONLY_NAMES
        and _safe_relative_path(input_dir, str(path.relative_to(input_dir))) is not None
    }
    for item in sorted(actual_safe_files - listed):
        errors.append(f"{manifest_path}: file `{item}` exists but is not listed in `input_files`")

    _validate_input_file_manifest(
        base_dir=input_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        listed=listed,
        errors=errors,
    )
    _validate_source_file_manifest(
        input_dir=input_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        errors=errors,
    )

    segments_path = input_dir / "segments.for_cloud.json"
    if segments_path.exists():
        segments_payload = read_json_file(segments_path)
        segments = segments_payload.get("segments") if isinstance(segments_payload, dict) else None
        if not isinstance(segments, list):
            errors.append(f"{segments_path}: `segments` must be a list")
    return errors


def _cloud_output_json_object(
    cloud_dir: Path, listed: set[str], name: str, errors: list[str]
) -> dict[str, Any] | None:
    if name not in listed:
        return None
    path = cloud_dir / name
    payload = read_json_file(path)
    if not isinstance(payload, dict):
        errors.append(f"{path}: must be a JSON object")
        return None
    return payload


def _require_list(payload: dict[str, Any], path: Path, key: str, errors: list[str]) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        errors.append(f"{path}: `{key}` must be a list")
        return []
    return value


def _validate_cloud_output_schemas(cloud_dir: Path, listed: set[str], errors: list[str]) -> None:
    chapters_path = cloud_dir / "chapters.json"
    chapters_payload = _cloud_output_json_object(cloud_dir, listed, "chapters.json", errors)
    if chapters_payload is not None:
        for index, chapter in enumerate(
            _require_list(chapters_payload, chapters_path, "chapters", errors)
        ):
            if not isinstance(chapter, dict):
                errors.append(f"{chapters_path}: chapters[{index}] must be an object")
                continue
            for key in ("start", "end", "title", "summary"):
                if not isinstance(chapter.get(key), str) or not chapter.get(key):
                    errors.append(
                        f"{chapters_path}: chapters[{index}].{key} must be a non-empty string"
                    )
            for key in ("source_chunks", "source_segment_ids"):
                if not isinstance(chapter.get(key), list):
                    errors.append(f"{chapters_path}: chapters[{index}].{key} must be a list")

    terms_path = cloud_dir / "terms.json"
    terms_payload = _cloud_output_json_object(cloud_dir, listed, "terms.json", errors)
    if terms_payload is not None:
        for index, term in enumerate(_require_list(terms_payload, terms_path, "terms", errors)):
            if not isinstance(term, dict):
                errors.append(f"{terms_path}: terms[{index}] must be an object")
                continue
            if not isinstance(term.get("term"), str) or not term.get("term"):
                errors.append(f"{terms_path}: terms[{index}].term must be a non-empty string")

    titles_path = cloud_dir / "title_candidates.json"
    titles_payload = _cloud_output_json_object(cloud_dir, listed, "title_candidates.json", errors)
    if titles_payload is not None:
        for index, title in enumerate(
            _require_list(titles_payload, titles_path, "candidates", errors)
        ):
            if not isinstance(title, dict):
                errors.append(f"{titles_path}: candidates[{index}] must be an object")
                continue
            if not isinstance(title.get("title"), str) or not title.get("title"):
                errors.append(
                    f"{titles_path}: candidates[{index}].title must be a non-empty string"
                )

    glossary_path = cloud_dir / "glossary_suggestions.json"
    glossary_payload = _cloud_output_json_object(
        cloud_dir, listed, "glossary_suggestions.json", errors
    )
    if glossary_payload is not None:
        for key in ("suggestions", "needs_human_confirmation"):
            _require_list(glossary_payload, glossary_path, key, errors)

    glossary_editor_path = cloud_dir / "glossary_editor_items.json"
    glossary_editor_payload = _cloud_output_json_object(
        cloud_dir, listed, "glossary_editor_items.json", errors
    )
    if glossary_editor_payload is not None:
        for index, item in enumerate(
            _require_list(glossary_editor_payload, glossary_editor_path, "items", errors)
        ):
            if not isinstance(item, dict):
                errors.append(f"{glossary_editor_path}: items[{index}] must be an object")
                continue
            for key in ("term", "category", "scope", "action", "source", "last_used"):
                if not isinstance(item.get(key), str) or not item.get(key):
                    errors.append(
                        f"{glossary_editor_path}: items[{index}].{key} must be a non-empty string"
                    )
            if not isinstance(item.get("hit_count"), int):
                errors.append(
                    f"{glossary_editor_path}: items[{index}].hit_count must be an integer"
                )

    patches_path = cloud_dir / "transcript.polish_suggestions.json"
    patches_payload = _cloud_output_json_object(
        cloud_dir, listed, "transcript.polish_suggestions.json", errors
    )
    if patches_payload is not None:
        for index, patch in enumerate(
            _require_list(patches_payload, patches_path, "patches", errors)
        ):
            if not isinstance(patch, dict):
                errors.append(f"{patches_path}: patches[{index}] must be an object")
                continue
            for key in ("patch_id", "start", "end", "old_text", "new_text", "reason", "risk"):
                if not isinstance(patch.get(key), str) or not patch.get(key):
                    errors.append(
                        f"{patches_path}: patches[{index}].{key} must be a non-empty string"
                    )
            if "segment_id" in patch and not isinstance(patch.get("segment_id"), str):
                errors.append(f"{patches_path}: patches[{index}].segment_id must be a string")
            if not isinstance(patch.get("requires_audio_check"), bool):
                errors.append(
                    f"{patches_path}: patches[{index}].requires_audio_check must be boolean"
                )

    for item in sorted(
        path
        for path in listed
        if path.startswith("chunk_summaries/") and path.endswith(".summary.json")
    ):
        path = cloud_dir / item
        payload = read_json_file(path)
        if not isinstance(payload, dict):
            errors.append(f"{path}: must be a JSON object")
            continue
        for key in ("chunk", "summary", "start", "end", "source"):
            if key not in payload:
                errors.append(f"{path}: missing `{key}`")
        if not isinstance(payload.get("terms", []), list):
            errors.append(f"{path}: `terms` must be a list")
        if not isinstance(payload.get("uncertainties", []), list):
            errors.append(f"{path}: `uncertainties` must be a list")


def validate_cloud_outputs(cloud_dir: Path) -> list[str]:
    """Validate cloud output artifacts and manifest schema."""
    errors: list[str] = []
    cloud_dir = _find_cloud_dir(cloud_dir)
    manifest_path = cloud_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"missing cloud output manifest: {manifest_path}"]
    manifest = read_json_file(manifest_path)
    if not isinstance(manifest, dict):
        return [f"{manifest_path}: manifest must be an object"]

    _validate_text_only_flags(manifest, manifest_path, errors)
    output_files = _manifest_file_list(manifest, "output_files")
    listed = _validate_path_list(
        base_dir=cloud_dir,
        manifest_path=manifest_path,
        paths=output_files,
        key="output_files",
        errors=errors,
    )
    if "manifest.json" not in listed:
        errors.append(f"{manifest_path}: `output_files` must include `manifest.json`")
    for item in sorted(listed):
        if item.startswith("input/"):
            errors.append(
                f"{manifest_path}: output manifest must not list input package file `{item}`"
            )
    _validate_cloud_output_schemas(cloud_dir, listed, errors)
    return errors


def validate_cloud_package(path: Path, *, mode: str = "auto") -> list[str]:
    """Validate cloud input, cloud outputs, or both."""
    if mode == "input":
        return validate_cloud_input(path)
    if mode == "outputs":
        return validate_cloud_outputs(path)
    if mode == "both":
        return [*validate_cloud_input(path), *validate_cloud_outputs(path)]

    errors: list[str] = []
    input_manifest = _find_input_dir(path) / "manifest.json"
    output_manifest = _find_cloud_dir(path) / "manifest.json"
    if input_manifest.exists():
        errors.extend(validate_cloud_input(path))
    if output_manifest.exists() and output_manifest != input_manifest:
        errors.extend(validate_cloud_outputs(path))
    if not input_manifest.exists() and not output_manifest.exists():
        errors.append(f"missing cloud manifest under: {path}")
    return errors
