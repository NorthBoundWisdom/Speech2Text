#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from huggingface_hub import try_to_load_from_cache

from atot.paths import TOOLS_DIR
from asr_candidate_presets import CandidatePreset, HfFileRequirement, LocalPathRequirement, presets


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def _format_status(ok: bool) -> str:
    return "ok" if ok else "missing"


def _check_executable(preset: CandidatePreset) -> CheckResult:
    path = Path(preset.executable)
    return CheckResult(
        name="executable",
        ok=path.exists() and os.access(path, os.X_OK),
        detail=str(path),
    )


def _check_doctor(preset: CandidatePreset, timeout: float) -> CheckResult:
    if not preset.doctor_command:
        return CheckResult(name="doctor", ok=True, detail="not required")
    env = os.environ.copy()
    env["PATH"] = f"{TOOLS_DIR / 'bin'}:{env.get('PATH', '')}"
    try:
        completed = subprocess.run(
            list(preset.doctor_command),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(name="doctor", ok=False, detail=f"{type(exc).__name__}: {exc}")
    detail = f"returncode={completed.returncode}"
    if completed.stderr.strip():
        detail += f", stderr={completed.stderr.strip().splitlines()[-1]}"
    return CheckResult(name="doctor", ok=completed.returncode == 0, detail=detail)


def _cache_path(requirement: HfFileRequirement, cache_dir: str | None) -> Path | None:
    cached = try_to_load_from_cache(
        requirement.model, requirement.filename, revision="main", cache_dir=cache_dir
    )
    if not isinstance(cached, str):
        return None
    path = Path(cached)
    return path if path.exists() else None


def _check_hf_file(requirement: HfFileRequirement, cache_dir: str | None) -> CheckResult:
    path = _cache_path(requirement, cache_dir)
    label = f"hf-cache:{requirement.model}/{requirement.filename}"
    if path is None:
        suffix = f" ({requirement.note})" if requirement.note else ""
        return CheckResult(name=label, ok=False, detail=f"not in local cache{suffix}")
    return CheckResult(name=label, ok=True, detail=str(path))


def _check_local_path(requirement: LocalPathRequirement) -> CheckResult:
    path = Path(requirement.path).expanduser()
    label = f"local-path:{path}"
    if path.exists():
        return CheckResult(name=label, ok=True, detail=requirement.note or str(path))
    suffix = f" ({requirement.note})" if requirement.note else ""
    return CheckResult(name=label, ok=False, detail=f"missing{suffix}")


def _probe_hf_file(
    requirement: HfFileRequirement,
    *,
    probe_bytes: int,
    timeout: float,
    min_mb_s: float,
    disable_xet: bool,
) -> CheckResult:
    script = Path(__file__).with_name("check_hf_model.py")
    command = [
        sys.executable,
        str(script),
        "--model",
        requirement.model,
        "--filename",
        requirement.filename,
        "--probe-bytes",
        str(probe_bytes),
        "--timeout",
        str(timeout),
        "--max-files",
        "0",
    ]
    if min_mb_s > 0:
        command.extend(["--min-mb-s", str(min_mb_s)])
    if disable_xet:
        command.append("--disable-xet")
    try:
        completed = subprocess.run(
            command, text=True, capture_output=True, check=False, timeout=timeout + 5
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(
            name=f"hf-probe:{requirement.model}/{requirement.filename}",
            ok=False,
            detail=f"{type(exc).__name__}: {exc}",
        )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    detail = lines[-1] if lines else f"returncode={completed.returncode}"
    if completed.stderr.strip():
        detail += f", stderr={completed.stderr.strip().splitlines()[-1]}"
    return CheckResult(
        name=f"hf-probe:{requirement.model}/{requirement.filename}",
        ok=completed.returncode == 0,
        detail=detail,
    )


def readiness_results(
    preset: CandidatePreset,
    *,
    cache_dir: str | None = None,
    doctor: bool = True,
    doctor_timeout: float = 30.0,
    probe_missing: bool = False,
    probe_bytes: int = 1024 * 1024,
    probe_timeout: float = 30.0,
    min_mb_s: float = 0.5,
    disable_xet: bool = True,
) -> list[CheckResult]:
    results = [_check_executable(preset)]
    if doctor:
        results.append(_check_doctor(preset, timeout=doctor_timeout))
    for requirement in preset.required_hf_files:
        cache_result = _check_hf_file(requirement, cache_dir)
        results.append(cache_result)
        if probe_missing and not cache_result.ok:
            results.append(
                _probe_hf_file(
                    requirement,
                    probe_bytes=probe_bytes,
                    timeout=probe_timeout,
                    min_mb_s=min_mb_s,
                    disable_xet=disable_xet,
                )
            )
    for requirement in preset.required_paths:
        results.append(_check_local_path(requirement))
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check whether an ASR candidate preset is ready to enter the gate."
    )
    parser.add_argument("--preset", required=True, choices=sorted(presets()))
    parser.add_argument("--cache-dir", help="Optional Hugging Face cache directory override.")
    parser.add_argument(
        "--skip-doctor", action="store_true", help="Skip preset doctor/check command."
    )
    parser.add_argument("--doctor-timeout", type=float, default=30.0)
    parser.add_argument(
        "--probe-missing",
        action="store_true",
        help="For missing HF cache files, run a small range-download probe. Cache misses still fail readiness.",
    )
    parser.add_argument("--probe-bytes", type=int, default=1024 * 1024)
    parser.add_argument("--probe-timeout", type=float, default=30.0)
    parser.add_argument("--min-mb-s", type=float, default=0.5)
    parser.add_argument(
        "--allow-xet", action="store_true", help="Do not pass --disable-xet to HF probes."
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    preset = presets()[args.preset]
    results = readiness_results(
        preset,
        cache_dir=args.cache_dir,
        doctor=not args.skip_doctor,
        doctor_timeout=args.doctor_timeout,
        probe_missing=args.probe_missing,
        probe_bytes=args.probe_bytes,
        probe_timeout=args.probe_timeout,
        min_mb_s=args.min_mb_s,
        disable_xet=not args.allow_xet,
    )
    print(f"Preset: {preset.name}")
    for result in results:
        print(f"- {result.name}: {_format_status(result.ok)} ({result.detail})")
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
