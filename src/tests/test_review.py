from atot.review import build_review, review_to_markdown


def test_review_flags_theme_conditioned_confusions():
    review = build_review(
        [
            {"start": 12.0, "end": 18.0, "text": "ChiacPT 出来之后，大家开始讨论定会论文。"},
            {"start": 20.0, "end": 24.0, "text": "Cloud Code 做实验。"},
        ],
        {
            "technical_terms": ["ChatGPT", "顶会", "Claude Code"],
        },
    )

    issues = review["issues"]
    assert any(
        item.get("observed") == "ChiacPT" and item.get("target") == "ChatGPT" for item in issues
    )
    assert any(item.get("observed") == "定会" and item.get("target") == "顶会" for item in issues)
    assert any(
        item.get("observed") == "Cloud Code" and item.get("target") == "Claude Code"
        for item in issues
    )
    assert review["summary"]["segment_issue_count"] == 2
    assert "ChiacPT" in review_to_markdown(review)


def test_review_does_not_flag_confusion_when_target_is_absent():
    review = build_review(
        [{"start": 0.0, "end": 1.0, "text": "这里说的是一个普通 Fast 路径。"}],
        {"technical_terms": ["AGI"]},
    )

    assert not any(item.get("observed") == "Fast" for item in review["issues"])


def test_review_does_not_treat_ken_ding_hui_as_top_conference_error():
    review = build_review(
        [{"start": 0.0, "end": 1.0, "text": "这个项目肯定会继续推进，一定会实现。"}],
        {"technical_terms": ["顶会"]},
    )

    assert not any(item.get("observed") == "定会" for item in review["issues"])


def test_review_flags_glossary_near_misses():
    review = build_review(
        [{"start": 3.0, "end": 9.0, "text": "今天请到孙天详，他来自上海创制学院。"}],
        {"people": ["孙天祥"], "organizations": ["上海创智学院"]},
    )

    issues = review["issues"]
    assert any(
        item.get("type") == "possible_glossary_near_miss"
        and item.get("target") == "孙天祥"
        and item.get("items", [])[0]["observed"] == "孙天详"
        for item in issues
    )
    assert any(
        item.get("type") == "possible_glossary_near_miss"
        and item.get("target") == "上海创智学院"
        and item.get("items", [])[0]["observed"] == "上海创制学院"
        for item in issues
    )
    assert review["segments"][0]["flags"] == ["possible_glossary_near_miss"]
    assert "Possible near miss" in review_to_markdown(review)


def test_review_near_miss_avoids_generic_terms():
    review = build_review(
        [{"start": 0.0, "end": 2.0, "text": "这个模型和智能的工具都很常见。"}],
        {"technical_terms": ["大模型", "智能体"]},
    )

    assert not any(item.get("type") == "possible_glossary_near_miss" for item in review["issues"])


def test_review_near_miss_ignores_title_variant_inside_numeric_handle():
    review = build_review(
        [{"start": 0.0, "end": 2.0, "text": "可以添加微信号毕不了夜123。"}],
        {"titles": ["毕不了业"]},
    )

    assert not any(item.get("type") == "possible_glossary_near_miss" for item in review["issues"])


def test_review_reports_suppressed_segments():
    review = build_review(
        [
            {"start": 0.0, "end": 1.0, "text": "正常内容。"},
            {
                "start": 95.0,
                "end": 100.0,
                "text": "",
                "suppressed": True,
                "suppress_reason": "tail_hallucination",
            },
        ],
        {},
    )

    assert review["summary"]["suppressed_segment_count"] == 1
    assert review["suppressed_segments"][0]["time"] == "00:01:35"
    assert review["suppressed_segments"][0]["reason"] == "tail_hallucination"
    markdown = review_to_markdown(review)
    assert "Suppressed segments: 1" in markdown
    assert "tail_hallucination" in markdown
