from atot.backends import ASRTranscribeOptions, MlxWhisperBackend
from atot.context import build_prompt_context, write_context_files
from atot.rules import load_rule_file, load_rule_file_for_text, selected_rule_packs


def test_prompt_context_uses_capped_topic_summary_and_glossary_terms(tmp_path):
    audio = tmp_path / "episode.m4a"
    audio.write_bytes(b"")
    long_private_note = "这是一段很长的个人备注，不应该完整进入 Whisper prompt。" * 80
    (tmp_path / "主题.md").write_text(
        f"日行迹（Analemma）创始人 孙天祥老师，讨论 ChatGPT 和顶会论文。\n{long_private_note}",
        encoding="utf-8",
    )
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("请输出准确中文。", encoding="utf-8")
    glossary = tmp_path / "glossary.json"
    glossary.write_text(
        '{"technical_terms": ["AGI"], "common_corrections": {"本课": "本科"}}', encoding="utf-8"
    )

    context = build_prompt_context(audio, prompt_file=prompt, glossary_file=glossary)

    assert "请输出准确中文" in str(context.effective_prompt)
    assert context.effective_prompt is not None
    assert len(context.effective_prompt) <= 800
    assert long_private_note not in context.effective_prompt
    assert "节目背景摘要" not in context.effective_prompt
    assert context.topic_prompt_summary is not None
    assert len(context.topic_prompt_summary) <= 280
    assert "孙天祥" in context.glossary["people"]
    assert "AGI" in context.glossary["technical_terms"]
    assert context.glossary["common_corrections"]["本课"] == "本科"
    assert context.glossary["common_corrections"]["日行纪"] == "日行迹"
    assert {item["label"] for item in context.prompt_sources} == {"public_prompt"}

    files = write_context_files(tmp_path / "output", context, glossary_file=glossary)
    assert files.topic_prompt_summary_file is not None
    assert (
        files.topic_prompt_summary_file.read_text(encoding="utf-8").strip()
        == context.topic_prompt_summary
    )


def test_topic_prompt_summary_skips_transport_metadata(tmp_path):
    audio = tmp_path / "episode.m4a"
    audio.write_bytes(b"")
    (tmp_path / "主题.md").write_text(
        """
        节目：科技访谈
        原链接：https://www.xiaoyuzhoufm.com/episode/abc123
        音频：https://media.xyzcdn.net/path/show.m4a
        发布时间：2026-05-28 12:00:00 +0800
        时长：PT67M
        Shownotes
        本期讨论 ChatGPT 和 AGI。
        """,
        encoding="utf-8",
    )

    context = build_prompt_context(audio, prompt_file=None, glossary_file=None)

    assert context.topic_prompt_summary is not None
    assert "科技访谈" in context.topic_prompt_summary
    assert "ChatGPT" in context.topic_prompt_summary
    assert "xiaoyuzhou" not in context.topic_prompt_summary
    assert "media.xyzcdn" not in context.topic_prompt_summary
    assert "2026-05-28" not in context.topic_prompt_summary
    assert "PT67M" not in context.topic_prompt_summary
    assert "Shownotes" not in context.topic_prompt_summary


def test_rule_files_are_bundled_and_backend_exposes_capabilities():
    review_rules = load_rule_file("review_rules.json")
    topic_rules = load_rule_file("topic_rules.json")
    tech_review_rules = load_rule_file_for_text("review_rules.json", "本期讨论 ChatGPT 和顶会论文")
    tech_topic_rules = load_rule_file_for_text("topic_rules.json", "本期讨论 ChatGPT 和顶会论文")
    explicit_tech_rules = load_rule_file_for_text(
        "review_rules.json", "普通访谈", packs=("tech_ai_zh",)
    )
    no_pack_rules = load_rule_file_for_text(
        "review_rules.json", "本期讨论 ChatGPT 和顶会论文", packs=()
    )
    backend = MlxWhisperBackend(verbose=False)
    options = ASRTranscribeOptions(model="large-v3-turbo")

    assert "ChatGPT" not in review_rules["confusions"]
    assert "ChatGPT" in tech_review_rules["confusions"]
    assert "ChatGPT" in explicit_tech_rules["confusions"]
    assert "ChatGPT" not in no_pack_rules["confusions"]
    assert selected_rule_packs("本期讨论 ChatGPT", ("auto",)) == ("tech_ai_zh",)
    assert "known_corrections" in topic_rules
    assert "ChatGPT" in tech_topic_rules["ascii_keep_terms"]
    assert backend.name == "mlx-whisper"
    assert backend.supports_prompt is True
    assert backend.supports_word_timestamps is True
    assert backend.supports_diarization is False
    assert options.language == "zh"
