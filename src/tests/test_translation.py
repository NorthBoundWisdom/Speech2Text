from atot.translation import apply_source_aware_zh_fixes, normalize_translated_zh_text


def test_normalize_translated_zh_text_collapses_repeated_short_units():
    text = "开放你的思想,开放你的思想,开放你的思想,开放你的思想."

    normalized = normalize_translated_zh_text(text)

    assert normalized == "开放你的思想，开放你的思想，开放你的思想。"


def test_normalize_translated_zh_text_strips_leading_punctuation():
    assert normalize_translated_zh_text(",我很高兴.") == "我很高兴。"


def test_normalize_translated_zh_text_strips_trailing_repeat_comma():
    assert normalize_translated_zh_text("非常,非常,非常,非常,非常,") == "非常，非常"


def test_apply_source_aware_zh_fixes_corrects_spiritual_medium():
    assert (
        apply_source_aware_zh_fixes("being a medium almost daily", "成为一个中文。")
        == "成为一名灵媒。"
    )
