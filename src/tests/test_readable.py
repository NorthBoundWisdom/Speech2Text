from atot.readable import compose_readable_transcript


def test_readable_composer_merges_segments_with_audited_joiners_and_spacing():
    result = compose_readable_transcript(
        [
            {"start": 0.0, "end": 1.0, "text": "我觉得"},
            {"start": 1.0, "end": 2.0, "text": "ChatGPT很好。"},
            {"start": 190.0, "end": 191.0, "text": "下一段AI继续讲"},
        ],
        title="Episode",
    )

    assert result.markdown.startswith("# Episode")
    assert "[00:00:00] 我觉得 ChatGPT 很好。" in result.markdown
    assert "[00:03:10] 下一段 AI 继续讲" in result.markdown
    assert result.log["paragraph_count"] == 2
    assert {item["type"] for item in result.log["transformations"]} >= {
        "insert_joiner",
        "normalize_spacing",
        "flush_paragraph",
    }


def test_readable_composer_splits_overlong_paragraphs():
    result = compose_readable_transcript(
        [
            {"start": 0.0, "end": 1.0, "text": "第一句。" * 30},
        ],
        max_paragraph_chars=40,
    )

    assert result.log["paragraph_count"] > 1
    assert any(item["type"] == "split_long_paragraph" for item in result.log["transformations"])
