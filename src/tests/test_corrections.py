from atot.corrections import (
    PUNCTUATION_PROMPT_SUFFIX,
    apply_corrections,
    apply_corrections_to_segments,
    default_glossary,
    make_prompt,
)


def sample_glossary():
    return {
        "people": ["孙天祥", "张伟楠"],
        "organizations": ["日行迹", "Analemma", "复旦大学", "上海创智学院", "西电"],
        "technical_terms": [
            "MOSS",
            "FARS",
            "AGI",
            "ChatGPT",
            "大模型",
            "智能体",
            "生物竞赛",
            "软件工程",
            "计算机科学",
        ],
        "common_corrections": {"西链": "西电", "本课": "本科", "魔术程度": "某种程度"},
    }


def test_default_glossary_is_generic():
    glossary = default_glossary()
    assert glossary["people"] == []
    assert glossary["organizations"] == []
    assert "ChatGPT" in glossary["technical_terms"]


def test_apply_corrections_counts_replacements():
    result = apply_corrections("我是本课，来自西链。魔术程度上。", sample_glossary())
    assert result.text == "我是本科，来自西电。某种程度上。"
    assert {item["from"]: item["count"] for item in result.report} == {
        "西链": 1,
        "本课": 1,
        "魔术程度": 1,
    }


def test_apply_corrections_cleans_common_asr_artifacts():
    result = apply_corrections("对＞那这里包括咖啡兼职＞?以及异常字符�。", {})

    assert result.text == "对，那这里包括咖啡兼职？以及异常字符。"
    assert {item["from"]: item["to"] for item in result.report} == {
        "＞": "，",
        "＞?": "？",
        "�": "",
    }


def test_apply_corrections_removes_runaway_repetition():
    result = apply_corrections(
        "我想聊着急的时候，我说，诶，是什么事情。但是因为我说,我说,我说,我说,我说,我说,我说,我说,",
        {},
    )

    assert result.text == "我想聊着急的时候，我说，诶，是什么事情。"
    assert result.report[-1]["kind"] == "asr_runaway_repetition"


def test_apply_corrections_keeps_short_natural_repetition():
    result = apply_corrections("结果我看到飞书里已读,已读,已读,已读,还是没人回。", {})

    assert result.text == "结果我看到飞书里已读，已读，已读，已读，还是没人回。"


def test_apply_corrections_trims_repeated_sentence_suffix():
    result = apply_corrections(
        "节目介绍结束。欢迎大家进行的频道。欢迎大家进行的频道。欢迎大家进行的频道。欢迎大家进行的频道。欢迎",
        {},
    )

    assert result.text == "节目介绍结束。欢迎大家进行的频道。"
    assert result.report[0]["kind"] == "asr_runaway_clause_repetition"
    assert result.report[0]["count"] == 4


def test_apply_corrections_keeps_short_sentence_emphasis():
    result = apply_corrections("他说谢谢。谢谢。谢谢。然后继续往下聊。", {})

    assert result.text == "他说谢谢。谢谢。谢谢。然后继续往下聊。"


def test_apply_corrections_to_segments():
    segments = [
        {"start": 0.0, "end": 1.0, "text": "西链"},
        {"start": 1.0, "end": 2.0, "text": "本课"},
        {"start": 2.0, "end": 3.0, "text": "我说,我说,我说,我说,我说,我说"},
    ]
    corrected, report = apply_corrections_to_segments(segments, sample_glossary())
    assert [s["text"] for s in corrected] == ["西电", "本科", ""]
    assert sum(item["count"] for item in report) == 8
    assert {item["kind"] for item in report} == {"glossary", "asr_runaway_repetition"}
    assert report[0]["matches"][0]["segment_index"] == 2


def test_apply_corrections_suppresses_tail_low_confidence_hallucination():
    segments = [
        {"start": 80.0, "end": 85.0, "text": "最后一句正常内容。", "avg_logprob": -0.2},
        {"start": 92.0, "end": 110.0, "text": "含糊重复的尾部幻觉。", "avg_logprob": -1.7},
    ]

    corrected, report = apply_corrections_to_segments(segments, {}, audio_duration=100.0)

    assert corrected[0]["text"] == "最后一句正常内容。"
    assert corrected[1]["text"] == ""
    assert corrected[1]["suppressed"] is True
    assert corrected[1]["suppress_reason"] == "tail_hallucination"
    assert corrected[1]["end"] == 100.0
    tail_report = next(item for item in report if item["kind"] == "asr_tail_hallucination")
    assert tail_report["matches"][0]["segment_index"] == 1


def test_apply_corrections_keeps_low_confidence_segment_outside_tail():
    segments = [
        {"start": 50.0, "end": 68.0, "text": "这段虽然低置信度但不在尾部。", "avg_logprob": -1.7},
        {"start": 95.0, "end": 98.0, "text": "结束。", "avg_logprob": -0.2},
    ]

    corrected, report = apply_corrections_to_segments(segments, {}, audio_duration=120.0)

    assert [segment["text"] for segment in corrected] == ["这段虽然低置信度但不在尾部。", "结束。"]
    assert {item["kind"] for item in report} != {"asr_tail_hallucination"}


def test_apply_corrections_suppresses_tail_high_compression_hallucination():
    segments = [
        {"start": 80.0, "end": 98.0, "text": "正常收尾。", "compression_ratio": 1.1},
        {
            "start": 99.2,
            "end": 100.0,
            "text": "课 课 课 课 课 课 课 课 课 课",
            "compression_ratio": 7.0,
        },
    ]

    corrected, report = apply_corrections_to_segments(segments, {}, audio_duration=100.0)

    assert corrected[-1]["text"] == ""
    assert corrected[-1]["suppressed"] is True
    assert corrected[-1]["suppress_reason"] == "tail_hallucination"
    assert any(item["kind"] == "asr_tail_hallucination" for item in report)


def test_make_prompt_adds_terms():
    prompt = make_prompt("基础提示。", sample_glossary())
    assert prompt is not None
    assert "基础提示" in prompt
    assert "孙天祥" in prompt
    assert "计算机科学" in prompt
    assert prompt.endswith(PUNCTUATION_PROMPT_SUFFIX)


def test_make_prompt_filters_noisy_metadata_terms():
    prompt = make_prompt(
        "基础提示。",
        {
            "technical_terms": [
                "ChatGPT",
                "PT67M",
                "mp3",
                "www.xiaoyuzhoufm.com/episode/abc",
                "media.xyzcdn.net/path/show.m4a",
            ]
        },
    )

    assert prompt is not None
    assert "ChatGPT" in prompt
    assert "PT67M" not in prompt
    assert "mp3" not in prompt
    assert "xiaoyuzhou" not in prompt
    assert "xyzcdn" not in prompt


def test_make_prompt_caps_topic_and_terms():
    glossary = {"technical_terms": [f"术语{i}" for i in range(100)]}
    prompt = make_prompt("基础提示。", glossary, topic_summary="很长的话题背景" * 80, max_chars=120)

    assert prompt is not None
    assert len(prompt) <= 120
    assert prompt.endswith(PUNCTUATION_PROMPT_SUFFIX[:120])


def test_ascii_correction_does_not_replace_inside_longer_token():
    result = apply_corrections("FAS 和 FARS", {"common_corrections": {"FAS": "FARS"}})
    assert result.text == "FARS 和 FARS"


def test_rule_layered_glossary_supports_safe_contextual_and_review_only():
    glossary = {
        "organizations": ["西电"],
        "technical_terms": ["计算机"],
        "safe_global": {"ChiaGPT": "ChatGPT"},
        "contextual_regex": [
            {
                "name": "xidian_cs_context",
                "pattern": "在系列学计算机",
                "replacement": "在西电学计算机",
                "requires_terms": ["西电", "计算机"],
            }
        ],
        "review_only": {"PIN3口": ["聘三口"]},
    }

    corrected, report = apply_corrections_to_segments(
        [{"start": 0.0, "end": 1.0, "text": "我在系列学计算机，用 ChiaGPT，路过 PIN3口。"}],
        glossary,
    )

    assert corrected[0]["text"] == "我在西电学计算机，用 ChatGPT，路过 PIN3口。"
    kinds = {item["kind"] for item in report}
    assert {"contextual_regex", "safe_global", "review_only"} <= kinds
    contextual = next(item for item in report if item["kind"] == "contextual_regex")
    assert contextual["rule_name"] == "xidian_cs_context"
    assert contextual["matches"][0]["before"].startswith("我在系列")


def test_contextual_regex_cache_keeps_invalid_rules_non_fatal():
    glossary = {
        "contextual_regex": [
            {"name": "bad", "pattern": "(", "replacement": "x"},
            {"name": "good", "pattern": "云原声", "replacement": "云原生"},
        ]
    }

    first = apply_corrections("云原声", glossary)
    second = apply_corrections("云原声", glossary)

    assert first.text == "云原生"
    assert second.text == first.text
