import pytest

from atot.cloud.output_state import CloudOutputOptions
from atot.cloud.review import (
    apply_cloud_patches,
    write_cloud_glossary_review,
    write_cloud_polish_suggestions,
)
from atot.cloud.summary_outputs import _chunk_user_content_for_cloud, write_cloud_summary
from atot.utils import read_json, write_json_atomic, write_text_atomic

fcntl = pytest.importorskip("fcntl")


def _write_cloud_input(tmp_path):
    output = tmp_path / "output"
    input_dir = output / "cloud" / "input"
    write_text_atomic(
        input_dir / "transcript.for_cloud.md",
        "# Transcript For Cloud\n\n"
        "[00:00:00 -> 00:00:02] 你好,这里是 API 测试。\n"
        "[00:11:00 -> 00:11:02] 第二段 API 再次出现。\n",
    )
    write_text_atomic(
        input_dir / "chunks" / "text_chunk_0001.md",
        "# Text Chunk 0001\n\n"
        "Range: 00:00:00 -> 00:02:00\n\n"
        "# Transcript For Cloud\n\n"
        "[00:00:00 -> 00:00:02] 你好,这里是 API 测试。\n",
    )
    write_json_atomic(
        input_dir / "manifest.json",
        {
            "episode_title": "API 测试节目",
            "audio_duration": 120.0,
            "text_chunks": ["chunks/text_chunk_0001.md"],
            "text_chunk_ranges": [
                {
                    "path": "chunks/text_chunk_0001.md",
                    "start": "00:00:00",
                    "end": "00:02:00",
                    "start_seconds": 0.0,
                    "end_seconds": 120.0,
                }
            ],
            "input_files": ["transcript.for_cloud.md"],
        },
    )
    write_json_atomic(
        input_dir / "qa.for_cloud.json",
        {
            "success": False,
            "issues": [{"type": "large_gap", "severity": "medium", "time": "00:10:00"}],
        },
    )
    write_json_atomic(
        input_dir / "glossary.for_cloud.json",
        {"technical_terms": ["API"], "people": ["测试嘉宾"]},
    )
    write_json_atomic(
        output / "run.json", {"success": True, "cloud": {"prepared": True, "outputs": []}}
    )
    return output


def test_write_cloud_summary_outputs_standard_files(tmp_path):
    output = _write_cloud_input(tmp_path)

    result = write_cloud_summary(CloudOutputOptions(output_dir=output))

    assert result["success"] is True
    assert result["mode"] == "chunked"
    summary_text = (output / "cloud" / "summary.md").read_text(encoding="utf-8")
    assert summary_text.startswith("# API 测试节目")
    assert "Chunk Highlights" in summary_text
    assert "你好,这里是 API 测试。" in summary_text
    chapter = read_json(output / "cloud" / "chapters.json")["chapters"][0]
    assert chapter["source_chunks"] == ["chunks/text_chunk_0001.md"]
    assert chapter["source_segment_ids"]
    assert "00:00:00 - 00:00:02" in (output / "cloud" / "chapters.md").read_text(encoding="utf-8")
    assert (output / "cloud" / "shownotes.md").exists()
    assert (
        read_json(output / "cloud" / "title_candidates.json")["candidates"][0]["title"]
        == "API 测试节目"
    )
    assert "API 测试节目" in (output / "cloud" / "title_candidates.md").read_text(encoding="utf-8")
    assert "API 测试节目" in (output / "cloud" / "social_copy.md").read_text(encoding="utf-8")
    terms = read_json(output / "cloud" / "terms.json")["terms"]
    assert {item["term"] for item in terms} == {"API", "测试嘉宾"}
    assert "API" in (output / "cloud" / "terms.md").read_text(encoding="utf-8")
    assert (output / "cloud" / "uncertainty_report.md").exists()
    assert (output / "cloud" / "fact_or_term_uncertainties.md").read_text(encoding="utf-8") == (
        output / "cloud" / "uncertainty_report.md"
    ).read_text(encoding="utf-8")
    assert (
        read_json(output / "cloud" / "chunk_summaries" / "chunk_0001.summary.json")["start"]
        == "00:00:00"
    )
    cloud_outputs = read_json(output / "run.json")["cloud"]["outputs"]
    run_cloud = read_json(output / "run.json")["cloud"]
    assert "cloud/summary.md" in cloud_outputs
    assert "cloud/manifest.json" in cloud_outputs
    assert "cloud/title_candidates.json" in cloud_outputs
    assert "cloud/title_candidates.md" in cloud_outputs
    assert "cloud/social_copy.md" in cloud_outputs
    assert "cloud/terms.json" in cloud_outputs
    assert "cloud/terms.md" in cloud_outputs
    assert "cloud/uncertainty_report.md" in cloud_outputs
    assert "cloud/fact_or_term_uncertainties.md" in cloud_outputs
    assert "cloud/chunk_summaries/chunk_0001.summary.json" in cloud_outputs
    assert run_cloud["summary_mode"] == "map_reduce"
    manifest = read_json(output / "cloud" / "manifest.json")
    assert manifest["contains_audio"] is False
    assert manifest["contains_video"] is False
    assert "summary.md" in manifest["output_files"]
    assert "title_candidates.json" in manifest["output_files"]
    assert "social_copy.md" in manifest["output_files"]
    assert "terms.json" in manifest["output_files"]
    assert "fact_or_term_uncertainties.md" in manifest["output_files"]
    assert manifest["summary_strategy"] == "map_reduce"


def test_chunk_summary_uses_manifest_range_when_chunk_text_has_no_range(tmp_path):
    output = _write_cloud_input(tmp_path)
    input_dir = output / "cloud" / "input"
    write_text_atomic(
        input_dir / "chunks" / "text_chunk_0001.md",
        "# Text Chunk 0001\n\n# Transcript For Cloud\n\n[00:03:00 -> 00:03:05] 缺少 Range 行。\n",
    )
    manifest = read_json(input_dir / "manifest.json")
    manifest["text_chunk_ranges"] = [
        {"path": "chunks/text_chunk_0001.md", "start": "00:03:00", "end": "00:03:05"}
    ]
    write_json_atomic(input_dir / "manifest.json", manifest)

    write_cloud_summary(CloudOutputOptions(output_dir=output))

    chunk_summary = read_json(output / "cloud" / "chunk_summaries" / "chunk_0001.summary.json")
    assert chunk_summary["start"] == "00:03:00"
    assert chunk_summary["end"] == "00:03:05"


def test_chunk_summary_uses_chunks_manifest_before_duration_fallback(tmp_path):
    output = _write_cloud_input(tmp_path)
    input_dir = output / "cloud" / "input"
    write_text_atomic(
        input_dir / "chunks" / "text_chunk_0001.md",
        "# Text Chunk 0001\n\n# Transcript For Cloud\n\n[00:04:00 -> 00:04:04] 缺少 Range 和 manifest range。\n",
    )
    manifest = read_json(input_dir / "manifest.json")
    manifest.pop("text_chunk_ranges", None)
    write_json_atomic(input_dir / "manifest.json", manifest)
    write_json_atomic(
        output / "chunks_manifest.json",
        {
            "chunk_layout": {
                "chunks": [
                    {
                        "index": 0,
                        "source_start": 235.0,
                        "source_end": 245.0,
                        "core_start": 240.0,
                        "core_end": 244.0,
                    }
                ]
            }
        },
    )

    write_cloud_summary(CloudOutputOptions(output_dir=output))

    chunk_summary = read_json(output / "cloud" / "chunk_summaries" / "chunk_0001.summary.json")
    assert chunk_summary["start"] == "00:04:00"
    assert chunk_summary["end"] == "00:04:04"


def test_write_cloud_glossary_review_outputs_schema(tmp_path):
    output = _write_cloud_input(tmp_path)

    result = write_cloud_glossary_review(CloudOutputOptions(output_dir=output))

    payload = read_json(output / "cloud" / "glossary_suggestions.json")
    queue = read_json(output / "cloud" / "glossary_review_queue.json")
    assert result["suggestion_count"] == 1
    assert payload["needs_human_confirmation"][0]["canonical"] == "API"
    assert queue["review_only_terms"][0]["canonical"] == "API"
    assert queue["global_rule_candidates"] == []


def test_cloud_polish_and_apply_patches(tmp_path):
    output = _write_cloud_input(tmp_path)
    polish = write_cloud_polish_suggestions(CloudOutputOptions(output_dir=output))

    assert polish["patch_count"] == 1
    patch = read_json(output / "cloud" / "transcript.polish_suggestions.json")["patches"][0]
    assert patch["patch_id"] == "patch_0001"
    assert patch["old_text"] == "你好,这里是 API 测试。"
    assert patch["new_text"] == "你好，这里是 API 测试。"
    assert patch["requires_audio_check"] is False
    result = apply_cloud_patches(output, output / "cloud" / "transcript.polish_suggestions.json")

    assert result["applied_patch_count"] == 1
    assert result["decisions"][0]["applied"] is True
    assert "你好，这里" in (output / "cloud" / "transcript.readable.md").read_text(encoding="utf-8")
    assert read_json(output / "cloud" / "patch_apply_run.json")["mode"] == "reviewed"
    assert (
        read_json(output / "cloud" / "patch_apply.audit.json")["review_state"] == "human_confirmed"
    )
    assert "cloud/transcript.readable.md" in read_json(output / "run.json")["cloud"]["outputs"]
    assert "transcript.readable.md" in read_json(output / "cloud" / "manifest.json")["output_files"]


def test_cloud_summary_can_call_configured_text_api(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        if "Text Chunk 0001" in kwargs["user_content"]:
            return (
                '{"summary":"块摘要","terms":[{"term":"云术语","confidence":"high"}],'
                '"uncertainties":[{"term":"云术语","reason":"疑似专名"}]}'
            )
        if kwargs["audit_path"].name == "title.api_run.json":
            return "AI 喜剧工作者续命指南"
        return "# Cloud Summary\n\n云摘要"

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", fake_call)

    result = write_cloud_summary(
        CloudOutputOptions(
            output_dir=output,
            call_api=True,
        )
    )

    assert result["source"] == "cloud_model"
    assert result["partial"] is False
    assert "云摘要" in (output / "cloud" / "summary.md").read_text(encoding="utf-8")
    assert (output / "cloud" / "short_title.txt").read_text(
        encoding="utf-8"
    ).strip() == "AI 喜剧工作者续命指南"
    assert (
        read_json(output / "cloud" / "title_candidates.json")["candidates"][0]["kind"]
        == "short_title"
    )
    assert read_json(output / "cloud" / "chapters.json")["chapters"]
    assert "00:00:00" in (output / "cloud" / "chapters.md").read_text(encoding="utf-8")
    assert (output / "cloud" / "social_copy.md").exists()
    assert any(
        item["term"] == "云术语" for item in read_json(output / "cloud" / "terms.json")["terms"]
    )
    assert "云术语" in (output / "cloud" / "fact_or_term_uncertainties.md").read_text(
        encoding="utf-8"
    )
    assert (output / "cloud" / "uncertainty_report.md").exists()
    assert (output / "cloud" / "fact_or_term_uncertainties.md").exists()
    assert (output / "cloud" / "chunk_summaries" / "chunk_0001.summary.json").exists()
    chunk_summary = read_json(output / "cloud" / "chunk_summaries" / "chunk_0001.summary.json")
    assert chunk_summary["source"] == "cloud_model"
    episode_call = calls[-2]
    assert "Text Chunk 0001" in calls[0]["user_content"]
    assert "你好,这里是 API 测试" not in episode_call["user_content"]
    assert "qa.for_cloud.md" not in episode_call["user_content"]
    assert "qa.compact.json" in episode_call["user_content"]
    assert "chunk_summaries/chunk_0001.summary.json" in episode_call["user_content"]
    assert calls[0]["audit_path"].name == "chunk_0001.api_run.json"
    assert calls[-1]["audit_path"].name == "title.api_run.json"
    assert "podcast list title" in calls[-1]["system_prompt"]


def test_cloud_summary_replaces_generic_work_heading(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)

    def fake_call(**kwargs):
        if kwargs["audit_path"].name == "chunk_0001.api_run.json":
            return '{"summary":"块摘要","terms":[],"uncertainties":[]}'
        if kwargs["audit_path"].name == "title.api_run.json":
            return "测试嘉宾：聊透 API"
        return "# 播客结构化总结：《work》\n\n## 一、主要内容\n\n云摘要。"

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", fake_call)

    write_cloud_summary(CloudOutputOptions(output_dir=output, call_api=True))

    summary = (output / "cloud" / "summary.md").read_text(encoding="utf-8")
    assert summary.startswith("# API 测试节目")
    assert "播客结构化总结：《work》" not in summary


def test_cloud_short_title_can_be_forced_from_existing_summary(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "cloud" / "summary.md", "# Summary\n\n长摘要")
    write_json_atomic(
        output / "cloud" / "title_candidates.json",
        {"candidates": [{"title": "旧标题", "kind": "short_title"}]},
    )
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        return "重新生成的短标题"

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", fake_call)

    from atot.cloud.summary_outputs import write_cloud_short_title

    skipped = write_cloud_short_title(CloudOutputOptions(output_dir=output, call_api=True))
    forced = write_cloud_short_title(
        CloudOutputOptions(output_dir=output, call_api=True),
        force=True,
    )

    assert skipped["skipped"] is True
    assert forced["title"] == "重新生成的短标题"
    assert calls[0]["audit_path"].name == "title.api_run.json"
    assert (output / "cloud" / "short_title.txt").read_text(
        encoding="utf-8"
    ).strip() == "重新生成的短标题"
    forced_candidates = read_json(output / "cloud" / "title_candidates.json")["candidates"]
    assert forced_candidates == [
        {"kind": "short_title", "source": "cloud_model", "title": "重新生成的短标题"}
    ]


def test_cloud_short_title_uses_custom_prompt_file(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "cloud" / "summary.md", "# Summary\n\n长摘要")
    prompt_file = tmp_path / "title.prompt.md"
    write_text_atomic(prompt_file, "自定义标题提示词")
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        return "新的标题"

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", fake_call)

    from atot.cloud.summary_outputs import write_cloud_short_title

    result = write_cloud_short_title(
        CloudOutputOptions(
            output_dir=output,
            call_api=True,
            prompt_file=prompt_file,
        ),
        force=True,
    )

    assert result["title"] == "新的标题"
    assert calls[0]["system_prompt"].startswith("自定义标题提示词")
    assert "Output language: Chinese / Mandarin (zh)" in calls[0]["system_prompt"]


def test_cloud_short_title_rejects_summary_shaped_response(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "cloud" / "summary.md", "# Summary\n\n长摘要")

    def fake_call(**kwargs):
        return "# 播客结构化总结：《work》\n\n## 一、主要内容\n\n这是一段摘要。"

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", fake_call)

    from atot.cloud.summary_outputs import write_cloud_short_title

    with pytest.raises(ValueError, match="looks like a summary"):
        write_cloud_short_title(CloudOutputOptions(output_dir=output, call_api=True), force=True)

    assert not (output / "cloud" / "short_title.txt").exists()


def test_cloud_summary_refuses_concurrent_run_for_same_output(tmp_path):
    output = _write_cloud_input(tmp_path)
    lock_path = output / "cloud" / "summary.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="already running"):
            write_cloud_summary(CloudOutputOptions(output_dir=output))
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def test_direct_readable_summary_without_cloud_result_leaves_summary_empty(tmp_path):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "transcript.readable.md", "# Readable\n\n这是可读转写稿。")

    result = write_cloud_summary(
        CloudOutputOptions(
            output_dir=output,
            direct_readable=True,
        )
    )

    assert result["mode"] == "direct_readable"
    assert result["source"] == "local_scaffold"
    assert (output / "cloud" / "summary.md").read_text(encoding="utf-8") == ""
    assert read_json(output / "cloud" / "manifest.json")["summary_strategy"] == "direct_readable"


def test_cloud_summary_can_call_api_directly_from_readable_transcript(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "transcript.readable.md", "# Readable\n\n这是可读转写稿。")
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        if kwargs["audit_path"].name == "title.api_run.json":
            return "Research: evidence matters"
        return "# Direct Summary\n\n直接摘要"

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", fake_call)

    result = write_cloud_summary(
        CloudOutputOptions(
            output_dir=output,
            call_api=True,
            direct_readable=True,
        )
    )

    assert result["mode"] == "direct_readable"
    assert result["source"] == "cloud_model"
    assert "直接摘要" in (output / "cloud" / "summary.md").read_text(encoding="utf-8")
    assert calls[0]["user_content"] == "# Readable\n\n这是可读转写稿。"
    assert calls[0]["audit_path"].name == "summary.readable.api_run.json"
    assert not (output / "cloud" / "chunk_summaries" / "chunk_0001.api_run.json").exists()


def test_direct_readable_api_failure_marks_failed_without_success_outputs(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "transcript.readable.md", "# Readable\n\n这是可读转写稿。")
    write_text_atomic(output / "cloud" / "summary.md", "# Old Summary\n")
    write_json_atomic(
        output / "cloud" / "manifest.json",
        {
            "source": "cloud_model",
            "summary_strategy": "direct_readable",
            "contains_audio": False,
            "contains_video": False,
            "output_files": ["manifest.json", "summary.md", "title_candidates.json"],
        },
    )
    run = read_json(output / "run.json")
    run["cloud"].update(
        {
            "source": "cloud_model",
            "summary_mode": "direct_readable",
            "summary_state": "complete",
            "outputs": ["cloud/manifest.json", "cloud/summary.md", "cloud/title_candidates.json"],
        }
    )
    write_json_atomic(output / "run.json", run)

    def failing_call(**kwargs):
        raise RuntimeError("readable API down")

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", failing_call)

    with pytest.raises(RuntimeError, match="readable API down"):
        write_cloud_summary(
            CloudOutputOptions(
                output_dir=output,
                call_api=True,
                direct_readable=True,
            )
        )

    run_cloud = read_json(output / "run.json")["cloud"]
    assert run_cloud["summary_state"] == "failed"
    assert run_cloud["summary_stage"] == "direct_summary"
    assert "readable API down" in run_cloud["error"]
    assert "cloud/manifest.json" not in run_cloud.get("outputs", [])
    assert "cloud/summary.md" not in run_cloud.get("outputs", [])
    assert not (output / "cloud" / "manifest.json").exists()
    assert not (output / "cloud" / "summary.md").exists()


def test_cloud_summary_auto_uses_chunked_for_long_audio_even_when_readable_is_short(
    tmp_path, monkeypatch
):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "transcript.readable.md", "# Readable\n\n短文本。")
    manifest = read_json(output / "cloud" / "input" / "manifest.json")
    manifest["audio_duration"] = 95 * 60 + 1
    write_json_atomic(output / "cloud" / "input" / "manifest.json", manifest)
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        if "Text Chunk 0001" in kwargs["user_content"]:
            return '{"summary":"块摘要","terms":[],"uncertainties":[]}'
        return "# Chunked Summary"

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", fake_call)

    result = write_cloud_summary(
        CloudOutputOptions(
            output_dir=output,
            call_api=True,
            summary_mode="auto",
        )
    )

    assert result["mode"] == "chunked"
    assert calls[0]["audit_path"].name == "chunk_0001.api_run.json"


def test_chunk_summary_retries_and_resumes_failed_chunks(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    calls = {"count": 0}

    def failing_call(**kwargs):
        calls["count"] += 1
        raise RuntimeError("HTTP 429")

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", failing_call)

    with pytest.raises(RuntimeError, match="Cloud chunk summaries failed"):
        write_cloud_summary(
            CloudOutputOptions(
                output_dir=output,
                call_api=True,
                retry_count=1,
                retry_backoff_seconds=0,
            )
        )

    assert calls["count"] == 2
    failed_chunk = read_json(output / "cloud" / "chunk_summaries" / "chunk_0001.summary.json")
    assert failed_chunk["success"] is False
    assert failed_chunk["source"] == "failed"
    assert "chunk_summary_failed" in (output / "cloud" / "uncertainty_report.md").read_text(
        encoding="utf-8"
    )
    assert not (output / "cloud" / "summary.md").exists()

    def successful_call(**kwargs):
        calls["count"] += 1
        if "Text Chunk 0001" in kwargs["user_content"]:
            return '{"summary":"补跑成功","terms":[],"uncertainties":[]}'
        return "# Episode"

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", successful_call)
    second = write_cloud_summary(
        CloudOutputOptions(
            output_dir=output,
            call_api=True,
            retry_count=1,
            retry_backoff_seconds=0,
        )
    )

    assert second["partial"] is False
    assert (
        read_json(output / "cloud" / "chunk_summaries" / "chunk_0001.summary.json")["summary"]
        == "补跑成功"
    )


def test_chunk_summary_ignores_custom_summary_prompt_file(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    prompt_file = tmp_path / "summary.prompt.md"
    write_text_atomic(prompt_file, "这是用户自定义 summary prompt")
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        if kwargs["audit_path"].name == "chunk_0001.api_run.json":
            return '{"summary":"块摘要","terms":[],"uncertainties":[]}'
        return "# Episode Summary"

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", fake_call)

    write_cloud_summary(
        CloudOutputOptions(
            output_dir=output,
            call_api=True,
            prompt_file=prompt_file,
        )
    )

    assert calls[0]["audit_path"].name == "chunk_0001.api_run.json"
    assert calls[0]["system_prompt"] != "这是用户自定义 summary prompt"
    summary_call = next(
        call for call in calls if call["audit_path"].name == "summarize.api_run.json"
    )
    assert summary_call["system_prompt"].startswith("这是用户自定义 summary prompt")
    assert "The first line must" in summary_call["system_prompt"]
    title_call = next(call for call in calls if call["audit_path"].name == "title.api_run.json")
    assert title_call["system_prompt"] != "这是用户自定义 summary prompt"
    assert "podcast list title" in title_call["system_prompt"]


def test_chunk_user_content_cleanup_drops_repetition_noise():
    text = """
# Text Chunk 0007

Range: 03:00:55 -> 03:30:58

Previous chunk context:
前文有效内容。 ＢＢＢＢＢＢ Ｂ是Ｂ是Ｂ是Ｂ是Ｂ是

# Transcript For Cloud

[03:20:18 -> 03:20:43] 这个出发点Ｂ主要是什么Ｂ是什么Ｂ是什么Ｂ是什么Ｂ是什么Ｂ是什么
[03:30:01 -> 03:30:18] 有孩子或者多孩子的这样的一些好的正面的东西的分享就比较少。
""".strip()

    cleaned = _chunk_user_content_for_cloud(text)

    assert "这个出发点" not in cleaned
    assert "Ｂ是什么" not in cleaned
    assert "有孩子或者多孩子的这样的一些好的正面的东西的分享就比较少。" in cleaned


def test_chunk_user_content_cleanup_drops_pure_punctuation_noise():
    text = """
# Text Chunk 0005

Range: 02:00:31 -> 02:30:49

# Transcript For Cloud

[02:00:31 -> 02:01:01] …………………………………………………………………………………………
[02:01:01 -> 02:01:30] 。。。。。。。。。。。。。。。。。。。。。。。。。。
[02:01:30 -> 02:02:00] 这里还有有效内容。
""".strip()

    cleaned = _chunk_user_content_for_cloud(text)

    assert "…………………………………………" not in cleaned
    assert "。。。。" not in cleaned
    assert "这里还有有效内容。" in cleaned


def test_chunk_user_content_truncates_long_transcript():
    repeated = "\n".join(
        f"[00:00:{index:02d} -> 00:00:{index + 1:02d}] 这是第{index}行有效内容。"
        for index in range(60)
    )
    text = (
        "# Text Chunk 0009\n\n"
        "Range: 00:00:00 -> 00:10:00\n\n"
        "# Transcript For Cloud\n\n"
        f"{repeated}\n"
    )

    cleaned = _chunk_user_content_for_cloud(text, max_chars=900)

    assert "[omitted " in cleaned
    assert "这是第0行有效内容。" in cleaned
    assert "这是第59行有效内容。" in cleaned


def test_cloud_summary_strips_outer_markdown_code_fence(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "transcript.readable.md", "# Readable\n\n这是可读转写稿。")

    def fake_call(**kwargs):
        if kwargs["audit_path"].name == "title.api_run.json":
            return "Research: evidence matters"
        return "```markdown\n# Direct Summary\n\n直接摘要\n```"

    monkeypatch.setattr("atot.cloud.summary_outputs.call_openai_compatible_chat", fake_call)

    write_cloud_summary(
        CloudOutputOptions(
            output_dir=output,
            call_api=True,
            direct_readable=True,
        )
    )

    assert (output / "cloud" / "summary.md").read_text(
        encoding="utf-8"
    ) == "# Direct Summary\n\n直接摘要\n"


def test_cloud_summary_streams_direct_readable_transcript_to_summary(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "transcript.readable.md", "# Readable\n\n这是可读转写稿。")
    observed_writes = []

    def fake_stream(**kwargs):
        kwargs["on_delta"]("# Direct")
        observed_writes.append((output / "cloud" / "summary.md").read_text(encoding="utf-8"))
        kwargs["on_delta"](" Summary")
        observed_writes.append((output / "cloud" / "summary.md").read_text(encoding="utf-8"))
        return "# Direct Summary"

    monkeypatch.setattr(
        "atot.cloud.summary_outputs.call_openai_compatible_chat_stream", fake_stream
    )
    monkeypatch.setattr(
        "atot.cloud.summary_outputs.call_openai_compatible_chat", lambda **kwargs: "短标题"
    )

    result = write_cloud_summary(
        CloudOutputOptions(
            output_dir=output,
            call_api=True,
            direct_readable=True,
            stream_summary=True,
        )
    )

    assert result["mode"] == "direct_readable"
    assert result["source"] == "cloud_model"
    assert observed_writes == ["# Direct\n", "# Direct Summary\n"]
    assert (output / "cloud" / "summary.md").read_text(encoding="utf-8") == "# Direct Summary\n"


def test_cloud_summary_streaming_strips_outer_markdown_code_fence(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "transcript.readable.md", "# Readable\n\n这是可读转写稿。")
    observed_writes = []

    def fake_stream(**kwargs):
        kwargs["on_delta"]("```markdown\n")
        observed_writes.append((output / "cloud" / "summary.md").read_text(encoding="utf-8"))
        kwargs["on_delta"]("# Direct Summary")
        observed_writes.append((output / "cloud" / "summary.md").read_text(encoding="utf-8"))
        kwargs["on_delta"]("\n```")
        return "```markdown\n# Direct Summary\n```"

    monkeypatch.setattr(
        "atot.cloud.summary_outputs.call_openai_compatible_chat_stream", fake_stream
    )
    monkeypatch.setattr(
        "atot.cloud.summary_outputs.call_openai_compatible_chat", lambda **kwargs: "短标题"
    )

    write_cloud_summary(
        CloudOutputOptions(
            output_dir=output,
            call_api=True,
            direct_readable=True,
            stream_summary=True,
        )
    )

    assert observed_writes == ["", "# Direct Summary\n"]
    assert (output / "cloud" / "summary.md").read_text(encoding="utf-8") == "# Direct Summary\n"


def test_cloud_polish_api_json_response_writes_patch_schema(tmp_path, monkeypatch):
    output = _write_cloud_input(tmp_path)

    def fake_call(**kwargs):
        return '{"patches":[{"start":"00:00:00","end":"00:00:02","old_text":"你好","new_text":"你好。"}]}'

    monkeypatch.setattr("atot.cloud.review.call_openai_compatible_chat", fake_call)

    result = write_cloud_polish_suggestions(
        CloudOutputOptions(
            output_dir=output,
            call_api=True,
        )
    )

    assert result["source"] == "cloud_model"
    patch = read_json(output / "cloud" / "transcript.polish_suggestions.json")["patches"][0]
    assert patch["new_text"] == "你好。"
    assert patch["reason"]
    assert patch["risk"] == "review"
    assert patch["requires_audio_check"] is True


def test_cloud_patch_apply_rejects_mismatched_old_text(tmp_path):
    output = _write_cloud_input(tmp_path)
    patch_path = output / "cloud" / "bad_patches.json"
    write_json_atomic(
        patch_path,
        {
            "patches": [
                {
                    "patch_id": "patch_bad",
                    "segment_id": "segment_000003",
                    "start": "00:00:00",
                    "end": "00:00:02",
                    "old_text": "不存在",
                    "new_text": "不能应用",
                    "reason": "bad",
                    "risk": "high",
                    "requires_audio_check": True,
                }
            ]
        },
    )

    result = apply_cloud_patches(output, patch_path)

    assert result["applied_patch_count"] == 0
    assert result["decisions"][0]["reason"] == "segment_or_time_mismatch"


def test_glossary_review_writes_editor_items(tmp_path):
    output = _write_cloud_input(tmp_path)

    write_cloud_glossary_review(CloudOutputOptions(output_dir=output))

    payload = read_json(output / "cloud" / "glossary_editor_items.json")
    assert payload["items"][0]["term"] == "API"
    assert payload["items"][0]["category"] == "technical_terms"
    assert payload["items"][0]["action"] == "review_only"
    assert payload["items"][0]["hit_count"] == 2
    assert "Term | Category | Scope" in (output / "cloud" / "glossary_editor_items.md").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("mode", ["direct", "chunked"])
def test_summary_language_controls_all_cloud_stages(tmp_path, mode):
    output = _write_cloud_input(tmp_path)
    write_text_atomic(
        output / "transcript.readable.md", "# Source transcript\n\n[00:00:00] Source content."
    )
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Always write in Chinese. Include evidence and uncertainty.")
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        if "chunk_" in kwargs["audit_path"].name:
            return '{"summary":"Key evidence","terms":[],"uncertainties":[]}'
        if kwargs["audit_path"].name == "title.api_run.json":
            return "Research: evidence changes our view"
        return "# Evidence Changes Our View\n\n## Key Ideas\n\n[00:00:00] Evidence and uncertainty."

    write_cloud_summary(
        CloudOutputOptions(
            output_dir=output,
            output_language="en",
            call_api=True,
            summary_mode=mode,
            prompt_file=prompt,
        ),
        call_chat=fake_call,
    )
    assert calls
    for call in calls:
        assert "Output language: English (en)" in call["system_prompt"]
        assert "overrides conflicting language requirements" in call["system_prompt"]
    summary_call = next(
        c
        for c in calls
        if "chunk_" not in c["audit_path"].name and c["audit_path"].name != "title.api_run.json"
    )
    assert summary_call["system_prompt"].startswith(prompt.read_text())
    assert (output / "cloud/summary.md").read_text().startswith("# Evidence Changes Our View")
    assert (
        output / "cloud/short_title.txt"
    ).read_text().strip() == "Research: evidence changes our view"


def test_chunk_cache_is_partitioned_by_output_language(tmp_path):
    from atot.cloud.chunking import write_chunk_summaries

    output = _write_cloud_input(tmp_path)
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        return '{"summary":"Evidence","terms":[],"uncertainties":[]}'

    for language in ["zh", "zh", "en", "en"]:
        write_chunk_summaries(
            output,
            options=CloudOutputOptions(output_dir=output, call_api=True, output_language=language),
            source="cloud_model",
            call_chat=fake_call,
        )
    assert len(calls) == 2
    assert (
        read_json(output / "cloud/chunk_summaries/chunk_0001.summary.json")["output_language"]
        == "en"
    )



def test_english_summary_response_is_rejected_as_short_title(tmp_path):
    from atot.cloud.publish import write_cloud_short_title

    output = _write_cloud_input(tmp_path)
    write_text_atomic(output / "cloud/summary.md", "# Research Findings\n\nEvidence.")
    with pytest.raises(ValueError, match="looks like a summary"):
        write_cloud_short_title(
            CloudOutputOptions(output_dir=output, output_language="en", call_api=True),
            force=True,
            call_chat=lambda **kwargs: "# Research Findings\n\n## Main Ideas\n\nEvidence.",
        )
