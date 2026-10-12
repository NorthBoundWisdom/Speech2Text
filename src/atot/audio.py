from __future__ import annotations

import shutil
import subprocess
import sys
import wave
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any

from .paths import TOOLS_DIR
from .utils import ensure_dir


@dataclass(frozen=True)
class ChunkSpec:
    index: int
    path: Path
    source_start: float
    source_end: float
    core_start: float
    core_end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.source_end - self.source_start)

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        payload["duration"] = self.duration
        return payload


class AudioError(RuntimeError):
    pass


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


def require_command(name: str) -> str:
    candidates = list(_command_candidates(name))
    path = next((p for p in candidates if p and Path(p).exists()), None)
    if path is None:
        raise AudioError(
            f"Missing command: {name}. Install ffmpeg and ensure {name} is on PATH "
            "or available under the data-root tools directory."
        )
    return path


def _command_candidates(name: str) -> list[str | None]:
    names = [name]
    if os.name == "nt" and not name.lower().endswith(".exe"):
        names.append(f"{name}.exe")
    roots = [
        Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin"),
        TOOLS_DIR / "bin",
        TOOLS_DIR / "ffmpeg" / "bin",
        Path(__file__).resolve().parents[2] / ".tools" / "bin",
        Path(__file__).resolve().parents[2] / ".tools" / "ffmpeg" / "bin",
    ]
    vcpkg_root = os.environ.get("VCPKG_ROOT")
    if vcpkg_root:
        roots.append(Path(vcpkg_root) / "installed" / "x64-windows" / "tools" / "ffmpeg")

    candidates: list[str | None] = []
    for command_name in names:
        candidates.append(shutil.which(command_name))
    for root in roots:
        for command_name in names:
            candidates.append(str(root / command_name))
    return candidates


def optional_command(name: str) -> str | None:
    try:
        return require_command(name)
    except AudioError:
        return shutil.which(name)


def run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(args, check=False, text=True, capture_output=True)
    except OSError as exc:
        command = " ".join(args[:2]) if args else "<empty command>"
        raise AudioError(f"Could not run command `{command}`: {exc}") from exc
    if check and result.returncode != 0:
        command = args[0] if args else "<empty command>"
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        detail = stderr or stdout or f"exit code {result.returncode}"
        raise AudioError(f"{command} failed with exit code {result.returncode}: {detail}")
    return result


def prepare_audio_command(
    input_path: str | Path,
    output_path: str | Path,
    *,
    sample_rate: int = 16_000,
) -> dict[str, Any]:
    src = Path(input_path).expanduser()
    dst = Path(output_path)
    ffmpeg = optional_command("ffmpeg")
    if ffmpeg is not None:
        args = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(dst),
        ]
        return {"tool": "ffmpeg", "available": True, "args": args}

    if src.suffix.lower() in VIDEO_EXTENSIONS:
        return {
            "tool": "ffmpeg",
            "available": False,
            "args": [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(src),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-c:a",
                "pcm_s16le",
                str(dst),
            ],
        }

    afconvert = shutil.which("afconvert")
    args = [
        afconvert or "afconvert",
        "-f",
        "WAVE",
        "-d",
        f"LEI16@{sample_rate}",
        "-c",
        "1",
        str(src),
        str(dst),
    ]
    return {"tool": "afconvert", "available": afconvert is not None, "args": args}


def wav_duration(path: str | Path) -> float:
    try:
        with wave.open(str(path), "rb") as wav:
            rate = wav.getframerate()
            if rate <= 0:
                raise AudioError(f"Could not read WAV sample rate: {path}")
            return wav.getnframes() / rate
    except wave.Error as exc:
        raise AudioError(f"Could not read WAV duration: {path}") from exc


def ffprobe_duration(path: str | Path) -> float:
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise AudioError(f"Audio file does not exist: {p}")
    ffprobe = optional_command("ffprobe")
    if ffprobe is None and p.suffix.lower() == ".wav":
        return wav_duration(p)
    if ffprobe is None:
        afinfo = shutil.which("afinfo")
        if afinfo is None:
            raise AudioError("Missing ffprobe. Install ffmpeg, or provide a WAV file on macOS.")
        result = run_command([afinfo, str(p)], check=False)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                marker = "estimated duration:"
                if marker in line:
                    value = line.split(marker, 1)[1].split("sec", 1)[0].strip()
                    try:
                        return float(value)
                    except ValueError:
                        break
        raise AudioError(
            f"Could not read audio duration from afinfo output:\n{result.stdout}\n{result.stderr}"
        )
    result = run_command(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(p),
        ],
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise AudioError(f"Could not read audio duration with ffprobe: {detail}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise AudioError(
            f"Could not read audio duration from ffprobe output: {result.stdout!r}"
        ) from exc


def probe_media(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser()
    ffprobe = optional_command("ffprobe")
    if ffprobe is None:
        return {"available": False, "path": str(p), "error": "ffprobe is unavailable"}
    result = run_command(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(p),
        ],
        check=False,
    )
    if result.returncode != 0:
        return {"available": True, "path": str(p), "error": result.stderr.strip()}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AudioError(f"Could not parse ffprobe media metadata: {exc}") from exc
    return normalize_media_probe(payload, path=p)


def normalize_media_probe(payload: dict[str, Any], *, path: Path | None = None) -> dict[str, Any]:
    streams = payload.get("streams", []) if isinstance(payload.get("streams"), list) else []
    format_payload = payload.get("format", {}) if isinstance(payload.get("format"), dict) else {}
    audio_streams: list[dict[str, Any]] = []
    video_streams: list[dict[str, Any]] = []
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        kind = str(stream.get("codec_type") or "")
        item = {
            "index": stream.get("index"),
            "codec": stream.get("codec_name"),
            "sample_rate": stream.get("sample_rate"),
            "channels": stream.get("channels"),
            "duration": stream.get("duration"),
        }
        if kind == "audio":
            audio_streams.append(item)
        elif kind == "video":
            video_streams.append(
                {
                    "index": stream.get("index"),
                    "codec": stream.get("codec_name"),
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "duration": stream.get("duration"),
                }
            )
    selected = audio_streams[0] if audio_streams else {}
    return {
        "available": True,
        "path": str(path) if path is not None else "",
        "container": format_payload.get("format_name"),
        "duration": format_payload.get("duration"),
        "audio_streams": audio_streams,
        "video_streams": video_streams,
        "selected_audio_stream": selected.get("index"),
        "audio_codec": selected.get("codec"),
        "sample_rate": selected.get("sample_rate"),
        "channels": selected.get("channels"),
    }


def prepare_audio(
    input_path: str | Path,
    output_path: str | Path,
    *,
    sample_rate: int = 16_000,
    overwrite: bool = False,
) -> Path:
    """Prepare a mono WAV file for transcription.

    Args:
        input_path: Source audio or video file accepted by ffmpeg or afconvert.
        output_path: Destination WAV path.
        sample_rate: Target sample rate in Hz.
        overwrite: Whether to replace an existing destination file.

    Returns:
        The prepared WAV path.

    Raises:
        AudioError: If the input is missing, the output path is invalid, no
            conversion tool is available, or conversion fails.
    """

    src = Path(input_path).expanduser()
    dst = Path(output_path)
    if sample_rate <= 0:
        raise AudioError("Sample rate must be positive.")
    if not src.exists() or not src.is_file():
        raise AudioError(f"Input audio does not exist: {src}")
    if dst.exists() and dst.is_dir():
        raise AudioError(f"Output audio path is a directory: {dst}")
    if dst.exists() and not overwrite:
        return dst
    ensure_dir(dst.parent)
    command = prepare_audio_command(src, dst, sample_rate=sample_rate)
    if not command["available"]:
        if src.suffix.lower() in VIDEO_EXTENSIONS:
            raise AudioError(
                "Video input requires ffmpeg. Install ffmpeg and ensure it is on PATH."
            )
        raise AudioError("Missing ffmpeg or afconvert. Install ffmpeg and ensure it is on PATH.")
    args = [str(item) for item in command["args"]]
    result = run_command(args, check=False)
    if result.returncode != 0:
        raise AudioError(f"{command['tool']} failed preparing audio:\n{result.stderr}")
    return dst


def write_wav_chunk(src: Path, dst: Path, start: float, duration: float) -> None:
    with wave.open(str(src), "rb") as wav:
        params = wav.getparams()
        rate = wav.getframerate()
        start_frame = max(0, int(round(start * rate)))
        frame_count = max(1, int(round(duration * rate)))
        wav.setpos(min(start_frame, wav.getnframes()))
        frames = wav.readframes(frame_count)
    ensure_dir(dst.parent)
    with wave.open(str(dst), "wb") as out:
        out.setparams(params)
        out.writeframes(frames)


def compute_chunks(
    duration: float,
    *,
    chunks_dir: str | Path,
    chunk_length: float = 20 * 60,
    overlap: float = 10,
) -> list[ChunkSpec]:
    if duration <= 0:
        raise AudioError("Audio duration must be positive.")
    if chunk_length <= 0:
        chunk_length = duration
    if overlap < 0:
        raise AudioError("Overlap must be non-negative.")
    if overlap * 2 >= chunk_length:
        raise AudioError("Overlap is too large. Use overlap < chunk_length / 2.")

    out_dir = Path(chunks_dir)
    specs: list[ChunkSpec] = []
    index = 0
    core_start = 0.0
    while core_start < duration:
        core_end = min(duration, core_start + chunk_length)
        source_start = max(0.0, core_start - (overlap if core_start > 0 else 0.0))
        source_end = min(duration, core_end + (overlap if core_end < duration else 0.0))
        specs.append(
            ChunkSpec(
                index=index,
                path=out_dir / f"chunk_{index:04d}.wav",
                source_start=source_start,
                source_end=source_end,
                core_start=core_start,
                core_end=core_end,
            )
        )
        index += 1
        if core_end >= duration:
            break
        core_start = core_end
    return specs


def materialize_chunks(
    prepared_wav: str | Path,
    chunks_dir: str | Path,
    *,
    chunk_length: float = 20 * 60,
    overlap: float = 10,
    overwrite: bool = False,
    duration: float | None = None,
) -> list[ChunkSpec]:
    ffmpeg = optional_command("ffmpeg")
    src = Path(prepared_wav)
    if duration is None:
        duration = ffprobe_duration(src)
    out_dir = ensure_dir(chunks_dir)
    specs = compute_chunks(duration, chunks_dir=out_dir, chunk_length=chunk_length, overlap=overlap)
    for spec in specs:
        if spec.path.exists() and not overwrite:
            continue
        length = max(0.01, spec.source_end - spec.source_start)
        if ffmpeg is None:
            write_wav_chunk(src, spec.path, spec.source_start, length)
            continue
        args = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{spec.source_start:.3f}",
            "-t",
            f"{length:.3f}",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(spec.path),
        ]
        result = run_command(args, check=False)
        if result.returncode != 0:
            raise AudioError(f"ffmpeg failed creating chunk {spec.index}:\n{result.stderr}")
    return specs


def materialize_chunk_specs(
    prepared_wav: str | Path, specs: list[ChunkSpec], *, overwrite: bool = False
) -> list[ChunkSpec]:
    ffmpeg = optional_command("ffmpeg")
    src = Path(prepared_wav)
    for spec in specs:
        if spec.path.exists() and not overwrite:
            continue
        length = max(0.01, spec.source_end - spec.source_start)
        if ffmpeg is None:
            write_wav_chunk(src, spec.path, spec.source_start, length)
            continue
        ensure_dir(spec.path.parent)
        args = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{spec.source_start:.3f}",
            "-t",
            f"{length:.3f}",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(spec.path),
        ]
        result = run_command(args, check=False)
        if result.returncode != 0:
            raise AudioError(f"ffmpeg failed creating chunk {spec.index}:\n{result.stderr}")
    return specs
