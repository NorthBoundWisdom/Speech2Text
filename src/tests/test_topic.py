from atot.corrections import apply_corrections, merge_glossaries
from atot.topic import extract_episode_glossary


TOPIC = """
日行迹（Analemma）创始人兼CEO、上海创智学院导师、中国首个类ChatGPT大模型MOSS一作 孙天祥

上海交通大学 计算机学院教授 张伟楠（@张伟楠SJTU）

全自动科研系统FARS发布，讨论顶会论文、AGI 和生存焦虑。
"""

PODCAST_TOPIC = """
- 节目：毕不了业

本期播客简介。
"""


def test_extract_episode_glossary_from_topic():
    glossary = extract_episode_glossary(TOPIC)

    assert "孙天祥" in glossary["people"]
    assert "张伟楠" in glossary["people"]
    assert "日行迹" in glossary["organizations"]
    assert "Analemma" in glossary["organizations"]
    assert "上海创智学院" in glossary["organizations"]
    assert "MOSS" in glossary["technical_terms"]
    assert "FARS" in glossary["technical_terms"]
    assert "论文" in glossary["technical_terms"]
    assert glossary["common_corrections"]["日行纪"] == "日行迹"
    assert glossary["common_corrections"]["上海创制学院"] == "上海创智学院"
    assert glossary["common_corrections"]["FAS"] == "FARS"


def test_extract_episode_glossary_ignores_url_and_media_metadata():
    glossary = extract_episode_glossary(
        """
        节目：科技访谈
        原链接：https://www.xiaoyuzhoufm.com/episode/abc123
        音频：https://media.xyzcdn.net/path/show.m4a
        时长：PT67M
        本期讨论 ChatGPT、AGI 和 RODE。
        """
    )

    terms = set(glossary["technical_terms"])
    assert {"ChatGPT", "AGI", "RODE"} <= terms
    assert "PT67M" not in terms
    assert "mp3" not in terms
    assert not any(
        "xiaoyuzhou" in term or "xyzcdn" in term or term.endswith(".m4a") for term in terms
    )


def test_topic_corrections_are_boundary_aware_for_ascii_terms():
    glossary = extract_episode_glossary(TOPIC)
    result = apply_corrections("FAS 发布了，FARS 不应变成 FARSS。MOS 是前作。漏文。", glossary)

    assert result.text == "FARS 发布了，FARS 不应变成 FARSS。MOSS 是前作。论文。"


def test_chatgpt_topic_adds_contextual_ascii_corrections():
    glossary = extract_episode_glossary("本期讨论 ChatGPT 和类ChatGPT 应用。")
    result = apply_corrections("ChiaGPT 出来后，GBT3 和 GPT3 都被频繁讨论。", glossary)

    assert result.text == "ChatGPT 出来后，GPT-3 和 GPT-3 都被频繁讨论。"


def test_claude_code_topic_adds_contextual_ascii_correction():
    glossary = extract_episode_glossary(
        "本期讨论 Claude Code、Codex、AI coding workflow 和 DeepSeek。"
    )
    result = apply_corrections("Cloud Code、Codex 和 Deepseek 都被频繁讨论。", glossary)
    unrelated = apply_corrections("Cloud Code 和 Codex 都被频繁讨论。", {})

    assert result.text == "Claude Code、Codex 和 DeepSeek 都被频繁讨论。"
    assert unrelated.text == "Cloud Code 和 Codex 都被频繁讨论。"


def test_episode_show_name_adds_narrow_podcast_corrections():
    glossary = extract_episode_glossary(PODCAST_TOPIC)
    result = apply_corrections("欢迎来到逼不了夜，我们之前很多期博客聊过。", glossary)
    non_title_result = apply_corrections("想加入听友群，可以添加微信号毕不了夜123。", glossary)

    assert "毕不了业" in glossary["titles"]
    assert "逼不了夜" not in glossary.get("common_corrections", {})
    assert result.text == "欢迎来到毕不了业，我们之前很多期播客聊过。"
    assert non_title_result.text == "想加入听友群，可以添加微信号毕不了夜123。"


def test_merge_glossaries_combines_base_and_episode_corrections():
    merged = merge_glossaries(
        {"people": ["孙天祥"], "common_corrections": {"本课": "本科"}},
        extract_episode_glossary(TOPIC),
    )

    assert "孙天祥" in merged["people"]
    assert "FARS" in merged["technical_terms"]
    assert merged["common_corrections"]["本课"] == "本科"
    assert merged["common_corrections"]["日行纪"] == "日行迹"


def test_topic_glossary_drives_narrow_named_entity_and_title_corrections():
    glossary = extract_episode_glossary(
        """
        日行迹（Analemma）创始人孙天祥，现为上海创智学院导师。
        本期节目：无聊斋。
        讨论 DeepSeek，与《等待戈多》的舞台经验。
        """
    )

    result = apply_corrections(
        "日行季后来在上海创始学院讨论 DeepSig 和 Deepseek，还聊等待歌多，也提到无聊宅。",
        glossary,
    )

    assert (
        result.text
        == "日行迹后来在上海创智学院讨论 DeepSeek 和 DeepSeek，还聊等待戈多，也提到无聊斋。"
    )
    assert "等待戈多" in glossary["titles"]


def test_episode_titles_are_not_global_corrections_without_topic_context():
    result = apply_corrections("还聊等待歌多，也提到无聊宅。", {})

    assert result.text == "还聊等待歌多，也提到无聊宅。"


def test_title_context_corrects_episode_counter_variant():
    glossary = extract_episode_glossary(PODCAST_TOPIC)

    result = apply_corrections("毕不了夜的第96期，今天我们继续聊。", glossary)

    assert result.text == "毕不了业的第96期，今天我们继续聊。"
