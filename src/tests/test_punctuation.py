from atot.punctuation import normalize_chinese_punctuation_with_report


def test_normalize_chinese_punctuation_keeps_english_internal_punctuation():
    text = "你好,今天聊 GPT-3 和 example.com. 你觉得好吗? 太好了!"

    corrected, report = normalize_chinese_punctuation_with_report(text)

    assert corrected == "你好，今天聊 GPT-3 和 example.com. 你觉得好吗？太好了！"
    assert {item["kind"] for item in report} == {"punctuation_normalization"}


def test_normalize_chinese_period_only_in_chinese_context():
    corrected, _ = normalize_chinese_punctuation_with_report("版本是 1.2.3. 结束.")

    assert corrected == "版本是 1.2.3. 结束。"
