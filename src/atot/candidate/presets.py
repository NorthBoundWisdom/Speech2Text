from __future__ import annotations

import argparse
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from atot.models import model_entry, required_local_files
from atot.paths import ENV_DIR, MODEL_DIR, TOOLS_DIR


DEFAULT_TIMEOUT_SECONDS = 1800


@dataclass(frozen=True)
class HfFileRequirement:
    model: str
    filename: str
    note: str = ""


@dataclass(frozen=True)
class LocalPathRequirement:
    path: str
    note: str = ""


@dataclass(frozen=True)
class CandidatePreset:
    """Runnable ASR candidate definition used by comparison and gate tools.

    Attributes:
        name: Stable preset identifier shown in CLI output.
        command: Shell command template. It may contain ``{audio}`` and
            ``{context}`` placeholders filled by candidate runners.
        note: Human-readable summary of what the preset exercises.
        executable: Primary executable expected by readiness checks.
        doctor_command: Optional command used to verify backend readiness.
        required_hf_files: Hugging Face files that must be available.
        required_paths: Local files or directories that must be available.
    """

    name: str
    command: str
    note: str
    executable: str
    doctor_command: tuple[str, ...] = ()
    required_hf_files: tuple[HfFileRequirement, ...] = ()
    required_paths: tuple[LocalPathRequirement, ...] = ()


def _tool_path(*parts: str) -> str:
    parts_path = Path(*parts)
    if parts_path.parts and parts_path.parts[0] == ".tools":
        return str(TOOLS_DIR / Path(*parts_path.parts[1:]))
    return parts_path.as_posix()


def _isolated_path_env() -> str:
    entries = [
        str(TOOLS_DIR / "bin"),
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ]
    return ":".join(entries)


def _local_model_dir(model_name: str) -> str:
    entry = model_entry(model_name)
    local_dir = entry.local_dir if entry is not None else model_name
    return str(MODEL_DIR / local_dir)


def _model_file_requirement(model_name: str, filename: str, note: str) -> LocalPathRequirement:
    for path in required_local_files(model_name):
        if Path(path).name == filename:
            relative = Path(path)
            if relative.parts and relative.parts[0] == "model":
                return LocalPathRequirement(
                    path=str(MODEL_DIR / Path(*relative.parts[1:])), note=note
                )
            return LocalPathRequirement(path=path, note=note)
    return LocalPathRequirement(path=str(Path(_local_model_dir(model_name)) / filename), note=note)


def _model_file_requirements(
    model_name: str, filenames: Sequence[str], note: str
) -> tuple[LocalPathRequirement, ...]:
    return tuple(_model_file_requirement(model_name, filename, note) for filename in filenames)


def _local_mlx_whisper_preset(
    *,
    name: str,
    model_dir: str,
    note: str,
    weight_filename: str,
    condition_on_previous_text: bool = True,
    word_timestamps: bool = False,
    temperature: float = 0.0,
    no_speech_threshold: float | None = 0.6,
    logprob_threshold: float | None = -1.0,
    compression_ratio_threshold: float | None = 2.4,
    hallucination_silence_threshold: float | None = None,
) -> CandidatePreset:
    path_env = _isolated_path_env()
    decode_flags = [
        "--condition-on-previous-text"
        if condition_on_previous_text
        else "--no-condition-on-previous-text",
        "--temperature",
        str(temperature),
        "--no-speech-threshold",
        "none" if no_speech_threshold is None else str(no_speech_threshold),
        "--logprob-threshold",
        "none" if logprob_threshold is None else str(logprob_threshold),
        "--compression-ratio-threshold",
        "none" if compression_ratio_threshold is None else str(compression_ratio_threshold),
        "--hallucination-silence-threshold",
        "none" if hallucination_silence_threshold is None else str(hallucination_silence_threshold),
    ]
    if word_timestamps:
        decode_flags.append("--word-timestamps")
    return CandidatePreset(
        name=name,
        command=(
            "env HF_HUB_DISABLE_XET=1 "
            f"PATH={shlex.quote(path_env)} "
            f"{shlex.quote(str(ENV_DIR / 'bin' / 'python'))} "
            f"{shlex.quote(_tool_path('src', 'scripts', 'mlx_whisper_candidate.py'))} "
            f"--model {shlex.quote(model_dir)} "
            "--language zh "
            "--context {context} " + " ".join(shlex.quote(flag) for flag in decode_flags) + " "
            "--stdout-only "
            "{audio}"
        ),
        note=note,
        executable=str(ENV_DIR / "bin" / "python"),
        required_paths=(
            _model_file_requirement(Path(model_dir).name, "config.json", "local model config"),
            _model_file_requirement(Path(model_dir).name, weight_filename, "local MLX weights"),
            LocalPathRequirement(
                path=str(TOOLS_DIR / "bin" / "ffmpeg"),
                note="required for non-WAV candidate inputs",
            ),
        ),
    )


def presets() -> dict[str, CandidatePreset]:
    path_env = _isolated_path_env()
    return {
        "mlx-qwen3-asr-0.6b": CandidatePreset(
            name="mlx-qwen3-asr-0.6b",
            command=(
                "env HF_HUB_DISABLE_XET=1 "
                f"PATH={shlex.quote(path_env)} "
                f"{shlex.quote(_tool_path('.tools', 'mlx-qwen3-asr-venv', 'bin', 'mlx-qwen3-asr'))} "
                f"--model {shlex.quote(_local_model_dir('Qwen3-ASR-0.6B'))} "
                "--language Chinese "
                "--context {glossary_terms} "
                "--output-format json "
                "--timestamps "
                f"--forced-aligner {shlex.quote(_local_model_dir('Qwen3-ForcedAligner-0.6B'))} "
                "--stdout-only "
                "{audio}"
            ),
            note="Requires Qwen3-ASR-0.6B and Qwen3-ForcedAligner-0.6B under the local model directory.",
            executable=_tool_path(".tools", "mlx-qwen3-asr-venv", "bin", "mlx-qwen3-asr"),
            doctor_command=(
                _tool_path(".tools", "mlx-qwen3-asr-venv", "bin", "mlx-qwen3-asr"),
                "--doctor",
            ),
            required_paths=(
                *_model_file_requirements(
                    "mlx-qwen3-asr-0.6b",
                    (
                        "config.json",
                        "merges.txt",
                        "model.safetensors",
                        "tokenizer_config.json",
                        "vocab.json",
                    ),
                    "main ASR model files",
                ),
                *_model_file_requirements(
                    "qwen3-forced-aligner-0.6b",
                    (
                        "config.json",
                        "merges.txt",
                        "model.safetensors",
                        "tokenizer_config.json",
                        "vocab.json",
                    ),
                    "forced aligner files required by --timestamps",
                ),
            ),
        ),
        "whisperlivekit-mlx": CandidatePreset(
            name="whisperlivekit-mlx",
            command=(
                "env HF_HUB_DISABLE_XET=1 "
                f"PATH={shlex.quote(path_env)} "
                f"{shlex.quote(_tool_path('.tools', 'whisperlivekit-venv', 'bin', 'wlk'))} "
                "transcribe "
                "--backend mlx-whisper "
                f"--model {shlex.quote(_local_model_dir('whisper-large-v3-turbo'))} "
                "--language zh "
                "--format json "
                "--output {output} "
                "{audio}"
            ),
            note="Uses WhisperLiveKit offline JSON output so Audio2Text can evaluate segments and timestamps.",
            executable=_tool_path(".tools", "whisperlivekit-venv", "bin", "wlk"),
            doctor_command=(_tool_path(".tools", "whisperlivekit-venv", "bin", "wlk"), "check"),
            required_paths=(
                _model_file_requirement(
                    "large-v3-turbo",
                    "config.json",
                    "WhisperLiveKit mlx-whisper large-v3-turbo config",
                ),
                _model_file_requirement(
                    "large-v3-turbo",
                    "weights.safetensors",
                    "WhisperLiveKit mlx-whisper large-v3-turbo weights",
                ),
            ),
        ),
        "mlx-whisper-local-large-v3-turbo": _local_mlx_whisper_preset(
            name="mlx-whisper-local-large-v3-turbo",
            model_dir=_local_model_dir("whisper-large-v3-turbo"),
            note="Uses the local whisper-large-v3-turbo MLX model directory.",
            weight_filename="weights.safetensors",
        ),
        "mlx-whisper-local-large-v3": _local_mlx_whisper_preset(
            name="mlx-whisper-local-large-v3",
            model_dir=_local_model_dir("whisper-large-v3-mlx"),
            note="Uses the local whisper-large-v3-mlx model directory.",
            weight_filename="weights.npz",
        ),
        "mlx-whisper-local-large-v3-4bit": _local_mlx_whisper_preset(
            name="mlx-whisper-local-large-v3-4bit",
            model_dir=_local_model_dir("whisper-large-v3-mlx-4bit"),
            note="Uses the local whisper-large-v3-mlx-4bit model directory.",
            weight_filename="weights.npz",
        ),
        "mlx-whisper-local-large-v3-turbo-no-prev": _local_mlx_whisper_preset(
            name="mlx-whisper-local-large-v3-turbo-no-prev",
            model_dir=_local_model_dir("whisper-large-v3-turbo"),
            note="Turbo variant with previous-text conditioning disabled to reduce runaway repetitions.",
            weight_filename="weights.safetensors",
            condition_on_previous_text=False,
        ),
        "mlx-whisper-local-large-v3-turbo-anti-repeat": _local_mlx_whisper_preset(
            name="mlx-whisper-local-large-v3-turbo-anti-repeat",
            model_dir=_local_model_dir("whisper-large-v3-turbo"),
            note="Turbo anti-repeat profile matching atot anti_repeat_zh_podcast decode thresholds.",
            weight_filename="weights.safetensors",
            condition_on_previous_text=False,
            no_speech_threshold=0.55,
            logprob_threshold=-0.9,
            compression_ratio_threshold=2.2,
        ),
        "mlx-whisper-local-large-v3-turbo-conservative": _local_mlx_whisper_preset(
            name="mlx-whisper-local-large-v3-turbo-conservative",
            model_dir=_local_model_dir("whisper-large-v3-turbo"),
            note="Turbo variant with conservative decode thresholds for hallucination-sensitive long audio.",
            weight_filename="weights.safetensors",
            condition_on_previous_text=False,
            no_speech_threshold=0.45,
            logprob_threshold=-0.8,
            compression_ratio_threshold=2.0,
            hallucination_silence_threshold=1.0,
            word_timestamps=True,
        ),
        "mlx-whisper-local-large-v3-turbo-repair-strict": _local_mlx_whisper_preset(
            name="mlx-whisper-local-large-v3-turbo-repair-strict",
            model_dir=_local_model_dir("whisper-large-v3-turbo"),
            note="Turbo repair_strict profile for repair-window and high-risk segment experiments.",
            weight_filename="weights.safetensors",
            condition_on_previous_text=False,
            no_speech_threshold=0.45,
            logprob_threshold=-0.8,
            compression_ratio_threshold=2.0,
            hallucination_silence_threshold=1.0,
            word_timestamps=True,
        ),
        "mlx-whisper-local-large-v3-no-prev": _local_mlx_whisper_preset(
            name="mlx-whisper-local-large-v3-no-prev",
            model_dir=_local_model_dir("whisper-large-v3-mlx"),
            note="Large-v3 variant with previous-text conditioning disabled.",
            weight_filename="weights.npz",
            condition_on_previous_text=False,
        ),
        "mlx-whisper-local-large-v3-4bit-no-prev": _local_mlx_whisper_preset(
            name="mlx-whisper-local-large-v3-4bit-no-prev",
            model_dir=_local_model_dir("whisper-large-v3-mlx-4bit"),
            note="4bit large-v3 variant with previous-text conditioning disabled.",
            weight_filename="weights.npz",
            condition_on_previous_text=False,
        ),
    }


def local_preset_names() -> list[str]:
    return sorted(name for name in presets() if name.startswith("mlx-whisper-local-"))


def _compare_command(preset: CandidatePreset, audio: Path, timeout: int) -> str:
    parts = [
        str(ENV_DIR / "bin" / "python"),
        "src/scripts/compare_asr_candidate.py",
        str(audio),
        "--preset",
        preset.name,
        "--candidate-timeout",
        str(timeout),
    ]
    return " ".join(shlex.quote(part) for part in parts)


def _gate_command(preset: CandidatePreset, timeout: int) -> str:
    parts = [
        str(ENV_DIR / "bin" / "python"),
        "src/scripts/asr_candidate_gate.py",
        "--preset",
        preset.name,
        "--candidate-timeout",
        str(timeout),
        "--strict",
    ]
    return " ".join(shlex.quote(part) for part in parts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print vetted ASR candidate command presets for Audio2Text gates."
    )
    parser.add_argument("--list", action="store_true", help="List preset names and exit.")
    parser.add_argument("--preset", choices=sorted(presets()), help="Preset to print.")
    parser.add_argument(
        "--mode",
        choices=("candidate-command", "compare", "gate"),
        default="candidate-command",
        help="Print only the candidate command template, a compare command, or a three-audio gate command.",
    )
    parser.add_argument(
        "--audio", type=Path, default=None, help="Audio path required for --mode compare."
    )
    parser.add_argument("--candidate-timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    all_presets = presets()
    if args.list:
        for item in all_presets.values():
            print(f"{item.name}\t{item.note}")
        return 0
    if not args.preset:
        raise SystemExit("--preset is required unless --list is used")
    preset = all_presets[args.preset]
    if args.mode == "candidate-command":
        print(preset.command)
    elif args.mode == "compare":
        if args.audio is None:
            raise SystemExit("--audio is required for --mode compare")
        print(_compare_command(preset, args.audio, args.candidate_timeout))
    else:
        print(_gate_command(preset, args.candidate_timeout))
    return 0
