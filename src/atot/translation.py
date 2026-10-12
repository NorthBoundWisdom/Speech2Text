from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import time
from typing import Any

from .cloud.client import CloudClientOptions, call_openai_compatible_chat, resolve_cloud_options
from .models import local_model_dir, required_local_files
from .paths import path_context
from .subtitles import SubtitleCue, split_subtitle_text
from .utils import compact_ws


DEFAULT_TRANSLATION_MODEL_ALIAS = "nllb-200-distilled-600m"
DEFAULT_TRANSLATION_MODEL_REPO = "facebook/nllb-200-distilled-600M"

TARGET_LANGUAGE_ALIASES = {
    "zh": "zh",
    "zh-cn": "zh",
    "zh_hans": "zh",
    "zho_hans": "zh",
    "chinese": "zh",
}

NLLB_LANGUAGE_CODES = {
    "ar": "arb_Arab",
    "de": "deu_Latn",
    "en": "eng_Latn",
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "hi": "hin_Deva",
    "id": "ind_Latn",
    "it": "ita_Latn",
    "ja": "jpn_Jpan",
    "jp": "jpn_Jpan",
    "ko": "kor_Hang",
    "pt": "por_Latn",
    "ru": "rus_Cyrl",
    "th": "tha_Thai",
    "vi": "vie_Latn",
    "zh": "zho_Hans",
}


@dataclass(frozen=True)
class SubtitleTranslation:
    cues: list[SubtitleCue]
    metadata: dict[str, Any]


def normalize_target_language(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().lower()
    if not stripped:
        return None
    if stripped in TARGET_LANGUAGE_ALIASES:
        return TARGET_LANGUAGE_ALIASES[stripped]
    raise ValueError(f"Unsupported target language: {value}. Currently supported: zh.")


def nllb_language_code(language: str | None) -> str:
    key = (language or "").strip().lower()
    if key in NLLB_LANGUAGE_CODES:
        return NLLB_LANGUAGE_CODES[key]
    raise ValueError(
        f"Unsupported translation source language: {language or 'unknown'}. "
        "Pass a supported --language value or use ASR auto-detection when available."
    )


def translation_model_dir(model_alias: str = DEFAULT_TRANSLATION_MODEL_ALIAS) -> Path:
    return local_model_dir(model_alias)


def missing_translation_model_files(
    model_alias: str = DEFAULT_TRANSLATION_MODEL_ALIAS,
) -> list[Path]:
    root = path_context().data_root
    return [root / item for item in required_local_files(model_alias) if not (root / item).exists()]


def translation_model_download_command(model_alias: str = DEFAULT_TRANSLATION_MODEL_ALIAS) -> str:
    model_dir = translation_model_dir(model_alias)
    repo = DEFAULT_TRANSLATION_MODEL_REPO
    return f'hf download {repo} --local-dir "~/Documents/SpeechToTextData/model/{model_dir.name}"'


def wrap_translated_text(text: str, *, max_line_chars: int = 42) -> str:
    chunks = split_subtitle_text(text, max_chars=max_line_chars)
    return "\n".join(chunks) if chunks else compact_ws(text)


def normalize_translated_zh_text(text: str) -> str:
    normalized = compact_ws(text)
    normalized = (
        normalized.replace(",", "，")
        .replace(";", "；")
        .replace(":", "：")
        .replace("?", "？")
        .replace("!", "！")
    )
    normalized = re.sub(r"(?<!\d)\.(?!\d)", "。", normalized)
    normalized = normalized.lstrip("，。！？；：、,.!?;: ")
    normalized = _collapse_repeated_units(normalized)
    normalized = normalized.rstrip("，、 ")
    return compact_ws(normalized)


def apply_source_aware_zh_fixes(source_text: str, translated_text: str) -> str:
    source = source_text.lower()
    fixed = translated_text
    if re.search(r"\bmedium\b", source) and "中文" in fixed:
        fixed = (
            fixed.replace("一个中文", "一名灵媒")
            .replace("成为中文", "成为灵媒")
            .replace("中文", "灵媒")
        )
    return fixed


def _collapse_repeated_units(text: str, *, max_repeats: int = 2) -> str:
    pattern = re.compile(r"((?:[\u4e00-\u9fffA-Za-z0-9]{1,12})(?:[，、]\s*)?)(?:\1){2,}")
    previous = None
    current = text
    while previous != current:
        previous = current
        current = pattern.sub(lambda match: match.group(1) * max_repeats, current)
    return current


def translate_subtitle_cues(
    cues: list[SubtitleCue],
    *,
    source_language: str,
    target_language: str,
    model_alias: str = DEFAULT_TRANSLATION_MODEL_ALIAS,
    batch_size: int = 16,
    max_line_chars: int = 42,
) -> SubtitleTranslation:
    target_language = normalize_target_language(target_language) or "zh"
    if target_language != "zh":
        raise ValueError(
            f"Unsupported target language: {target_language}. Currently supported: zh."
        )
    source_code = nllb_language_code(source_language)
    target_code = nllb_language_code(target_language)
    if source_code == target_code:
        translated_cues = [
            SubtitleCue(
                index=cue.index, start=cue.start, end=cue.end, text=wrap_translated_text(cue.text)
            )
            for cue in cues
        ]
        return SubtitleTranslation(
            cues=translated_cues,
            metadata={
                "skipped": True,
                "reason": "source_language_matches_target_language",
                "source_language": source_language,
                "target_language": target_language,
                "model": model_alias,
                "device": "none",
                "runtime_seconds": 0.0,
                "cue_count": len(cues),
            },
        )

    missing = missing_translation_model_files(model_alias)
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            "Local translation model is missing. "
            f"Missing files: {missing_text}. "
            f"Download with: {translation_model_download_command(model_alias)}"
        )

    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except Exception as exc:  # pragma: no cover - depends on optional local runtime
        raise RuntimeError(
            "Local subtitle translation requires transformers. "
            "Run python3 configs/setup_local_app.py to install the updated runtime."
        ) from exc

    model_dir = translation_model_dir(model_alias)
    device = (
        "mps"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
        else "cpu"
    )
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir), local_files_only=True)
    model.to(device)
    model.eval()
    tokenizer.src_lang = source_code
    forced_bos_token_id = tokenizer.convert_tokens_to_ids(target_code)

    translated_texts: list[str] = []
    texts = [compact_ws(cue.text) for cue in cues]
    with torch.no_grad():
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            encoded = tokenizer(
                batch, return_tensors="pt", padding=True, truncation=True, max_length=256
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            generated = model.generate(
                **encoded,
                forced_bos_token_id=forced_bos_token_id,
                max_length=256,
                no_repeat_ngram_size=3,
                repetition_penalty=1.15,
            )
            translated_texts.extend(
                apply_source_aware_zh_fixes(source, normalize_translated_zh_text(translated))
                for source, translated in zip(
                    batch,
                    tokenizer.batch_decode(generated, skip_special_tokens=True),
                    strict=True,
                )
            )

    if len(translated_texts) != len(cues):
        raise RuntimeError(
            f"Translation returned {len(translated_texts)} cue texts for {len(cues)} input cues."
        )

    translated_cues = [
        SubtitleCue(
            index=cue.index,
            start=cue.start,
            end=cue.end,
            text=wrap_translated_text(text, max_line_chars=max_line_chars),
        )
        for cue, text in zip(cues, translated_texts, strict=True)
    ]
    return SubtitleTranslation(
        cues=translated_cues,
        metadata={
            "skipped": False,
            "source_language": source_language,
            "target_language": target_language,
            "source_code": source_code,
            "target_code": target_code,
            "model": model_alias,
            "model_dir": str(model_dir),
            "device": device,
            "runtime_seconds": time.perf_counter() - started,
            "cue_count": len(cues),
        },
    )


def translate_subtitle_cues_cloud(
    cues: list[SubtitleCue],
    *,
    source_language: str,
    target_language: str,
    batch_size: int = 24,
    max_line_chars: int = 42,
    audit_dir: Path | None = None,
) -> SubtitleTranslation:
    target_language = normalize_target_language(target_language) or "zh"
    if target_language != "zh":
        raise ValueError(
            f"Unsupported target language: {target_language}. Currently supported: zh."
        )
    source_code = nllb_language_code(source_language)
    target_code = nllb_language_code(target_language)
    if source_code == target_code:
        translated_cues = [
            SubtitleCue(
                index=cue.index, start=cue.start, end=cue.end, text=wrap_translated_text(cue.text)
            )
            for cue in cues
        ]
        return SubtitleTranslation(
            cues=translated_cues,
            metadata={
                "backend": "cloud",
                "skipped": True,
                "reason": "source_language_matches_target_language",
                "source_language": source_language,
                "target_language": target_language,
                "model": "none",
                "runtime_seconds": 0.0,
                "cue_count": len(cues),
            },
        )

    resolved = resolve_cloud_options(CloudClientOptions())
    if audit_dir is not None:
        audit_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    translated_texts: list[str] = []
    texts = [compact_ws(cue.text) for cue in cues]
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = call_openai_compatible_chat(
            system_prompt=_cloud_subtitle_translation_system_prompt(),
            user_content=_cloud_subtitle_translation_user_content(
                batch, source_language=source_language
            ),
            options=CloudClientOptions(),
            audit_path=(audit_dir / f"translation.cloud.{start // batch_size:04d}.api_run.json")
            if audit_dir
            else None,
        )
        translated_texts.extend(
            _parse_cloud_translation_response(response, expected_count=len(batch))
        )

    if len(translated_texts) != len(cues):
        raise RuntimeError(
            f"Translation returned {len(translated_texts)} cue texts for {len(cues)} input cues."
        )

    translated_cues = [
        SubtitleCue(
            index=cue.index,
            start=cue.start,
            end=cue.end,
            text=wrap_translated_text(
                apply_source_aware_zh_fixes(cue.text, normalize_translated_zh_text(text)),
                max_line_chars=max_line_chars,
            ),
        )
        for cue, text in zip(cues, translated_texts, strict=True)
    ]
    return SubtitleTranslation(
        cues=translated_cues,
        metadata={
            "backend": "cloud",
            "source_language": source_language,
            "target_language": target_language,
            "source_code": source_code,
            "target_code": target_code,
            "model": resolved.model,
            "api_base": resolved.api_base,
            "api": "responses",
            "runtime_seconds": round(time.perf_counter() - started, 3),
            "cue_count": len(cues),
            "batch_count": (len(texts) + batch_size - 1) // batch_size,
        },
    )


def _cloud_subtitle_translation_system_prompt() -> str:
    return (
        "You translate subtitle cue text into Simplified Chinese. "
        "Preserve meaning, names, numbers, and tone. Do not add explanations. "
        "Return only strict JSON: an array of strings, one translated string per input item, in the same order."
    )


def _cloud_subtitle_translation_user_content(texts: list[str], *, source_language: str) -> str:
    return json.dumps(
        {
            "source_language": source_language,
            "target_language": "zh-Hans",
            "items": texts,
        },
        ensure_ascii=False,
        indent=2,
    )


def _parse_cloud_translation_response(text: str, *, expected_count: int) -> list[str]:
    stripped = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if fenced:
        stripped = fenced.group(1).strip()
    payload = json.loads(stripped)
    if isinstance(payload, dict):
        payload = payload.get("items") or payload.get("translations")
    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise ValueError("Cloud subtitle translation must return a JSON array of strings.")
    if len(payload) != expected_count:
        raise RuntimeError(
            f"Cloud translation returned {len(payload)} texts for {expected_count} input texts."
        )
    return [compact_ws(item) for item in payload]
