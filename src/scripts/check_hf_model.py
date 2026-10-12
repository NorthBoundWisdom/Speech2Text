#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import httpx
from huggingface_hub import HfApi, hf_hub_url, try_to_load_from_cache


DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
DEFAULT_PROBE_BYTES = 1024 * 1024
LOCAL_CACHE_MISS_RETURN_CODE = 4


@dataclass(frozen=True)
class FileEntry:
    name: str
    size: int | None


def _format_size(size: int | None) -> str:
    if size is None:
        return "unknown"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _file_entries(model_info) -> list[FileEntry]:
    entries: list[FileEntry] = []
    for sibling in getattr(model_info, "siblings", []) or []:
        name = getattr(sibling, "rfilename", None)
        if not name:
            continue
        size = getattr(sibling, "size", None)
        entries.append(FileEntry(name=name, size=size if isinstance(size, int) else None))
    return sorted(entries, key=lambda item: item.name)


def _find_file(entries: Sequence[FileEntry], filename: str) -> FileEntry | None:
    for entry in entries:
        if entry.name == filename:
            return entry
    return None


def _local_cache_path(
    *,
    repo_id: str,
    filename: str,
    revision: str,
    cache_dir: str | None,
) -> Path | None:
    cached = try_to_load_from_cache(repo_id, filename, revision=revision, cache_dir=cache_dir)
    if not isinstance(cached, str):
        return None
    path = Path(cached)
    return path if path.exists() else None


def _probe_file_range(
    *,
    repo_id: str,
    filename: str,
    revision: str,
    probe_bytes: int,
    timeout: float,
) -> tuple[int, float, int]:
    url = hf_hub_url(repo_id=repo_id, filename=filename, revision=revision)
    headers = {"Range": f"bytes=0-{max(probe_bytes - 1, 0)}"}
    started = time.perf_counter()
    bytes_read = 0
    with httpx.stream(
        "GET",
        url,
        headers=headers,
        follow_redirects=True,
        timeout=timeout,
        trust_env=True,
    ) as response:
        response.raise_for_status()
        status_code = response.status_code
        for chunk in response.iter_bytes():
            bytes_read += len(chunk)
            if bytes_read >= probe_bytes:
                break
    return status_code, time.perf_counter() - started, bytes_read


def _mb_per_second(bytes_read: int, elapsed: float) -> float:
    return bytes_read / elapsed / 1024 / 1024 if elapsed > 0 else 0.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check Hugging Face API access and optionally probe a model file download path. "
            "This distinguishes metadata connectivity from large-file download health."
        )
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model repo id to inspect.")
    parser.add_argument("--revision", default="main")
    parser.add_argument(
        "--filename",
        help="Optional model file to probe, for example weights.npz or model.safetensors.",
    )
    parser.add_argument(
        "--probe-bytes",
        type=int,
        default=DEFAULT_PROBE_BYTES,
        help="Bytes to read when --filename is provided.",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--local-cache-only",
        action="store_true",
        help="Check whether --filename is already present in the local Hugging Face cache without network access.",
    )
    parser.add_argument("--cache-dir", help="Optional Hugging Face cache directory override.")
    parser.add_argument(
        "--min-mb-s",
        type=float,
        default=0.0,
        help="Fail if the measured probe speed is below this MB/s threshold.",
    )
    parser.add_argument(
        "--disable-xet",
        action="store_true",
        help="Set HF_HUB_DISABLE_XET=1 for this process before probing.",
    )
    parser.add_argument("--max-files", type=int, default=40, help="Maximum file entries to print.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.disable_xet:
        os.environ["HF_HUB_DISABLE_XET"] = "1"

    if args.local_cache_only:
        if not args.filename:
            print("--local-cache-only requires --filename")
            return 2
        cached_path = _local_cache_path(
            repo_id=args.model,
            filename=args.filename,
            revision=args.revision,
            cache_dir=args.cache_dir,
        )
        if cached_path is None:
            print(f"Local cache: missing `{args.filename}` for {args.model}@{args.revision}")
            return LOCAL_CACHE_MISS_RETURN_CODE
        print(f"Local cache: ok {cached_path} ({_format_size(cached_path.stat().st_size)})")
        return 0

    api = HfApi()
    info = api.model_info(args.model, revision=args.revision, files_metadata=True)
    entries = _file_entries(info)
    print(f"Model: {info.modelId}")
    print(f"Revision: {args.revision}")
    print(f"Files: {len(entries)}")
    for entry in entries[: max(args.max_files, 0)]:
        print(f"- {entry.name} ({_format_size(entry.size)})")
    if len(entries) > args.max_files:
        print(f"... {len(entries) - args.max_files} more files")

    if not args.filename:
        print("API check: ok")
        return 0

    entry = _find_file(entries, args.filename)
    if entry is None:
        print(f"File probe: missing `{args.filename}` in model metadata")
        return 2

    print(f"File probe: {entry.name} ({_format_size(entry.size)})")
    try:
        status_code, elapsed, bytes_read = _probe_file_range(
            repo_id=args.model,
            filename=args.filename,
            revision=args.revision,
            probe_bytes=max(args.probe_bytes, 1),
            timeout=args.timeout,
        )
    except Exception as exc:
        print(f"Download probe: failed: {type(exc).__name__}: {exc}")
        return 1

    rate = _mb_per_second(bytes_read, elapsed)
    print(
        "Download probe: ok "
        f"(status={status_code}, bytes={bytes_read}, elapsed={elapsed:.2f}s, rate={rate:.2f} MB/s)"
    )
    if args.min_mb_s and rate < args.min_mb_s:
        print(f"Download probe: too slow (min={args.min_mb_s:.2f} MB/s, actual={rate:.2f} MB/s)")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
