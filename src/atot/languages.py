from __future__ import annotations

COMMON_LANGUAGE_HINTS = (
    ("zh", "Chinese / Mandarin"),
    ("en", "English"),
    ("ja", "Japanese; jp is accepted as an alias"),
    ("ko", "Korean"),
    ("yue", "Cantonese"),
    ("de", "German"),
    ("fr", "French"),
    ("es", "Spanish"),
    ("ru", "Russian"),
    ("pt", "Portuguese"),
    ("it", "Italian"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("vi", "Vietnamese"),
    ("th", "Thai"),
    ("id", "Indonesian"),
)

LANGUAGE_ALIASES = {
    "auto": None,
    "detect": None,
    "jp": "ja",
    "cn": "zh",
    "mandarin": "zh",
    "chinese": "zh",
    "japanese": "ja",
    "english": "en",
    "korean": "ko",
    "cantonese": "yue",
}


def normalize_language_hint(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    lowered = stripped.lower()
    if lowered in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[lowered]
    return stripped


def language_help_epilog() -> str:
    lines = [
        "Language hints for --language:",
        "  Default: zh. Use auto to let ASR detect the language.",
        "  Common codes:",
    ]
    lines.extend(f"    {code:<4} {label}" for code, label in COMMON_LANGUAGE_HINTS)
    lines.extend(
        [
            "  Examples:",
            "    Audio2TextCli exec transcribe path/to/audio.m4a --language ja",
            "    Audio2TextCli exec srt path/to/video.mp4 --language zh --language en",
            "    Audio2TextCli exec srt path/to/video.mp4 --language auto",
        ]
    )
    return "\n".join(lines)
