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
    return lowered


def language_help_epilog() -> str:
    lines = [
        "Language hints for --language:",
        "  Default: auto. Repeat --language for mixed-language hints.",
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


def normalize_languages(values: list[str] | tuple[str, ...]) -> list[str]:
    """Canonical requested codes; an explicit auto selection clears all hints."""
    if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) for v in values):
        raise ValueError("languages must be an array of language codes.")
    normalized = [normalize_language_hint(v) for v in values]
    if None in normalized:
        return []
    codes = list(dict.fromkeys(normalized))
    allowed = {code for code, _ in COMMON_LANGUAGE_HINTS}
    if any(code not in allowed for code in codes):
        raise ValueError(
            "Unsupported language code. Use a code from the language settings catalog."
        )
    return [str(code) for code in codes]


def resolve_languages(values: list[str] | tuple[str, ...]) -> tuple[str | None, list[str]]:
    codes = normalize_languages(values)
    return (codes[0] if len(codes) == 1 else None), codes


def summary_language(value: str) -> str:
    codes = normalize_languages([value])
    if not codes:
        raise ValueError("Summary output requires a specific language, not auto.")
    return codes[0]


def language_label(code: str) -> str:
    return dict(COMMON_LANGUAGE_HINTS)[summary_language(code)]


def output_language_instruction(code: str) -> str:
    return (
        f"Output language: {language_label(code)} ({code}). "
        "This output-language setting overrides conflicting language requirements in the preceding prompt. "
        "Write all generated prose, headings, and titles in this language; preserve proper names, "
        "verbatim quotations, timestamps, and required JSON field names. "
        "Follow all other content and formatting requirements."
    )


def mixed_language_context(codes: list[str] | tuple[str, ...]) -> str:
    if len(codes) < 2:
        return ""
    return (
        "Expected spoken languages: "
        + ", ".join(language_label(code) for code in codes)
        + ". Transcribe each spoken language as spoken."
    )
