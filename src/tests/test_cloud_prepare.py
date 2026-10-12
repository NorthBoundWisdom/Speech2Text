from atot.cloud.prepare import CloudPrepareOptions, prepare_cloud_input
from atot.utils import read_json, write_json_atomic, write_text_atomic


def test_prepare_cloud_input_writes_text_only_manifest(tmp_path):
    output = tmp_path / "episode" / "output"
    details = output
    write_json_atomic(
        details / "corrected.json",
        {
            "segments": [
                {"start": 0.0, "end": 30.0, "text": "第一段"},
                {"start": 1200.0, "end": 1230.0, "text": "第二段"},
            ]
        },
    )
    write_json_atomic(details / "qa.json", {"success": True})
    write_text_atomic(details / "qa.md", "# QA\n\nStatus: PASS\n")
    write_json_atomic(details / "review.json", {"summary": {}})
    write_json_atomic(details / "glossary.effective.json", {"technical_terms": ["ASR"]})
    write_json_atomic(
        details / "run.json", {"audio_duration": 1230.0, "model_alias_or_input": "large-v3-turbo"}
    )
    write_json_atomic(
        output / "manifest.json",
        {
            "schema_version": 1,
            "artifacts": [
                {"path": "corrected.json", "bytes": 12, "sha256": "abc"},
                {"path": "run.json", "bytes": 12, "sha256": "excluded"},
            ],
        },
    )
    write_text_atomic(output.parent / "主题.md", "节目主题")

    result = prepare_cloud_input(CloudPrepareOptions(output_dir=output, chunk_minutes=10.0))

    input_dir = output / "cloud" / "input"
    manifest = read_json(input_dir / "manifest.json")
    assert result["manifest"]["contains_audio"] is False
    assert manifest["contains_video"] is False
    assert "manifest.json" in manifest["input_files"]
    assert "transcript.for_cloud.md" in manifest["input_files"]
    assert "handoff_contract.md" in manifest["input_files"]
    assert "expected_outputs.schema.json" in manifest["input_files"]
    assert "README.md" in manifest["input_files"]
    assert manifest["readme"] == "README.md"
    assert "corrected.json" in {item["path"] for item in manifest["source_file_manifest"]}
    assert "run.json" not in {item["path"] for item in manifest["source_file_manifest"]}
    assert {item["source"] for item in manifest["source_file_manifest"]} == {"manifest"}
    assert "manifest.json" not in {item["path"] for item in manifest["input_file_manifest"]}
    assert "transcript.for_cloud.md" in {item["path"] for item in manifest["input_file_manifest"]}
    assert "prompts/summarize.prompt.md" in manifest["input_files"]
    assert "prompts/glossary_review.prompt.md" in manifest["prompt_templates"]
    assert "redaction_map.local.json" not in manifest["input_files"]
    assert (input_dir / "topic.for_cloud.md").read_text(encoding="utf-8").strip() == "节目主题"
    assert "只基于转写稿内容总结" in (input_dir / "prompts" / "summarize.prompt.md").read_text(
        encoding="utf-8"
    )
    assert len(manifest["text_chunks"]) == 2
    assert manifest["text_chunk_ranges"][1]["path"] == "chunks/text_chunk_0002.md"
    assert manifest["text_chunk_ranges"][1]["start"] == "00:20:00"
    assert manifest["text_chunk_ranges"][1]["end"] == "00:20:30"
    second_chunk = (input_dir / "chunks" / "text_chunk_0002.md").read_text(encoding="utf-8")
    assert "Previous chunk context:" in second_chunk
    assert "第一段" in second_chunk
    assert "Range: 00:20:00 -> 00:20:30" in second_chunk


def test_prepare_cloud_input_uses_episode_metadata_title_in_work_tree(tmp_path):
    data_root = tmp_path / "data"
    material_dir = data_root / "materials" / "episode-001"
    output = data_root / "work" / "episode-001"
    media = material_dir / "voice.m4a"
    write_text_atomic(media, "audio placeholder")
    write_json_atomic(material_dir / "episode.json", {"title": "真正的播客标题"})
    write_text_atomic(material_dir / "主题.md", "# 主题文件标题\n")
    write_json_atomic(
        output / "corrected.json", {"segments": [{"start": 0.0, "end": 2.0, "text": "第一段"}]}
    )
    write_json_atomic(output / "qa.json", {"success": True})
    write_json_atomic(output / "review.json", {"summary": {}})
    write_json_atomic(output / "glossary.effective.json", {})
    write_json_atomic(
        output / "run.json",
        {
            "input_path": str(media),
            "audio_duration": 2.0,
            "model_alias_or_input": "large-v3-turbo",
        },
    )

    prepare_cloud_input(CloudPrepareOptions(output_dir=output))

    manifest = read_json(output / "cloud" / "input" / "manifest.json")
    assert manifest["episode_title"] == "真正的播客标题"
    assert manifest["episode_title"] != "work"


def test_prepare_cloud_input_redacts_pii_from_transcript_and_segments(tmp_path):
    output = tmp_path / "episode" / "output"
    details = output
    write_json_atomic(
        details / "corrected.json",
        {
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.0,
                    "text": "电话 13812345678，邮箱 me@example.com，联系人：张三，地址上海市浦东新区世纪大道100号",
                }
            ]
        },
    )
    write_text_atomic(output.parent / "主题.md", "私下说，这段不要公开。")

    prepare_cloud_input(CloudPrepareOptions(output_dir=output, redact="pii"))

    input_dir = output / "cloud" / "input"
    transcript = (input_dir / "transcript.for_cloud.md").read_text(encoding="utf-8")
    segments = read_json(input_dir / "segments.for_cloud.json")["segments"]
    assert "13812345678" not in transcript
    assert "me@example.com" not in segments[0]["text"]
    assert "张三" not in transcript
    assert "上海市浦东新区世纪大道100号" not in segments[0]["text"]
    assert "[PERSON_UNCONFIRMED_1]" in transcript
    assert "[ADDRESS_1]" in transcript
    assert "privacy_hint" in (input_dir / "privacy_review.md").read_text(encoding="utf-8")
    assert (input_dir / "redaction_map.local.json").exists()
    manifest = read_json(input_dir / "manifest.json")
    assert "redaction_map.local.json" not in manifest["input_files"]
    assert manifest["privacy_review_file"] == "privacy_review.md"
    assert {finding["type"] for finding in manifest["privacy_findings"]} >= {
        "address",
        "person_unconfirmed",
        "privacy_hint",
    }
